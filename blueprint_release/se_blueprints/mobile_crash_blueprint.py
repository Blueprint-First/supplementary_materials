"""
Mobile crash analysis blueprint.

Inbound: a batch of crash clusters (raw list or {data:[...]} envelope).
Each cluster is routed by CrashType:
  - ANDROID_JAVA_CRASH    → full 5-stage analysis chain.
  - ANDROID_NATIVE_CRASH  → registered with an empty stage list; the
                            engine surfaces this as a localized
                            "No interceptor found" failure rather than a
                            silent skip.

Internal Dubbo services (report query, app crash data) and code-side
adapters (stack parser, repo index, git API, summary parser) are stubbed
via `ctx["xxx"]` injection — the production adapters will land in the
public release once the framework decoupling roadmap completes (see
`../framework_roadmap.md`).
"""

from sca.engine import (
    Blueprint,
    node,
    precondition,
    postcondition,
    retry,
    timeout,
    sequence,
    route_by,
    foreach,
    PostconditionFailure,
)
from sca.tools import kb, llm

BP = Blueprint(name="mobile_crash_analysis", version="0.1.0")

# CrashType → interceptor chain registration (mirrors CrashAnalyseChain.init()).
SUPPORTED_CRASH_TYPES = {"ANDROID_JAVA_CRASH", "ANDROID_NATIVE_CRASH"}


# ---------- Stage 0: parse + per-crash routing ----------

@node(BP)
@postcondition(lambda ctx: ctx.get("crash_list") is not None)
def parse_crash_list(ctx):
    """Parse inbound payload — accepts raw array or {data:[...]} envelope."""
    raw = ctx["raw_crash_list"]
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict) and "data" in raw:
        items = raw["data"]
    elif isinstance(raw, dict):
        items = [raw]
    else:
        ctx["error_msg"] = f"unsupported crashListContent format: {type(raw).__name__}"
        items = []
    ctx["crash_list"] = [
        {
            "summary": it.get("summary"),
            "cluster_id": it.get("clusterId"),
            "crash_type": it.get("crashType") or ctx.get("default_crash_type"),
            "app_id": it.get("appId") or ctx.get("default_app_id"),
            "app_version": it.get("appVersion") or ctx.get("default_app_version"),
        }
        for it in items
    ]
    return ctx


@node(BP)
@precondition(lambda ctx: ctx.get("current_crash") is not None)
@postcondition(lambda ctx: ctx.get("route_decision") is not None)
def route_by_crash_type(ctx):
    """Route by CrashType. Empty / unsupported routes return error early."""
    crash_type = ctx["current_crash"]["crash_type"]
    if crash_type not in SUPPORTED_CRASH_TYPES:
        ctx["error_msg"] = f"No interceptor found, analysedInfo's crashType: {crash_type}"
        ctx["route_decision"] = "skip"
        return ctx
    if crash_type == "ANDROID_NATIVE_CRASH":
        ctx["error_msg"] = f"No interceptor found, analysedInfo's crashType: {crash_type}"
        ctx["route_decision"] = "skip"
        return ctx
    ctx["route_decision"] = "android_java_crash"
    return ctx


# ---------- Stage 1: SummeryAnalyseInterceptor ----------

@node(BP)
@retry(max_attempts=2, backoff_seconds=1.0)
@precondition(lambda ctx: ctx["current_crash"]["summary"] is not None)
@postcondition(lambda ctx: ctx.get("summary_features") is not None)
def summary_analyse(ctx):
    """Extract structured features from the crash summary text."""
    f = ctx["summary_parser"].extract(ctx["current_crash"]["summary"])
    ctx["summary_features"] = {
        "exception_class": f["exception_class"],
        "exception_message": f["exception_message"],
        "thread_name": f.get("thread_name"),
    }
    return ctx


# ---------- Stage 2: StackAnalyseInterceptor ----------

@node(BP)
@timeout(seconds=20)
@precondition(lambda ctx: ctx.get("summary_features") is not None)
@postcondition(lambda ctx: ctx.get("stack_frames") and len(ctx["stack_frames"]) > 0)
def stack_analyse(ctx):
    """Symbolicate and structure the crash stack into ordered frames."""
    raw_stack = ctx["current_crash"]["summary"]
    frames = ctx["stack_parser"].parse(raw_stack, app_id=ctx["current_crash"]["app_id"])
    ctx["stack_frames"] = [
        {
            "class_name": f["class_name"],
            "method_name": f["method_name"],
            "file_name": f.get("file_name"),
            "line_number": f.get("line_number"),
            "is_app_frame": f["is_app_frame"],
        }
        for f in frames
    ]
    ctx["top_app_frame"] = next(
        (f for f in ctx["stack_frames"] if f["is_app_frame"]),
        ctx["stack_frames"][0],
    )
    return ctx


# ---------- Stage 3: SourceCodeMetaInterceptor ----------

@node(BP)
@retry(max_attempts=2, backoff_seconds=1.0)
@precondition(lambda ctx: ctx.get("top_app_frame") is not None)
@postcondition(lambda ctx: ctx.get("source_meta") is not None)
def source_code_meta(ctx):
    """Resolve top app frame to source file + module + owning team."""
    frame = ctx["top_app_frame"]
    meta = ctx["repo_index"].locate(
        class_name=frame["class_name"],
        file_name=frame["file_name"],
        app_version=ctx["current_crash"]["app_version"],
    )
    if meta is None:
        ctx["error_msg"] = f"source meta not found for {frame['class_name']}"
        ctx["source_meta"] = {}
        return ctx
    ctx["source_meta"] = {
        "repo_path": meta["repo_path"],
        "module": meta["module"],
        "owning_team": meta["owning_team"],
        "file_path": meta["file_path"],
        "line_range": meta["line_range"],
    }
    return ctx


# ---------- Stage 4: KB lookup of known crashes ----------

@node(BP)
@retry(max_attempts=2, backoff_seconds=1.0)
@precondition(lambda ctx: ctx.get("stack_frames") and ctx.get("summary_features"))
@postcondition(lambda ctx: ctx.get("kb_hits") is not None)
def kb_query_known_crashes(ctx):
    """Look up similar crashes from the known-crashes knowledge base."""
    top_sig = (
        f"{ctx['top_app_frame']['class_name']}#"
        f"{ctx['top_app_frame']['method_name']}"
    )
    query = {
        "exception_class": ctx["summary_features"]["exception_class"],
        "top_frame_signature": top_sig,
        "module": ctx["source_meta"].get("module"),
    }
    hits = kb.query(namespace="known_crashes", query=query, top_k=5)
    ctx["kb_hits"] = [
        {
            "case_id": h.source_id,
            "score": h.score,
            "root_cause": h.payload["root_cause"],
            "fix_commit": h.payload.get("fix_commit"),
        }
        for h in hits
    ]
    return ctx


# ---------- Stage 5: AdvancedCrashAnalysisInterceptor (LLM) ----------

@node(BP)
@retry(max_attempts=2, on=PostconditionFailure, backoff_seconds=2.0)
@timeout(seconds=60)
@precondition(lambda ctx: ctx.get("source_meta") is not None and ctx.get("kb_hits") is not None)
@postcondition(lambda ctx: ctx.get("advanced_analysis") is not None)
def advanced_crash_analysis(ctx):
    """LLM root-cause pass over summary + stack + source + KB."""
    prompt = {
        "task": "android_java_crash_root_cause",
        "summary_features": ctx["summary_features"],
        "stack_frames": ctx["stack_frames"][:20],
        "source_meta": ctx["source_meta"],
        "kb_hits": ctx["kb_hits"],
    }
    schema = {
        "root_cause": "str",
        "confidence": "float",
        "evidence": "list[str]",
        "suspect_files": "list[str]",
    }
    ctx["advanced_analysis"] = llm.invoke(prompt, schema=schema, tools=[])
    return ctx


# ---------- Stage 6: GitBlameInterceptor ----------

@node(BP)
@retry(max_attempts=3, backoff_seconds=1.0)
@timeout(seconds=30)
@precondition(lambda ctx: ctx["advanced_analysis"].get("suspect_files"))
def git_blame(ctx):
    """Run git blame on suspect files to rank likely-culprit commits."""
    suspects = ctx["advanced_analysis"]["suspect_files"]
    commits = ctx["git_api"].blame_rank(
        repo_path=ctx["source_meta"]["repo_path"],
        files=suspects,
        before_version=ctx["current_crash"]["app_version"],
    )
    if not commits:
        ctx["error_msg"] = "git_blame returned no candidate commits"
        return ctx
    ctx["blame_commit"] = commits[0]
    ctx["blame_candidates"] = commits[:5]
    return ctx


# ---------- Stage 7: LLM remediation hint ----------

@node(BP)
@retry(max_attempts=2, on=PostconditionFailure, backoff_seconds=2.0)
@timeout(seconds=45)
@precondition(lambda ctx: ctx.get("blame_commit") is not None)
@postcondition(lambda ctx: ctx.get("remediation_hint") is not None)
def llm_remediation_hint(ctx):
    """LLM-generated remediation hint grounded in blame commit + KB cases."""
    prompt = {
        "task": "android_java_crash_remediation",
        "root_cause": ctx["advanced_analysis"]["root_cause"],
        "blame_commit": ctx["blame_commit"],
        "kb_fixes": [h["fix_commit"] for h in ctx["kb_hits"] if h.get("fix_commit")],
    }
    schema = {"hint_text": "str", "suggested_owner": "str"}
    result = llm.invoke(prompt, schema=schema, tools=[])
    ctx["remediation_hint"] = result["hint_text"]
    ctx["suggested_owner"] = result["suggested_owner"]
    return ctx


# ---------- Top-level: per-crash chain registered by CrashType ----------

ANDROID_JAVA_CRASH_CHAIN = sequence(
    summary_analyse,
    stack_analyse,
    source_code_meta,
    kb_query_known_crashes,
    advanced_crash_analysis,
    git_blame,
    llm_remediation_hint,
)

PER_CRASH_GRAPH = sequence(
    route_by_crash_type,
    route_by(
        key="route_decision",
        cases={
            "android_java_crash": ANDROID_JAVA_CRASH_CHAIN,
            "skip": sequence(),
        },
    ),
)

BP.graph = sequence(
    parse_crash_list,
    foreach("crash_list", item_key="current_crash", body=PER_CRASH_GRAPH),
)


if __name__ == "__main__":
    BP.run()
