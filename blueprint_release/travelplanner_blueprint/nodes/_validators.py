"""
Author-encoded validators backing each rule in
`constraint_rules/commonsense_constraints.json`.

Each entry maps `rule_id` → callable `(itinerary, goal, ctx) -> bool` that
returns True when the rule is satisfied. The set of rule_ids covered here
is exactly the set rebuttal §1.1's fair-comparison ablation injects into
the baseline system prompts — keeping enforcement and prompt-injection
identical is what makes the ablation comparison fair.

Validators only inspect the assembled itinerary + goal + ctx; they NEVER
call the LLM or any KB. This keeps `constraint_verify` deterministic.
"""

from typing import Any, Dict, Callable, List


def _all_meal_names(itinerary: List[Dict[str, Any]]) -> List[str]:
    names = []
    for day in itinerary:
        for slot in ("breakfast", "lunch", "dinner"):
            meal = day.get(slot)
            if meal and meal.get("name"):
                names.append(meal["name"])
    return names


def transport_budget_within_estimate(itinerary, goal, ctx):
    estimate = ctx["budget_estimate"]["average"]["flight"]
    total = sum((day.get("transportation") or {}).get("cost", 0) for day in itinerary)
    return total <= estimate * 1.05


def accommodation_comprehensive(itinerary, goal, ctx):
    nights_required = max(1, len(goal.date_range) - 1)
    nights_seen = 0
    for day in itinerary:
        acc = day.get("accommodation")
        if not acc:
            continue
        nights_seen += 1
        if acc.get("maximum_occupancy", 0) < goal.people_number:
            return False
        if acc.get("minimum_nights", 0) > nights_required:
            return False
    return nights_seen >= nights_required


def restaurant_global_uniqueness(itinerary, goal, ctx):
    names = _all_meal_names(itinerary)
    return len(names) == len(set(names))


def activity_city_consistency(itinerary, goal, ctx):
    for day in itinerary:
        city = (day.get("accommodation") or {}).get("city") or day.get("current_city")
        for attr in day.get("attractions", []):
            if attr.get("city") != city:
                return False
    return True


def entity_name_exact_matching(itinerary, goal, ctx):
    """Hotel / restaurant / attraction names must match the source CSV verbatim."""
    catalog = ctx["entity_catalog"]
    for day in itinerary:
        acc = day.get("accommodation")
        if acc and acc.get("hotel") and acc["hotel"] not in catalog["hotels"]:
            return False
        for slot in ("breakfast", "lunch", "dinner"):
            meal = day.get(slot)
            if meal and meal.get("name") and meal["name"] not in catalog["restaurants"]:
                return False
        for attr in day.get("attractions", []):
            if attr.get("name") and attr["name"] not in catalog["attractions"]:
                return False
    return True


def required_field_completeness(itinerary, goal, ctx):
    required = ("day", "current_city", "transportation", "accommodation", "breakfast", "lunch", "dinner", "attractions")
    for day in itinerary:
        for key in required:
            if day.get(key) is None:
                return False
    return True


def reasonable_city_route_planning(itinerary, goal, ctx):
    """current_city must change only when transport mode allows it."""
    last_city = None
    for day in itinerary:
        city = day.get("current_city")
        if last_city is not None and city != last_city:
            transport = day.get("transportation")
            if transport is None:
                return False
        last_city = city
    return True


def current_city_format_and_transport_consistency(itinerary, goal, ctx):
    """If transportation is present, its `to` must match current_city."""
    for day in itinerary:
        transport = day.get("transportation")
        if not transport:
            continue
        if transport.get("to") and transport["to"] != day.get("current_city"):
            return False
    return True


# rule_id → validator. rule_ids match the `id` field of
# constraint_rules/commonsense_constraints.json.
RULES: Dict[str, Callable] = {
    "transport_budget_within_estimate": transport_budget_within_estimate,
    "accommodation_comprehensive": accommodation_comprehensive,
    "restaurant_global_uniqueness": restaurant_global_uniqueness,
    "activity_city_consistency": activity_city_consistency,
    "entity_name_exact_matching": entity_name_exact_matching,
    "required_field_completeness": required_field_completeness,
    "reasonable_city_route_planning": reasonable_city_route_planning,
    "current_city_format_and_transport_consistency": current_city_format_and_transport_consistency,
}


# rule_id → category, mirrors the `category` field of
# commonsense_constraints.json. Used by constraint_verify to pick the
# replan target.
RULE_CATEGORY: Dict[str, str] = {
    "transport_budget_within_estimate": "transportation",
    "accommodation_comprehensive": "accommodation",
    "restaurant_global_uniqueness": "restaurant",
    "activity_city_consistency": "planning",
    "entity_name_exact_matching": "information_accuracy",
    "required_field_completeness": "information_accuracy",
    "reasonable_city_route_planning": "planning",
    "current_city_format_and_transport_consistency": "transportation",
}
