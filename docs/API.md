# API contracts

Base prefix /api. POST /auth/register and /auth/login return user, CSRF token and opaque HttpOnly cookie. GET /auth/session restores; POST /auth/logout revokes. Writes require X-CSRF-Token and a trusted Origin. Durable store/dataset/analysis/demo mutations additionally require Idempotency-Key (1–100 chars). Same key/payload replays saved response; changed payload conflicts. /docs provides live OpenAPI.

| Method/path | Purpose |
|---|---|
| GET /health | Liveness |
| GET, POST /v1/stores | List/create store and fixed currency |
| POST /v1/imports/orders/preview | Parsed rows and row errors |
| GET, POST /v1/stores/{id}/datasets | Immutable order revisions |
| POST /v1/stores/{id}/analyses | Calculate/save retention snapshot |
| GET /v1/analyses | Latest 100 owner analyses |
| POST /v1/comparisons | 2–10 distinct matching reviews |
| GET /v1/analyses/{id}/report?format=json | Full saved context/results |
| GET /v1/analyses/{id}/report?format=customers | Customer CSV with currency |
| GET /v1/analyses/{id}/report?format=cohorts | Long-form cohort CSV; blanks unavailable |
| POST /v1/demo | Synthetic store/orders; empty catalog only |

Analysis payload:
```json
{"dataset_id":"owned-id","scenario_name":"Retention review","as_of":"2026-09-30","inactivity_days":90,"cohort_horizon":6}
```
Dataset payload:
```json
{"source":"Store export","coverage_end":"2026-09-30","orders":[{"customer_id":"C001","order_id":"O001","order_date":"2026-01-01","amount":"49.90","status":"completed"}]}
```
Preview takes {"csv_text":"customer_id,order_id,order_date,amount,status\n..."}. Comparison takes {"analysis_ids":["id1","id2"]}; same store, dataset, date and horizon required, allowing threshold/name changes.

401 unauthenticated, 403 CSRF/origin failure, 404 absent/foreign ownership, 409 duplicate/replay conflict, 422 invalid contract and 429 throttle. Preview returns row errors as response data; valid=false must block saving. CSV identifiers cannot contain formula prefixes, and free-form source/name labels are not included in CSV exports.
