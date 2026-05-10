"""Leave request blueprint."""

from sca.engine import Blueprint, node, precondition, postcondition, retry, sequence

BP = Blueprint(name="leave_request", version="0.1.0")


@node(BP)
@postcondition(lambda ctx: ctx.get("request") is not None)
def parse_request(ctx):
    p = ctx["raw_request"]
    ctx["request"] = {
        "employee_id": p["employee_id"],
        "days": int(p["days"]),
        "start_date": p["start_date"],
        "end_date": p["end_date"],
    }
    return ctx


@node(BP)
@retry(max_attempts=3, backoff_seconds=1.0)
@precondition(lambda ctx: ctx.get("request") is not None)
@postcondition(lambda ctx: ctx.get("eligible") is not None)
def eligibility_check(ctx):
    req = ctx["request"]
    bal = ctx["hr_api"].get_leave_balance(req["employee_id"])
    overlap = any(
        not (req["end_date"] < bw["start"] or req["start_date"] > bw["end"])
        for bw in ctx["calendar_api"].list_blackout_windows()
    )
    ctx["eligible"] = bal >= req["days"] and not overlap
    if not ctx["eligible"]:
        ctx["reject_reason"] = f"insufficient balance ({bal} < {req['days']})" if bal < req["days"] else "blackout window overlap"
    return ctx


@node(BP)
@precondition(lambda ctx: ctx.get("eligible") is True)
@postcondition(lambda ctx: ctx.get("approved") is not None)
def approve(ctx):
    req = ctx["request"]
    m = ctx["hr_api"].request_manager_approval(req)
    chain = [m["approver_id"]]
    if not m["approved"]:
        ctx["approved"], ctx["approver_chain"] = False, chain
        return ctx
    if req["days"] >= 2:
        h = ctx["hr_api"].request_dept_head_approval(req)
        chain.append(h["approver_id"])
        ctx["approved"] = h["approved"]
    else:
        ctx["approved"] = True
    ctx["approver_chain"] = chain
    return ctx


@node(BP)
@retry(max_attempts=3, backoff_seconds=1.0)
@precondition(lambda ctx: ctx.get("approved") is True)
def write_calendar(ctx):
    ev = ctx["calendar_api"].create_leave_event(ctx["request"], approver_chain=ctx["approver_chain"])
    ctx["calendar_event_id"] = ev["id"]
    return ctx


@node(BP)
def notify_and_audit(ctx):
    summary = {
        "request": ctx["request"],
        "approver_chain": ctx.get("approver_chain"),
        "approved": ctx.get("approved"),
        "reject_reason": ctx.get("reject_reason"),
        "calendar_event_id": ctx.get("calendar_event_id"),
    }
    ctx["audit_log_id"] = ctx["audit_api"].append(summary)
    ctx["notification_id"] = ctx["notify_api"].send(**summary)
    return ctx


BP.graph = sequence(
    parse_request, eligibility_check, approve, write_calendar, notify_and_audit
)


if __name__ == "__main__":
    BP.run()
