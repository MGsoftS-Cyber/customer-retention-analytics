# Contributing

Understand docs/METHODOLOGY.md before changing calculations. Keep analytics in engine.py, CSV parsing in imports.py, contracts in schemas.py, HTTP ownership in routes.py and transactional replay in services.py. React coordinates workflows; do not recalculate monetary or cohort definitions in UI.

From backend: install requirements-dev.txt, then run `ruff check app tests migrations`, `ruff format --check app tests migrations`, `pytest -q`, `alembic upgrade head`, `alembic check`. From frontend: `npm ci`, `npm run format:check`, `npm run build`. Use an isolated database for migration work.

Add meaningful tests when changing denominators, time boundaries, tie handling, refunds, ownership or retries. Preserve old datasets and analysis outputs. Version engine semantics deliberately. Schema changes require new Alembic revisions; never rewrite deployed old migrations. Comments should explain the business definition and why ordering/ownership matters.

Create your GitHub repository, unpack source, initialize git and push. The included CI validates Python, migrations, frontend and image build. Do not commit databases, credentials, .env or customer data. PR descriptions should explain behavior, methodology changes, validation and limits.
