# Engineering architecture

React → same-origin API → FastAPI/session/ownership → immutable dataset snapshot → pure engine → saved analysis and reports. Business writes and durable retry receipts commit atomically.

| File | Responsibility |
|---|---|
| backend/app/main.py | App, accounts, safe errors, headers, static assets |
| security.py | Argon2, opaque sessions, CSRF/origin checks, throttling |
| schemas.py | Strict bounded IDs, dates, statuses and monetary text |
| imports.py | Row preview, duplicate detection, cents and coverage normalization |
| engine.py | Cohorts, unique buyer metrics, tie-aware scores, segments |
| models.py | Owner/store/dataset/analysis/replay schema |
| services.py | Payload hash and atomic idempotency transaction |
| routes.py | Owner-scoped data, calculations, comparisons and exports |
| database.py / config.py | Request sessions and runtime settings |
| frontend/src/main.jsx | Six views, forms, heatmap, filters and reports |
| frontend/src/api.js | Same-origin JSON transport and in-memory CSRF |

User owns Store and LoginSession. Store has unique owner/name and fixed currency. Dataset belongs to Store and stores normalized orders, quality, coverage_end, source and fingerprint. Unique store/fingerprint avoids identical revisions; fingerprint includes source and coverage. Analysis belongs to Store and Dataset, preserving inputs/results/engine version. RequestRecord is unique by owner/scope/key.

Customers are analytical entities derived from stable customer IDs in the order dataset, not a separate editable CRM master. They have no login or contact profile. One store uses one currency; amounts are not converted. JSON snapshots bound the first release to 10000 orders and five years; larger implementations should use normalized/indexed facts and worker jobs.

Ownership is verified on every store, dataset and report access. UUID secrecy is not authorization. Single-owner access is implemented; shared workspaces/roles require new membership data and checks.
