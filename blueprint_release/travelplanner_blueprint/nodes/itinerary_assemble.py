"""
Assemble the four sub-plans into the TravelPlanner submission shape.

Per-day combination of transport + accommodation + dining + attraction
into a single ordered list.
"""

from sca.engine import node, precondition, postcondition

from ..blueprint import BP


@node(BP)
@precondition(lambda ctx: all(ctx.get(k) is not None for k in (
    "transport_plan", "accommodation_plan", "dining_plan", "attraction_plan"
)))
@postcondition(lambda ctx: ctx.get("itinerary") and len(ctx["itinerary"]) == max(1, len(ctx["goal"].date_range)))
def itinerary_assemble(ctx):
    """Combine the four sub-plans into one day-keyed itinerary."""
    transport = {seg["day"]: seg for seg in ctx["transport_plan"]}
    accommodation = {a["day"]: a for a in ctx["accommodation_plan"]}
    dining = {d["day"]: d for d in ctx["dining_plan"]}
    attractions = {a["day"]: a for a in ctx["attraction_plan"]}

    days = sorted({*transport.keys(), *accommodation.keys(), *dining.keys(), *attractions.keys()})
    itinerary = []
    for day in days:
        itinerary.append({
            "day": day,
            "current_city": (accommodation.get(day) or {}).get("city"),
            "transportation": transport.get(day),
            "accommodation": accommodation.get(day),
            "breakfast": (dining.get(day) or {}).get("breakfast"),
            "lunch": (dining.get(day) or {}).get("lunch"),
            "dinner": (dining.get(day) or {}).get("dinner"),
            "attractions": (attractions.get(day) or {}).get("attractions", []),
        })
    ctx["itinerary"] = itinerary
    return ctx
