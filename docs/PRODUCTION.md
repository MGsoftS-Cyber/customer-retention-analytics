# Production operations and extensions

Compose binds localhost:8085 with internal PostgreSQL. Use HTTPS reverse proxy, COOKIE_SECURE=true, explicit ALLOWED_ORIGINS and a strong database password. Configure ingress request limits, timeouts, infrastructure rate limits and monitoring. Test backups with actual restores. Run migrations once before replicas; bundled entrypoint assumes one instance.

Execute PostgreSQL migration/concurrency tests on your runtime. Local SQLite checks do not prove PostgreSQL behavior. Docker runtime, database concurrency and production load were not verified in delivery. Add dependency review and security/load tests before launch.

This starter lacks shared-workspace roles, email verification, recovery, SSO, distributed rate limiting, billing, worker queues and live store connectors. Add these deliberately for commercial SaaS. JSON datasets/analyses and list responses are bounded but can be large; production should paginate metadata, store indexed facts and queue calculations.

Only pseudonymous customer IDs are needed. They may still identify people when linked to the source store. Apply your organization’s retention/deletion policy to datasets, analysis snapshots, exports and backups. This release does not provide self-service customer deletion or permissioned campaign sending. Avoid logging payloads, cookies or credentials. No legal compliance certification is implied.

A future commerce adapter must map stable IDs, aggregate one record per order, define status/refund timing, enforce one currency, declare observation cutoff and preserve source revisions. Subscription businesses need contract start/end/renewal events for true subscription churn. RFM inactivity alone cannot provide that.
