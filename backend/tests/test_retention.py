"""Denominators, chronology, money, ownership and saved snapshots."""

from datetime import date
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.engine import evaluate, score_map, money
from app.imports import normalize, preview_orders
from app.schemas import OrderInput, DatasetInput


def row(c, oid, day, amount="10.00", status="completed"):
    return dict(customer_id=c, order_id=oid, order_date=day, amount=amount, status=status)


def data(rows, asof="2026-04-15", coverage="2026-04-30", inactive=90):
    d = DatasetInput(source="test", coverage_end=coverage, orders=rows)
    normalized, q = normalize(d.orders, d.coverage_end)
    return dict(
        orders=normalized, quality=q, coverage_end=coverage, as_of=asof, inactivity_days=inactive, cohort_horizon=4
    )


def test_cohort_unique_buyers_denominator():
    out = evaluate(
        data(
            [
                row("A", "1", "2026-01-05"),
                row("B", "2", "2026-01-06"),
                row("A", "3", "2026-02-01"),
                row("A", "4", "2026-02-02"),
                row("A", "5", "2026-03-01"),
            ]
        )
    )
    assert [x["rate"] for x in out["cohorts"][0]["cells"]] == [1, 0.5, 0.5, None, None]
    assert out["cohorts"][0]["cells"][1]["active_customers"] == 1
    assert out["summary"]["repeat_purchase_rate"] == 0.5


def test_return_after_gap():
    out = evaluate(data([row("A", "1", "2026-01-01"), row("A", "2", "2026-03-01")]))
    assert [x["rate"] for x in out["cohorts"][0]["cells"][:3]] == [1, 0, 1]


def test_asof_excludes_later_orders():
    out = evaluate(
        data([row("A", "1", "2026-01-01"), row("A", "2", "2026-03-01"), row("B", "3", "2026-04-01")], asof="2026-02-15")
    )
    assert out["summary"]["customers"] == 1 and out["summary"]["revenue"] == "10.00"
    assert out["customers"][0]["frequency"] == 1 and out["customers"][0]["recency_days"] == 45


def test_exact_money_and_status_exclusions():
    out = evaluate(
        data(
            [
                row("A", "1", "2026-01-01", "0.10"),
                row("A", "2", "2026-02-01", "0.20"),
                row("B", "3", "2026-01-02", "999", "cancelled"),
                row("C", "4", "2026-01-03", "999", "refunded"),
            ]
        )
    )
    assert out["summary"]["revenue"] == "0.30" and out["summary"]["customers"] == 1
    assert out["summary"]["average_order_value"] == "0.15" and money(1) == "0.01"


def test_ties_and_recency_direction():
    assert score_map([5, 5, 5]) == {5: 3}
    assert score_map([1, 2, 3, 4, 5]) == {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
    assert score_map([1, 2, 3, 4, 5], True)[1] == 5
    assert score_map([1, 1, 2, 3])[1] == 2


def test_inactivity_boundary():
    out = evaluate(data([row("A", "1", "2026-01-15"), row("B", "2", "2026-01-14")]))
    by = {x["customer_id"]: x for x in out["customers"]}
    assert by["A"]["recency_days"] == 90 and by["A"]["segment"] != "At risk"
    assert by["B"]["segment"] == "At risk" and out["summary"]["inactive_customers"] == 1


def test_long_inactive():
    assert evaluate(data([row("A", "1", "2026-01-01")], inactive=30))["customers"][0]["segment"] == "Long inactive"


def test_empty_completed_history():
    out = evaluate(data([row("A", "1", "2026-01-01", status="refunded")]))
    assert out["summary"]["customers"] == 0 and out["summary"]["repeat_purchase_rate"] is None
    assert out["customers"] == out["cohorts"] == []


@pytest.mark.parametrize("asof", ["2025-12-31", "2026-05-01"])
def test_outside_coverage(asof):
    with pytest.raises(ValueError):
        evaluate(data([row("A", "1", "2026-01-01")], asof=asof))


def test_duplicates_and_invalid_coverage():
    with pytest.raises(ValueError):
        data([row("A", "1", "2026-01-01"), row("B", "1", "2026-01-02")])
    with pytest.raises(ValueError):
        data([row("A", "1", "2026-04-30")], coverage="2026-04-01")


@pytest.mark.parametrize("amount", ["NaN", "-1", "1.001", "1e2", "1000000001", "=SUM(1,2)"])
def test_invalid_money(amount):
    with pytest.raises(ValidationError):
        OrderInput(**row("A", "1", "2026-01-01", amount))


def test_preview_validation():
    h = "customer_id,order_id,order_date,amount,status\n"
    assert preview_orders(h + "A,O1,2026-01-01,10,completed")["valid"]
    assert not preview_orders(h + "A,O1,2026-01-01,10,completed\nA,O1,2026-01-02,10,completed")["valid"]
    assert not preview_orders("wrong,header\n1,2")["valid"]


def login(client, email="owner@example.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "Retention!2026"})
    assert r.status_code == 201, r.text
    return {"X-CSRF-Token": r.json()["csrf_token"], "Origin": "http://localhost:8005", "Idempotency-Key": str(uuid4())}


def seed(client):
    h = login(client)
    d = client.post("/api/v1/demo", headers=h)
    assert d.status_code == 201, d.text
    b = dict(
        dataset_id=d.json()["dataset_id"],
        as_of=str(date.today()),
        scenario_name="Base review",
        inactivity_days=90,
        cohort_horizon=6,
    )
    return h, d.json(), b


def test_reports_replay_and_conflict(client):
    h, d, b = seed(client)
    url = f"/api/v1/stores/{d['store_id']}/analyses"
    h["Idempotency-Key"] = str(uuid4())
    a = client.post(url, json=b, headers=h)
    assert a.status_code == 201, a.text
    assert client.post(url, json=b, headers=h).json()["id"] == a.json()["id"]
    assert client.post(url, json={**b, "inactivity_days": 30}, headers=h).status_code == 409
    for fmt in ["json", "customers", "cohorts"]:
        r = client.get(f"/api/v1/analyses/{a.json()['id']}/report?format={fmt}")
        assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]


def test_owner_isolation(client):
    h, d, b = seed(client)
    a = client.post(f"/api/v1/stores/{d['store_id']}/analyses", json=b, headers=h).json()
    client.cookies.clear()
    other = login(client, "other@example.com")
    assert client.get(f"/api/v1/stores/{d['store_id']}/datasets").status_code == 404
    assert client.post(f"/api/v1/stores/{d['store_id']}/analyses", json=b, headers=other).status_code == 404
    assert client.get(f"/api/v1/analyses/{a['id']}/report").status_code == 404
    assert client.get("/api/v1/analyses").json() == []


def test_dataset_dedup_and_frozen_snapshot(client):
    h, d, b = seed(client)
    url = f"/api/v1/stores/{d['store_id']}"
    body = dict(source="upload", coverage_end=str(date.today()), orders=[row("X", "O1", "2026-01-01")])
    h["Idempotency-Key"] = str(uuid4())
    dataset = client.post(url + "/datasets", json=body, headers=h).json()
    h["Idempotency-Key"] = str(uuid4())
    assert client.post(url + "/datasets", json=body, headers=h).json()["id"] == dataset["id"]
    b["dataset_id"] = dataset["id"]
    h["Idempotency-Key"] = str(uuid4())
    a = client.post(url + "/analyses", json=b, headers=h).json()
    body["orders"].append(row("X", "O2", "2026-02-01"))
    h["Idempotency-Key"] = str(uuid4())
    assert client.post(url + "/datasets", json=body, headers=h).status_code == 201
    saved = client.get(f"/api/v1/analyses/{a['id']}/report").json()
    assert saved["inputs"] == a["inputs"] and saved["results"] == a["results"]


def test_comparison_rules(client):
    h, d, b = seed(client)
    url = f"/api/v1/stores/{d['store_id']}/analyses"
    a = client.post(url, json=b, headers=h).json()
    h["Idempotency-Key"] = str(uuid4())
    c = client.post(url, json={**b, "inactivity_days": 30}, headers=h).json()
    assert client.post("/api/v1/comparisons", json={"analysis_ids": [a["id"], c["id"]]}, headers=h).status_code == 200
    h["Idempotency-Key"] = str(uuid4())
    e = client.post(url, json={**b, "cohort_horizon": 3}, headers=h).json()
    assert client.post("/api/v1/comparisons", json={"analysis_ids": [a["id"], e["id"]]}, headers=h).status_code == 422


def test_auth_csrf_preview(client):
    assert client.get("/api/v1/stores").status_code == 401
    h = login(client)
    assert client.post("/api/v1/stores", json={"name": "store"}, headers={"Idempotency-Key": "a"}).status_code == 403
    assert client.post("/api/v1/imports/orders/preview", json={"csv_text": "wrong"}, headers=h).json()["valid"] is False
