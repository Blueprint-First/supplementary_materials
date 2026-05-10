"""
Estimate the per-domain budget envelope from days × multipliers ×
(flight / hotel / restaurant unit prices).

Three modes (lowest / highest / average) and three day tiers (3 / 5 / 7)
with multipliers `{flight, hotel, restaurant}`. Attractions in the
TravelPlanner data are price-free, so the attraction sub-planner does
not consume an envelope here.
"""

from sca.engine import node, precondition, postcondition

from ..blueprint import BP


# Multipliers per day-tier and per-domain.
MULTIPLIERS = {
    3: {"flight": 2, "hotel": 3, "restaurant": 9},
    5: {"flight": 3, "hotel": 5, "restaurant": 15},
    7: {"flight": 4, "hotel": 7, "restaurant": 21},
}


def _select_tier(days: int) -> int:
    """Snap arbitrary day counts to the source's 3 / 5 / 7 tiers."""
    if days <= 3:
        return 3
    if days <= 5:
        return 5
    return 7


def _estimate(prices, mode):
    clean = [p for p in prices if p is not None and str(p) != "nan"]
    if not clean:
        return 0.0
    if mode == "lowest":
        return float(min(clean))
    if mode == "highest":
        return float(max(clean))
    return float(sum(clean)) / len(clean)


@node(BP)
@precondition(lambda ctx: ctx.get("goal") and ctx["goal"].budget_allocated > 0)
@postcondition(lambda ctx: ctx.get("budget_estimate") is not None
               and {"lowest", "highest", "average"} <= set(ctx["budget_estimate"].keys()))
def budget_estimation(ctx):
    """Compute lowest / highest / average budget envelopes per domain."""
    goal = ctx["goal"]
    days = max(1, len(goal.date_range))
    tier = _select_tier(days)
    mults = MULTIPLIERS[tier]

    flight_prices = ctx["flights_api"].prices_for(goal.cities, goal.date_range)
    hotel_prices = ctx["accommodations_api"].prices_for(goal.cities)
    restaurant_prices = ctx["restaurants_api"].prices_for(goal.cities)

    estimate = {}
    for mode in ("lowest", "highest", "average"):
        estimate[mode] = {
            "flight": _estimate(flight_prices, mode) * mults["flight"],
            "hotel": _estimate(hotel_prices, mode) * mults["hotel"],
            "restaurant": _estimate(restaurant_prices, mode) * mults["restaurant"],
        }
        estimate[mode]["total"] = sum(estimate[mode].values())

    ctx["budget_estimate"] = estimate
    ctx["budget_tier_days"] = tier
    return ctx
