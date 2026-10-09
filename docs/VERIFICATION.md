# Verification

Executed: 23 pytest tests; Ruff lint and formatting; SQLite Alembic upgrade and schema check; frontend Prettier and Vite production build. Browser checks cover registration, demo, two reviews, customer search, cohorts, threshold comparison, JSON/customer/cohort downloads, invalid/valid CSV import, session restore, mobile width and logout. Screenshots show synthetic data only.

Tests verify unique cohort buyer denominators, non-monotonic return, unavailable months, as_of exclusion, exact cents, excluded statuses, tie-aware RFM, strict inactivity boundary, empty populations, coverage, invalid monetary values, duplicates, auth/CSRF, owner isolation, frozen snapshots and replay conflict. No statistical model validation is needed because this release calculates descriptive analytics.

Not executed: Docker runtime, PostgreSQL runtime/concurrency, external synchronization or load testing. The included browser-smoke.cjs requires playwright-core and a compatible Chromium; run from project root with RETENTION_BROWSER and RETENTION_URL configured.
