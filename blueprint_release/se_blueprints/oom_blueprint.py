"""
Java OOM diagnosis blueprint.

Deterministic SCA node graph for triaging Java service OOM at fleet
scale:

    drain traffic -> jstat / jmap snapshot -> parse heap dump || scan logs
        -> correlate -> KB lookup of similar historical cases
        -> LLM root-cause pass -> LLM remediation hint -> draft ticket

Internal service registry, dump store, log API, ticket API, and observability
hooks are stubbed via `ctx["xxx_api"]` injection — the production adapters
will land in the public release once the framework decoupling roadmap
completes (see `../framework_roadmap.md`).
"""

from sca.engine import (
    Blueprint,
    node,
    precondition,
    postcondition,
    retry,
    timeout,
    sequence,
    fork_join,
    PostconditionFailure,
)
from sca.tools import kb, llm

BP = Blueprint(name="oom_diagnosis", version="0.1.0")


# ---------- Stage 1: target acquisition ----------

@node(BP)
@retry(max_attempts=3, backoff_seconds=2.0)
@postcondition(lambda ctx: ctx.get("jvm_pid") is not None)
def fetch_target_jvm(ctx):
    """Resolve the suspected JVM pid on the target host."""
    proc = ctx["jvm_ops"].locate_jvm(ctx["target_host"], app=ctx["app_name"])
    ctx["jvm_pid"] = proc["pid"]
    ctx["jvm_start_ts"] = proc["start_ts"]
    ctx["jvm_uptime_s"] = proc["uptime_s"]
    return ctx


@node(BP)
@precondition(lambda ctx: ctx.get("jvm_pid") is not None)
@postcondition(lambda ctx: ctx.get("traffic_drained") is True)
def traffic_drained_check(ctx):
    """Refuse to inspect a JVM still serving production traffic."""
    in_lb = ctx["lb_api"].is_in_pool(ctx["target_host"])
    if in_lb:
        ctx["traffic_drained"] = False
        raise RuntimeError(
            f"host {ctx['target_host']} still in load-balancer pool — drain first"
        )
    ctx["traffic_drained"] = True
    return ctx


# ---------- Stage 2: snapshot + dump ----------

@node(BP)
@timeout(seconds=30)
@precondition(lambda ctx: ctx.get("traffic_drained") is True)
@postcondition(lambda ctx: ctx.get("jstat_done") is True)
def jstat_snapshot(ctx):
    """Capture a jstat -gc snapshot for GC pressure context."""
    s = ctx["jvm_ops"].jstat_gc(ctx["target_host"], ctx["jvm_pid"])
    ctx["jstat"] = {
        "ygc": s["ygc"],
        "ygct_s": s["ygct"],
        "fgc": s["fgc"],
        "fgct_s": s["fgct"],
        "old_used_pct": s["old_used_pct"],
        "metaspace_used_pct": s["metaspace_used_pct"],
    }
    ctx["jstat_done"] = True
    return ctx


@node(BP)
@precondition(lambda ctx: ctx.get("jstat_done") is True)
@postcondition(lambda ctx: ctx.get("gc_pressure") is not None)
def assess_gc_pressure(ctx):
    """Categorize GC pressure from jstat — short-circuits dump on benign cases."""
    j = ctx["jstat"]
    fgc_per_min = (j["fgc"] / max(ctx["jvm_uptime_s"], 1)) * 60
    category = (
        "old_saturated" if j["old_used_pct"] >= 90 and fgc_per_min > 0.5
        else "metaspace_leak" if j["metaspace_used_pct"] >= 95
        else "young_gc_storm" if j["ygc"] > 0 and (j["ygct_s"] / max(j["ygc"], 1)) > 0.5
        else "benign" if j["old_used_pct"] < 50 and fgc_per_min < 0.05
        else "ambiguous"
    )
    ctx["gc_pressure"] = {
        "category": category,
        "fgc_per_min": round(fgc_per_min, 3),
        "old_used_pct": j["old_used_pct"],
        "metaspace_used_pct": j["metaspace_used_pct"],
    }
    return ctx


@node(BP)
@timeout(seconds=180)
@precondition(lambda ctx: ctx.get("gc_pressure", {}).get("category") != "benign")
@postcondition(lambda ctx: ctx.get("heap_dump_path") is not None)
def jmap_heap_dump(ctx):
    """Trigger jmap heap dump to a side-channel dump store."""
    dump_path = ctx["dump_store"].allocate_path(host=ctx["target_host"], pid=ctx["jvm_pid"])
    ctx["jvm_ops"].jmap_dump(ctx["target_host"], ctx["jvm_pid"], dump_path)
    ctx["heap_dump_path"] = dump_path
    return ctx


# ---------- Stage 3: parse heap || scan logs ----------

@node(BP)
@precondition(lambda ctx: ctx.get("heap_dump_path") is not None)
@postcondition(lambda ctx: ctx.get("dump_verified") is True)
def verify_dump_integrity(ctx):
    """Validate jmap output before parsing — magic header, size sanity, monotonic write."""
    path = ctx["heap_dump_path"]
    head = ctx["dump_store"].read_head(path, n_bytes=8)
    if not head.startswith(b"JAVA PROFILE"):
        raise RuntimeError(f"dump {path} missing JAVA PROFILE magic header")
    size = ctx["dump_store"].stat(path)["size"]
    if size < ctx.get("min_dump_bytes", 1024 * 1024):
        raise RuntimeError(f"dump {path} too small ({size}) — likely truncated")
    if ctx["dump_store"].is_being_written(path):
        raise RuntimeError(f"dump {path} still being written — refusing to parse mid-flight")
    ctx["dump_verified"] = True
    ctx["heap_dump_size"] = size
    return ctx


@node(BP)
@timeout(seconds=300)
@precondition(lambda ctx: ctx.get("dump_verified") is True)
@postcondition(lambda ctx: ctx.get("dominator_tree") is not None)
def parse_heap_dump(ctx):
    """Parse heap dump and extract the dominator tree (top retained)."""
    parsed = ctx["heap_parser"].parse(ctx["heap_dump_path"], top_n=20)
    ctx["dominator_tree"] = parsed["dominators"]
    ctx["heap_summary"] = {
        "used_bytes": parsed["used_bytes"],
        "total_bytes": parsed["total_bytes"],
        "class_count": parsed["class_count"],
    }
    return ctx


@node(BP)
@precondition(lambda ctx: ctx.get("dominator_tree") is not None)
@postcondition(lambda ctx: ctx.get("suspect_classes") is not None)
def identify_suspect_classes(ctx):
    """Pick suspect classes by retained-size threshold."""
    threshold = ctx.get("suspect_threshold_bytes", 50 * 1024 * 1024)
    ctx["suspect_classes"] = [
        {
            "class_name": d["class_name"],
            "retained_mb": d["retained_bytes"] // (1024 * 1024),
            "instance_count": d["instance_count"],
        }
        for d in ctx["dominator_tree"]
        if d["retained_bytes"] >= threshold
    ]
    return ctx


@node(BP)
@timeout(seconds=60)
@postcondition(lambda ctx: ctx.get("matched_logs") is not None)
def log_scan(ctx):
    """Scan service logs for OOM-adjacent ERROR lines around the dump time."""
    window_s = ctx.get("log_window_s", 600)
    around_ts = ctx["jvm_start_ts"] + ctx["jvm_uptime_s"]
    ctx["matched_logs"] = ctx["log_api"].grep(
        host=ctx["target_host"],
        patterns=["OutOfMemoryError", "GC overhead", "Java heap space"],
        around_ts=around_ts,
        window_s=window_s,
    )
    return ctx


# ---------- Stage 4: correlate (join) ----------

@node(BP)
@precondition(lambda ctx: ctx.get("suspect_classes") is not None and ctx.get("matched_logs") is not None)
@postcondition(lambda ctx: len(ctx.get("suspects", [])) > 0)
def correlate(ctx):
    """Correlate suspect classes with matched logs into a single suspect set."""
    suspects = []
    for cls in ctx["suspect_classes"]:
        short = cls["class_name"].split(".")[-1].lower()
        related = [log for log in ctx["matched_logs"] if short in log["line"].lower()]
        suspects.append({
            "class_name": cls["class_name"],
            "retained_mb": cls["retained_mb"],
            "instance_count": cls["instance_count"],
            "related_logs": related[:5],
        })
    ctx["suspects"] = suspects
    return ctx


# ---------- Stage 5: KB lookup of similar historical cases ----------

@node(BP)
@retry(max_attempts=2, backoff_seconds=1.0)
@precondition(lambda ctx: ctx.get("suspects") is not None)
@postcondition(lambda ctx: ctx.get("kb_hits") is not None)
def kb_query_oom_patterns(ctx):
    """Look up similar OOM cases from the historical knowledge base."""
    query = {
        "suspect_classes": [s["class_name"] for s in ctx["suspects"][:5]],
        "log_keywords": list({log["pattern"] for s in ctx["suspects"] for log in s["related_logs"]}),
        "app_name": ctx["app_name"],
    }
    hits = kb.query(namespace="oom_cases", query=query, top_k=5)
    ctx["kb_hits"] = [
        {
            "case_id": h.source_id,
            "score": h.score,
            "root_cause": h.payload["root_cause"],
            "fix_summary": h.payload["fix_summary"],
        }
        for h in hits
    ]
    return ctx


# ---------- Stage 6: LLM root cause + remediation ----------

@node(BP)
@retry(max_attempts=2, on=PostconditionFailure, backoff_seconds=2.0)
@timeout(seconds=60)
@precondition(lambda ctx: ctx.get("suspects") and ctx.get("kb_hits") is not None)
@postcondition(lambda ctx: ctx.get("root_cause") is not None)
def llm_root_cause(ctx):
    """LLM root-cause pass over suspects + jstat + KB hits."""
    prompt = {
        "task": "java_oom_root_cause",
        "app_name": ctx["app_name"],
        "jstat": ctx["jstat"],
        "gc_pressure": ctx["gc_pressure"],
        "heap_summary": ctx["heap_summary"],
        "suspects": ctx["suspects"],
        "kb_hits": ctx["kb_hits"],
    }
    schema = {
        "root_cause": "str",
        "confidence": "float",
        "evidence": "list[str]",
        "ranked_suspects": "list[str]",
    }
    result = llm.invoke(prompt, schema=schema, tools=[])
    ctx["root_cause"] = result["root_cause"]
    ctx["root_cause_confidence"] = result["confidence"]
    ctx["root_cause_evidence"] = result["evidence"]
    ctx["ranked_suspects"] = result["ranked_suspects"]
    return ctx


@node(BP)
@retry(max_attempts=2, on=PostconditionFailure, backoff_seconds=2.0)
@timeout(seconds=45)
@precondition(lambda ctx: ctx.get("root_cause") is not None)
@postcondition(lambda ctx: ctx.get("remediation_hint") is not None)
def remediation_hint(ctx):
    """LLM-generated, KB-grounded remediation hint."""
    prompt = {
        "task": "java_oom_remediation",
        "root_cause": ctx["root_cause"],
        "evidence": ctx["root_cause_evidence"],
        "kb_fix_summaries": [h["fix_summary"] for h in ctx["kb_hits"]],
    }
    schema = {"hint_text": "str", "action_items": "list[str]"}
    result = llm.invoke(prompt, schema=schema, tools=[])
    ctx["remediation_hint"] = result["hint_text"]
    ctx["remediation_actions"] = result["action_items"]
    return ctx


# ---------- Stage 7: ticket draft ----------

@node(BP)
@precondition(lambda ctx: ctx.get("remediation_hint") is not None)
@postcondition(lambda ctx: ctx.get("ticket_draft") is not None)
def draft_ticket(ctx):
    """Draft (never auto-create) an on-call ticket with full evidence trail."""
    ctx["ticket_draft"] = ctx["ticket_api"].draft({
        "title": f"[OOM] {ctx['app_name']} — {ctx['root_cause'][:64]}",
        "host": ctx["target_host"],
        "jvm_pid": ctx["jvm_pid"],
        "heap_dump_path": ctx["heap_dump_path"],
        "ranked_suspects": ctx["ranked_suspects"],
        "evidence": ctx["root_cause_evidence"],
        "kb_references": [h["case_id"] for h in ctx["kb_hits"]],
        "remediation_hint": ctx["remediation_hint"],
        "action_items": ctx["remediation_actions"],
    })
    return ctx


BP.graph = sequence(
    fetch_target_jvm,
    traffic_drained_check,
    jstat_snapshot,
    assess_gc_pressure,
    jmap_heap_dump,
    verify_dump_integrity,
    fork_join(
        branches=[
            sequence(parse_heap_dump, identify_suspect_classes),
            log_scan,
        ],
        join=correlate,
    ),
    kb_query_oom_patterns,
    llm_root_cause,
    remediation_hint,
    draft_ticket,
)


if __name__ == "__main__":
    BP.run()
