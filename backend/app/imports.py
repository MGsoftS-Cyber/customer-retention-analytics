"""Order-level CSV parsing and complete immutable dataset normalization."""

import csv
import io
from decimal import Decimal
from datetime import date
from .schemas import OrderInput

HEADER = ["customer_id", "order_id", "order_date", "amount", "status"]


def preview_orders(text):
    rows, errors = [], []
    try:
        reader = csv.DictReader(io.StringIO(text), strict=True)
        if reader.fieldnames != HEADER:
            return dict(valid=False, rows=[], errors=[dict(row=1, message="Use header: " + ",".join(HEADER))])
        seen = set()
        for number, raw in enumerate(reader, 2):
            if number > 10001:
                errors.append(dict(row=number, message="Maximum 10000 orders."))
                break
            try:
                item = OrderInput(**raw).model_dump(mode="json")
                if item["order_id"] in seen:
                    raise ValueError("Duplicate order ID. Import one aggregate record per order, not order lines.")
                seen.add(item["order_id"])
                rows.append(item)
            except (ValueError, TypeError):
                errors.append(dict(row=number, message="Invalid/duplicate order: check IDs, date, amount and status."))
    except csv.Error:
        errors.append(dict(row=1, message="Malformed CSV quoting."))
    if not rows:
        errors.append(dict(row=1, message="At least one valid order is required."))
    return dict(valid=bool(rows) and not errors, rows=rows, errors=errors)


def normalize(orders, coverage_end):
    rows = []
    seen = set()
    for item in orders:
        x = item.model_dump(mode="json")
        if x["order_id"] in seen:
            raise ValueError("Duplicate order IDs are not accepted.")
        seen.add(x["order_id"])
        if date.fromisoformat(x["order_date"]) > coverage_end:
            raise ValueError("Coverage end must include every imported order date.")
        x["amount_cents"] = int(Decimal(x.pop("amount")) * 100)
        rows.append(x)
    rows.sort(key=lambda x: (x["order_date"], x["order_id"]))
    if (coverage_end - date.fromisoformat(rows[0]["order_date"])).days > 1826:
        raise ValueError("Dataset coverage is limited to five years (1826 days).")
    warnings = [
        "Cohorts use first observed completed purchase; incomplete earlier history can misclassify acquisition."
    ]
    if (date.today() - coverage_end).days > 7:
        warnings.append("Coverage is stale. Analysis cannot go beyond the declared coverage end.")
    counts = {s: sum(x["status"] == s for x in rows) for s in ["completed", "cancelled", "refunded"]}
    return rows, dict(
        count=len(rows),
        start=rows[0]["order_date"],
        end=rows[-1]["order_date"],
        coverage_end=str(coverage_end),
        customer_ids=len({x["customer_id"] for x in rows}),
        statuses=counts,
        warnings=warnings,
    )
