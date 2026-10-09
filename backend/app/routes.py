"""Owner-scoped store, dataset, retention and export workflows."""

import csv
import io
import json
import hashlib
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select
from .database import get_db
from .security import current_user
from .models import Store, Dataset, Analysis
from .schemas import StoreInput, DatasetInput, CsvInput, RetentionInput, ComparisonInput
from .services import mutation
from .imports import preview_orders, normalize
from .engine import evaluate, ENGINE_VERSION

router = APIRouter(prefix="/api/v1")
Key = Header(min_length=1, max_length=100)


def owned_store(db, identifier, user):
    obj = db.scalar(select(Store).where(Store.id == identifier, Store.user_id == user.id))
    if not obj:
        raise HTTPException(404, "Store not found in your account.")
    return obj


def owned_analysis(db, identifier, user):
    obj = db.scalar(select(Analysis).join(Store).where(Analysis.id == identifier, Store.user_id == user.id))
    if not obj:
        raise HTTPException(404, "Analysis not found in your account.")
    return obj


def store_view(x):
    return dict(id=x.id, name=x.name, currency=x.currency)


def dataset_view(x):
    return dict(
        id=x.id,
        store_id=x.store_id,
        source=x.source,
        coverage_end=x.coverage_end,
        quality=x.quality,
        orders=x.orders,
        created_at=x.created_at,
    )


def analysis_view(x):
    return dict(
        id=x.id,
        store_id=x.store_id,
        dataset_id=x.dataset_id,
        inputs=x.inputs,
        results=x.results,
        engine_version=x.engine_version,
        created_at=x.created_at,
    )


@router.get("/stores")
def stores(user=Depends(current_user), db=Depends(get_db)):
    return [store_view(x) for x in db.scalars(select(Store).where(Store.user_id == user.id))]


@router.post("/stores", status_code=201)
def create_store(data: StoreInput, idempotency_key: str = Key, user=Depends(current_user), db=Depends(get_db)):
    def work():
        obj = Store(user_id=user.id, **data.model_dump())
        db.add(obj)
        db.flush()
        return store_view(obj)

    return mutation(db, user, "store", idempotency_key, data.model_dump(mode="json"), work)


@router.post("/imports/orders/preview")
def preview(data: CsvInput, user=Depends(current_user)):
    return preview_orders(data.csv_text)


@router.get("/stores/{identifier}/datasets")
def datasets(identifier: str, user=Depends(current_user), db=Depends(get_db)):
    owned_store(db, identifier, user)
    return [
        dataset_view(x)
        for x in db.scalars(select(Dataset).where(Dataset.store_id == identifier).order_by(Dataset.created_at.desc()))
    ]


@router.post("/stores/{identifier}/datasets", status_code=201)
def create_dataset(
    identifier: str, data: DatasetInput, idempotency_key: str = Key, user=Depends(current_user), db=Depends(get_db)
):
    owned_store(db, identifier, user)
    try:
        rows, quality = normalize(data.orders, data.coverage_end)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    body = data.model_dump(mode="json")
    fingerprint = hashlib.sha256(
        json.dumps(dict(orders=rows, source=data.source, coverage_end=str(data.coverage_end)), sort_keys=True).encode()
    ).hexdigest()

    def work():
        existing = db.scalar(select(Dataset).where(Dataset.store_id == identifier, Dataset.fingerprint == fingerprint))
        if existing:
            return dataset_view(existing)
        obj = Dataset(
            store_id=identifier,
            source=data.source,
            coverage_end=str(data.coverage_end),
            orders=rows,
            quality=quality,
            fingerprint=fingerprint,
        )
        db.add(obj)
        db.flush()
        return dataset_view(obj)

    return mutation(db, user, "dataset:" + identifier, idempotency_key, body, work)


@router.post("/stores/{identifier}/analyses", status_code=201)
def analyze(
    identifier: str, data: RetentionInput, idempotency_key: str = Key, user=Depends(current_user), db=Depends(get_db)
):
    store = owned_store(db, identifier, user)
    dataset = db.scalar(select(Dataset).where(Dataset.id == data.dataset_id, Dataset.store_id == identifier))
    if not dataset:
        raise HTTPException(404, "Dataset not found in this store.")
    inputs = dict(
        **data.model_dump(mode="json"),
        store=store_view(store),
        source=dataset.source,
        coverage_end=dataset.coverage_end,
        orders=dataset.orders,
        quality=dataset.quality,
    )
    try:
        results = evaluate(inputs)
        json.dumps(results, allow_nan=False)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None

    def work():
        obj = Analysis(
            store_id=identifier, dataset_id=dataset.id, inputs=inputs, results=results, engine_version=ENGINE_VERSION
        )
        db.add(obj)
        db.flush()
        return analysis_view(obj)

    return mutation(db, user, "analysis:" + identifier, idempotency_key, data.model_dump(mode="json"), work)


@router.get("/analyses")
def analyses(user=Depends(current_user), db=Depends(get_db)):
    return [
        analysis_view(x)
        for x in db.scalars(
            select(Analysis).join(Store).where(Store.user_id == user.id).order_by(Analysis.created_at.desc()).limit(100)
        )
    ]


@router.post("/comparisons")
def compare(data: ComparisonInput, user=Depends(current_user), db=Depends(get_db)):
    items = [owned_analysis(db, i, user) for i in data.analysis_ids]
    if len({(x.store_id, x.dataset_id, x.inputs["as_of"], x.inputs["cohort_horizon"]) for x in items}) != 1:
        raise HTTPException(422, "Compare the same store, dataset, analysis date and cohort horizon.")
    return dict(
        analyses=[analysis_view(x) for x in items],
        message="Compare inactivity thresholds on frozen data; this is not a campaign outcome test.",
    )


@router.get("/analyses/{identifier}/report")
def report(identifier: str, format: str = "json", user=Depends(current_user), db=Depends(get_db)):
    obj = owned_analysis(db, identifier, user)
    if format == "json":
        text, media = json.dumps(analysis_view(obj), indent=2), "application/json"
    elif format in {"customers", "cohorts"}:
        output = io.StringIO()
        writer = csv.writer(output)
        if format == "customers":
            keys = [
                "customer_id",
                "first_purchase",
                "last_purchase",
                "recency_days",
                "frequency",
                "monetary",
                "r_score",
                "f_score",
                "m_score",
                "rfm",
                "segment",
            ]
            writer.writerow(keys + ["currency"])
            for row in obj.results["customers"]:
                writer.writerow([row[k] for k in keys] + [obj.inputs["store"]["currency"]])
        else:
            writer.writerow(["cohort", "cohort_size", "age_month", "period", "active_customers", "rate", "state"])
            for cohort in obj.results["cohorts"]:
                for cell in cohort["cells"]:
                    writer.writerow(
                        [
                            cohort["cohort"],
                            cohort["customers"],
                            cell["month"],
                            cell["period"],
                            cell["active_customers"],
                            cell["rate"],
                            cell["state"],
                        ]
                    )
        text, media = output.getvalue(), "text/csv"
    else:
        raise HTTPException(422, "Use json, customers or cohorts format.")
    ext = "json" if format == "json" else "csv"
    return Response(
        text,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="retention-{format}-{obj.id}.{ext}"'},
    )


@router.post("/demo", status_code=201)
def demo(idempotency_key: str = Key, user=Depends(current_user), db=Depends(get_db)):
    def work():
        if db.scalar(select(Store).where(Store.user_id == user.id)):
            raise HTTPException(409, "Demo requires an empty store catalog.")
        store = Store(user_id=user.id, name="Northstar Online", currency="USD")
        db.add(store)
        db.flush()
        end = date.today()
        raw = []
        for customer in range(1, 121):
            first = end - timedelta(days=330 - (customer % 10) * 27)
            for purchase in range(1 + customer % 7):
                day = first + timedelta(days=purchase * (17 + customer % 19))
                if day > end:
                    break
                raw.append(
                    dict(
                        customer_id=f"C{customer:04d}",
                        order_id=f"O{customer:04d}-{purchase}",
                        order_date=str(day),
                        amount=f"{40 + (customer * 13 + purchase * 7) % 180}.00",
                        status="refunded" if customer % 17 == 0 and purchase == 0 else "completed",
                    )
                )
        data = DatasetInput(source="Synthetic demonstration", coverage_end=end, orders=raw)
        rows, quality = normalize(data.orders, end)
        dataset = Dataset(
            store_id=store.id,
            source=data.source,
            coverage_end=str(end),
            orders=rows,
            quality=quality,
            fingerprint=hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
        )
        db.add(dataset)
        db.flush()
        return dict(
            store_id=store.id, dataset_id=dataset.id, message="Synthetic orders created; no external store connected."
        )

    return mutation(db, user, "demo", idempotency_key, {}, work)
