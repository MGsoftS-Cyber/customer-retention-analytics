"""Observed purchase retention and deterministic, tie-aware RFM analytics.

No churn probabilities, lifetime-value prediction or automated campaigns.
All money aggregates in integer minor units; outputs format two decimals.
"""

from collections import Counter, defaultdict
from datetime import date
from math import ceil
from bisect import bisect_left, bisect_right

ENGINE_VERSION = "1.0.0"


def money(cents):
    return f"{cents // 100}.{cents % 100:02d}"


def month_index(day):
    return day.year * 12 + day.month - 1


def month_label(index):
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def score_map(values, inverse=False):
    """Midrank quintiles: identical values receive identical scores, all-equal gets 3."""
    ordered = sorted(values)
    result = {}
    for value in set(values):
        percentile = (bisect_left(ordered, value) + bisect_right(ordered, value)) / (2 * len(ordered))
        score = max(1, min(5, ceil(5 * percentile)))
        result[value] = 6 - score if inverse else score
    return result


def segment(customer, inactivity):
    # Explicit priority makes segment assignments reproducible.
    if customer["recency_days"] > 2 * inactivity:
        return "Long inactive"
    if customer["recency_days"] > inactivity:
        return "At risk"
    if customer["r_score"] >= 4 and customer["f_score"] >= 4 and customer["m_score"] >= 4:
        return "Champions"
    if customer["frequency"] == 1 and customer["recency_days"] <= 30:
        return "New buyers"
    if customer["f_score"] >= 4:
        return "Loyal buyers"
    return "Developing buyers"


def evaluate(data):
    cutoff = date.fromisoformat(data["as_of"])
    if str(cutoff) > data["coverage_end"] or str(cutoff) < data["quality"]["start"]:
        raise ValueError("Analysis date must be within the dataset's observed start and coverage end.")
    # Exclude future and non-completed records before *all* customer calculations.
    orders = [x for x in data["orders"] if x["status"] == "completed" and x["order_date"] <= str(cutoff)]
    groups = defaultdict(list)
    for x in orders:
        groups[x["customer_id"]].append(x)
    customers = []
    for identifier, items in sorted(groups.items()):
        first = min(x["order_date"] for x in items)
        last = max(x["order_date"] for x in items)
        cents = sum(x["amount_cents"] for x in items)
        customers.append(
            dict(
                customer_id=identifier,
                first_purchase=first,
                last_purchase=last,
                recency_days=(cutoff - date.fromisoformat(last)).days,
                frequency=len(items),
                monetary_cents=cents,
                monetary=money(cents),
                cohort=first[:7],
                active_months=sorted({x["order_date"][:7] for x in items}),
            )
        )
    maps = [
        score_map([x[field] for x in customers], inverse)
        for field, inverse in [("recency_days", True), ("frequency", False), ("monetary_cents", False)]
    ]
    for x in customers:
        for name, field, mapping in zip(
            ["r_score", "f_score", "m_score"], ["recency_days", "frequency", "monetary_cents"], maps
        ):
            x[name] = mapping[x[field]]
        x["rfm"] = f"{x['r_score']}{x['f_score']}{x['m_score']}"
        x["segment"] = segment(x, data["inactivity_days"])
    cohort_groups = defaultdict(list)
    for x in customers:
        cohort_groups[x["cohort"]].append(x)
    cohorts = []
    current_month = month_index(cutoff)
    for label, members in sorted(cohort_groups.items()):
        origin = month_index(date.fromisoformat(label + "-01"))
        cells = []
        for lead in range(data["cohort_horizon"] + 1):
            target = origin + lead
            # Month 0 is acquisition baseline; subsequent open/future months remain unavailable.
            observable = lead == 0 or target < current_month
            active = sum(month_label(target) in x["active_months"] for x in members) if observable else None
            cells.append(
                dict(
                    month=lead,
                    period=month_label(target),
                    active_customers=active,
                    rate=active / len(members) if active is not None else None,
                    state="baseline" if lead == 0 else "closed" if observable else "open_or_future",
                )
            )
        cohorts.append(dict(cohort=label, customers=len(members), cells=cells))
    counts = Counter(x["segment"] for x in customers)
    total = sum(x["amount_cents"] for x in orders)
    repeat = sum(x["frequency"] >= 2 for x in customers)
    inactive = sum(x["recency_days"] > data["inactivity_days"] for x in customers)
    # Reconstruct exact active-buyer counts per observed month, never distinct-order counts.
    monthly = []
    start_month = month_index(date.fromisoformat(data["quality"]["start"]))
    for m in range(start_month, current_month + 1):
        label = month_label(m)
        month_orders = [x for x in orders if x["order_date"][:7] == label]
        monthly.append(
            dict(
                month=label,
                buyers=len({x["customer_id"] for x in month_orders}),
                orders=len(month_orders),
                revenue=money(sum(x["amount_cents"] for x in month_orders)),
                partial=m == current_month,
            )
        )
    return dict(
        summary=dict(
            customers=len(customers),
            completed_orders=len(orders),
            revenue=money(total),
            repeat_buyers=repeat,
            repeat_purchase_rate=repeat / len(customers) if customers else None,
            inactive_customers=inactive,
            inactivity_rate=inactive / len(customers) if customers else None,
            average_order_value=money((total + len(orders) // 2) // len(orders)) if orders else None,
        ),
        customers=customers,
        cohorts=cohorts,
        monthly=monthly,
        segments=[dict(segment=k, customers=v) for k, v in sorted(counts.items())],
        warnings=[
            "Cohort acquisition means first observed completed order, not verified lifetime acquisition.",
            "Open/future follow-up months are unavailable, not zero retention.",
            "Inactivity and RFM segments are descriptive rules, not churn predictions.",
            "Cancelled and refunded orders are excluded entirely; partial refunds require upstream net amounts.",
        ],
        conventions=dict(
            retention="Any completed purchase in the exact cohort-age month, not consecutive survival",
            money="Integer cents; one store currency; no conversion",
            rfm="Tie-aware empirical midrank quintiles; all equal scores 3",
            coverage="User-declared completeness; no verification against source store",
        ),
    )
