# Dialogue Example 1 — Leave Request Blueprint

> Anonymized human ↔ agent dialogue. Converged in 3 rounds. Final blueprint: 87 LoC. See [`../../se_blueprints/leave_request_blueprint.py`](../../se_blueprints/leave_request_blueprint.py).

## Round 1 — Elicitation

**Human:** I need a workflow for processing employee leave requests.

**Agent:** Got it. Two clarifying questions before I sketch the node graph:

1. What are the hard approval rules? (e.g., manager approval threshold, blackout periods, balance check.)
2. Where do I read employee balance and where do I write the approved leave?

**Human:**
1. <2 days = manager approval; ≥2 days = manager + dept head; balance must be sufficient; no blackout overlap.
2. Read balance from `<HR_API>`; write approved leave to `<CALENDAR_API>`.

## Round 2 — Node graph

**Agent:** Proposed graph:

```
parse_request -> balance_check -> blackout_check ->
    approval_router -> {manager_approve | manager_and_dept_head_approve} ->
    write_calendar -> notify
```

Pre/post:
- `balance_check` postcondition: `balance >= requested_days`
- `blackout_check` postcondition: no overlap with blackout list
- `approval_router` precondition: both checks passed
- `write_calendar` precondition: approval received

**Human:** Add a node before `notify` that emits to the audit log. Otherwise good.

## Round 3 — Compile and dry-run

**Agent:** Inserted `audit_log` node between `write_calendar` and `notify`. Compiled to 87 LoC. Smoke task (1-day leave, sufficient balance) passes all postconditions. Ready for human review.

**Human:** Approved.
