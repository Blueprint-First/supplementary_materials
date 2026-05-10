# Mobile Crash Diagnosis — Anonymized Execution Trace

## Incident

- App: `<APP>` (Android, tens of millions of DAU)
- Crash signature: `java.lang.NullPointerException` at `com.<app>.feed.FeedRecyclerAdapter#onBindViewHolder`
- Affected releases: `9.18.0`, `9.18.1` (regression introduced in 9.18.0)
- Cluster ID: `cluster-feed-adapter-npe-9180`
- Inbound payload: 1 cluster, 412 raw reports rolled up by the reporting backend

## Input

The blueprint is invoked with the following initial `ctx`. The reporting backend rolls per-device crash reports into clusters and forwards each cluster as one `raw_crash_list` item; the dispatcher fills `default_*` from the cluster's metadata:

```python
ctx = {
    "raw_crash_list": {
        "data": [
            {
                "clusterId": "cluster-feed-adapter-npe-9180",
                "crashType": "ANDROID_JAVA_CRASH",
                "appId": "<APP-ID>",
                "appVersion": "9.18.1",
                "summary": (
                    "java.lang.NullPointerException: Attempt to invoke virtual "
                    "method 'java.lang.String com.<app>.feed.FeedItem.getId()' "
                    "on a null object reference\n"
                    "    at com.<app>.feed.FeedRecyclerAdapter.onBindViewHolder"
                    "(FeedRecyclerAdapter.java:147)\n"
                    "    at com.<app>.feed.FeedRecyclerAdapter.onBindViewHolder"
                    "(FeedRecyclerAdapter.java:42)\n"
                    "    at androidx.recyclerview.widget.RecyclerView$Adapter."
                    "onBindViewHolder(RecyclerView.java:7570)\n"
                    "    at androidx.recyclerview.widget.RecyclerView$Adapter."
                    "bindViewHolder(RecyclerView.java:7647)\n"
                    "    at androidx.recyclerview.widget.RecyclerView$Recycler."
                    "tryBindViewHolderByDeadline(RecyclerView.java:6526)\n"
                    "    ... 13 more framework frames\n"
                ),
            }
        ]
    },
    "default_crash_type": "ANDROID_JAVA_CRASH",
    "default_app_id": "<APP-ID>",
    "default_app_version": "9.18.1",

    # injected adapter handles
    "summary_parser": <SummaryParserAdapter>,    # extract(summary) -> features
    "stack_parser":   <StackParserAdapter>,      # parse(raw, app_id=...) -> frames
    "repo_index":     <RepoIndexAdapter>,        # locate(class_name=, file_name=, app_version=)
    "git_api":        <GitAdapter>,              # blame_rank(repo_path=, files=, before_version=)
}
```

`kb` / `llm` are resolved via `sca.tools`, identical to the Java OOM case.

## SCA execution

| Step | Node | Outcome | Duration |
|---|---|---|---|
| 1 | `parse_crash_list` | 1 crash item parsed; `crash_type=ANDROID_JAVA_CRASH` | 0.1 s |
| 2 | `route_by_crash_type` | route_decision: `android_java_crash` (full 5-interceptor chain) | 0.05 s |
| 3 | `summary_analyse` | `exception_class=NullPointerException`; `exception_message="Attempt to invoke virtual method 'String com.<app>.feed.FeedItem.getId()' on a null object reference"`; `thread_name="main"` | 0.3 s |
| 4 | `stack_analyse` | 18 frames extracted; top app frame: `FeedRecyclerAdapter#onBindViewHolder` (`FeedRecyclerAdapter.java:147`) | 1.4 s |
| 5 | `source_code_meta` | Resolved to `repo_path=android-app/feed`; `module=feed`; `owning_team=feed-platform`; `file_path=src/main/java/com/<app>/feed/FeedRecyclerAdapter.java`; `line_range=140-160` | 1.1 s |
| 6 | `kb_query_known_crashes` | 2 hits; top hit `crash-2025-Q1-441` (score 0.83): "Adapter onBindViewHolder NPE after async list mutation"; `fix_commit=<HASH-PRIOR>` | 0.9 s |
| 7 | `advanced_crash_analysis` (LLM) | Root cause: "FeedRecyclerAdapter holds reference to the previous data list after async deletion completes; viewHolder is bound against a stale index"; confidence 0.79; `suspect_files=["FeedRecyclerAdapter.java", "FeedDataController.java"]` | 9.2 s |
| 8 | `git_blame` | 3 candidate commits; top: `<COMMIT-HASH-A>` by `<dev-id-7>` ("feed: switch to async deletion path", 11 days before 9.18.0 release cut) | 2.6 s |
| 9 | `llm_remediation_hint` | hint: "Guard against null `FeedItem` in `onBindViewHolder` (defensive return); cancel pending deletion task in `onDetachedFromWindow`; consider switching to `ListAdapter` + `DiffUtil` for safer list-mutation semantics"; `suggested_owner=feed-platform` | 6.0 s |

**Total wall-clock:** 21.7 s for the engine; with platform-side dispatch + draft-ticket persistence the alert-to-draft-ticket time was ~8 min, matching the deployment-scale median.

### Stack frame extract (from step 4)

```
at com.<app>.feed.FeedRecyclerAdapter.onBindViewHolder(FeedRecyclerAdapter.java:147)
at com.<app>.feed.FeedRecyclerAdapter.onBindViewHolder(FeedRecyclerAdapter.java:42)
at androidx.recyclerview.widget.RecyclerView$Adapter.onBindViewHolder(RecyclerView.java:7570)
at androidx.recyclerview.widget.RecyclerView$Adapter.bindViewHolder(RecyclerView.java:7647)
at androidx.recyclerview.widget.RecyclerView$Recycler.tryBindViewHolderByDeadline(RecyclerView.java:6526)
... (13 more frames, all framework)
```

`is_app_frame` filtering correctly identified the first two frames as belonging to the app, and `top_app_frame` resolved to line 147 (the `getId()` invocation).

## Output

Final `ctx` snapshot (per-crash, after the foreach iteration completes):

```python
ctx["summary_features"] = {
    "exception_class": "java.lang.NullPointerException",
    "exception_message": (
        "Attempt to invoke virtual method 'java.lang.String "
        "com.<app>.feed.FeedItem.getId()' on a null object reference"
    ),
    "thread_name": "main",
}

ctx["source_meta"] = {
    "repo_path": "android-app/feed",
    "module": "feed",
    "owning_team": "feed-platform",
    "file_path": "src/main/java/com/<app>/feed/FeedRecyclerAdapter.java",
    "line_range": [140, 160],
}

ctx["kb_hits"] = [
    {
        "case_id": "crash-2025-Q1-441",
        "score": 0.83,
        "root_cause": "Adapter onBindViewHolder NPE after async list mutation",
        "fix_commit": "<HASH-PRIOR>",
    },
    {
        "case_id": "crash-2024-Q4-208",
        "score": 0.61,
        "root_cause": "RecyclerView holder bound against stale position after diff",
        "fix_commit": "<HASH-PRIOR-2>",
    },
]

ctx["advanced_analysis"] = {
    "root_cause": (
        "FeedRecyclerAdapter retains a reference to the previous data list "
        "after FeedDataController completes an async deletion; the holder "
        "is then bound against a stale index whose backing FeedItem has "
        "already been removed, producing a null lookup at "
        "FeedRecyclerAdapter.java:147."
    ),
    "confidence": 0.79,
    "evidence": [
        "top app frame = onBindViewHolder line 147 (FeedItem.getId())",
        "FeedDataController switched to async deletion in <COMMIT-HASH-A> (11d before 9.18.0 cut)",
        "no null-guard around FeedItem at line 147 in 9.18.x",
        "KB hit crash-2025-Q1-441 (score 0.83) — same async-deletion + adapter NPE pattern",
    ],
    "suspect_files": [
        "src/main/java/com/<app>/feed/FeedRecyclerAdapter.java",
        "src/main/java/com/<app>/feed/FeedDataController.java",
    ],
}

ctx["blame_commit"] = {
    "hash": "<COMMIT-HASH-A>",
    "author": "<dev-id-7>",
    "subject": "feed: switch to async deletion path",
    "ts": 1759310000,
    "files": [
        "src/main/java/com/<app>/feed/FeedDataController.java",
        "src/main/java/com/<app>/feed/FeedRecyclerAdapter.java",
    ],
}
ctx["blame_candidates"] = [<COMMIT-HASH-A>, <COMMIT-HASH-B>, <COMMIT-HASH-C>]   # top 3

ctx["remediation_hint"] = (
    "Guard against null FeedItem in onBindViewHolder (defensive return + "
    "warn-once log); cancel pending FeedDataController deletion task in "
    "onDetachedFromWindow; consider switching to ListAdapter + DiffUtil for "
    "safer list-mutation semantics. Fix-commit precedent in <HASH-PRIOR> "
    "(crash-2025-Q1-441) used the same defensive-return pattern."
)
ctx["suggested_owner"] = "feed-platform"
```

This `ctx` is what the platform-side dispatcher persists into the draft ticket (the dispatcher itself, not the blueprint, owns the `<TICKET-SYSTEM>` write — the blueprint stays side-effect-free past `llm_remediation_hint`). The on-call mobile engineer accepted the draft after a 100-second review; the fix shipped in `9.18.2` four days later and the cluster's incoming-rate dropped to baseline within the next two release-rollout windows.

## Routing-failure demonstration (`ANDROID_NATIVE_CRASH`)

Same blueprint, same payload shape, but `crash_type=ANDROID_NATIVE_CRASH`:

| Step | Node | Outcome |
|---|---|---|
| 1 | `parse_crash_list` | 1 crash item parsed |
| 2 | `route_by_crash_type` | route_decision: `skip`; `error_msg="No interceptor found, analysedInfo's crashType: ANDROID_NATIVE_CRASH"` |
| 3 | (chain `skip` branch) | empty sequence; foreach iteration completes |

The engine surfaces the missing native chain as a named, structured outcome (`error_msg`) at the routing node — not as a silent skip and not as a downstream LLM hallucination over an empty stack. The blueprint registers `ANDROID_NATIVE_CRASH` with an empty interceptor list pending the native-symbolication chain landing. The same structural gap, in a free-form agent, would either silently no-op or produce a confidently-wrong root cause.

## Failure-mode demonstration (postcondition)

In a parallel test run on a synthetic crash where the top app frame's class name was deliberately not in the repo index, `source_code_meta` set `source_meta = {}` and recorded `error_msg="source meta not found for com.<app>.unknown.GhostClass"`.

- **With downstream preconditions intact:** `kb_query_known_crashes` evaluated its precondition `ctx.get("stack_frames") and ctx.get("summary_features")` (both present) and proceeded — but its KB query used `module=None`, returning 0 hits. `advanced_crash_analysis` then ran but with only summary + stack + empty KB, producing a low-confidence (0.41) root-cause string. `git_blame`'s precondition `ctx["advanced_analysis"].get("suspect_files")` *was* satisfied (LLM returned a guessed file), so `git_blame` ran and returned no candidates. The draft was not emitted because `blame_commit` was missing.
- **Without the precondition guard on `git_blame`:** the chain proceeded through `llm_remediation_hint`, which produced a hint targeting a fabricated file — exactly the false-positive ticket pattern the 30% → 8% improvement is designed to eliminate.

This is the same qualitative debuggability gain documented in the Java OOM trace: structural absences (missing source meta, empty git blame) produce localized, named outcomes rather than confidently-wrong downstream tickets.
