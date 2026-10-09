# RetentionIQ — Customer Retention Analytics

Idea 3: an independent analytics application for online stores and businesses that want to understand repeat purchases, monthly purchase cohorts and inactive customer groups. Python 3.12/FastAPI, JavaScript/React 19, SQLAlchemy/Alembic, SQLite locally and PostgreSQL 17 in Compose. Version 1.0.0, MIT license.

## Start with Docker

Copy `.env.example` to `.env`, replace POSTGRES_PASSWORD with a strong URL-safe value, run `docker compose up --build`, then open http://localhost:8085. Register your own account; no default credentials. Load demo data and Analyze customer retention.

Docker and PostgreSQL runtime were not executed in the delivery environment. Test them on the target system before deployment.

## Local development

Backend (Python 3.12):
```sh
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8005
```
Frontend in a second terminal (Node 24):
```sh
cd frontend
npm ci
npm run dev
```
Open http://localhost:5178. Vite proxies /api to 8005. For a single-server preview, run `npm run build` in frontend and open http://localhost:8005. SQLite defaults to backend/retention.db. Live OpenAPI is at /docs.

## Workflow

1. Create a store and choose USD, EUR, GBP or DZD. No currency conversion.
2. Upload order CSV with exact header `customer_id,order_id,order_date,amount,status`.
3. Review row errors, source label and coverage end; save an immutable dataset.
4. Select analysis date, inactivity threshold (7–365 days) and cohort horizon (1–12 months).
5. Save a review; inspect summary, cohort heatmap and RFM segments.
6. Search customer IDs; download customer CSV, cohort CSV or complete JSON.
7. Compare inactivity thresholds on the same frozen dataset, date and horizon.

`examples/orders.csv` is synthetic. Each order appears once, not once per line item. Stable customer IDs suffice; no names/emails are required. All money input uses nonnegative decimal text with at most two decimal places; the engine sums integer minor units. Completed orders count; cancelled and fully refunded records do not. Partial refunds must be netted upstream into completed amounts under a documented policy.

## Definitions and limits

Customers means customers with at least one completed order on/before as_of. Repeat rate means buyers with at least two orders divided by all purchasing buyers, including immature new buyers. Cohorts use first observed completed purchase, not verified lifetime acquisition. Follow-up retention means a purchase in that exact month, not consecutive survival. Current/future follow-up months stay unavailable. M0 is acquisition baseline.

RFM is descriptive, with tie-aware empirical ranks; inactive is a strict recency threshold. No churn prediction, future CLV, subscription renewal logic, campaign sending, live commerce connector, shared-team access or billing is included. Customer IDs are pseudonymous, not guaranteed anonymous. Store owner controls dataset meaning/completeness.

Read docs/METHODOLOGY.md for precise formulas; docs/ARCHITECTURE.md, API.md, PRODUCTION.md and VERIFICATION.md for engineering detail. Screenshots are in docs. CONTRIBUTING.md explains review and checks.
