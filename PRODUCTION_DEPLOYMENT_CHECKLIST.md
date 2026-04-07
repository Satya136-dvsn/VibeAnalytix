# Production Deployment Checklist

This checklist captures the minimum controls required before deploying VibeAnalytix to production.

## Security and Network

- [x] Set `ENFORCE_HTTPS=true` for API instances behind TLS termination.
- [x] Set `TRUSTED_HOSTS` to real domains (example: `api.vibeanalytix.com,localhost`).
- [x] Set `CORS_ALLOWED_ORIGINS` to real frontend origins only.
- [x] Ensure API is not publicly exposing Docker daemon or internal Redis/Postgres ports.
- [x] Use firewall rules so only API/worker services can access Redis and Postgres.

## Secrets and Configuration

- [x] Replace default `JWT_SECRET` with a long random secret.
- [x] Set `OPENAI_API_KEY` and/or `GEMINI_API_KEY` from secret manager, not committed files.
- [x] Disable API docs in production by setting `ENABLE_API_DOCS=false`.
- [x] Verify `DEBUG=false` in all API and worker containers.
- [x] Use environment-specific `.env` files managed outside source control.

## Rate Limiting and Abuse Prevention

- [x] Job submission is Redis sliding-window limited (`RATE_LIMIT_JOBS_PER_HOUR`).
- [x] Login endpoint is Redis sliding-window limited (`RATE_LIMIT_LOGIN_PER_MINUTE`).
- [x] Register endpoint is Redis sliding-window limited (`RATE_LIMIT_REGISTER_PER_HOUR`).
- [x] Repo chat endpoint is Redis sliding-window limited (`RATE_LIMIT_CHAT_PER_MINUTE`).
- [x] Set production values for all rate-limit variables based on expected traffic.

## Runtime Hardening

- [x] Trusted host validation enabled through FastAPI middleware.
- [x] Baseline security headers enabled on API responses.
- [x] Structured API error envelopes enabled for HTTP, validation, and unhandled errors.
- [x] Run services with non-root users in container images.
- [x] Configure CPU/memory limits for API/worker/beat containers.
- [x] Add readiness/liveness probes for all deployable services.

## Data and Persistence

- [x] Run database migrations before deployment (`alembic upgrade head`).
- [x] Enable database backups and retention policy.
- [x] Confirm pgvector extension exists in production database.
- [x] Verify Redis persistence/recovery mode fits your reliability requirements.

## Observability and Operations

- [ ] Send API and worker logs to a centralized log store.
- [ ] Add alerting for job failure spikes, queue depth, and timeout watchdog events.
- [ ] Add dashboards for request rate, latency, 4xx/5xx counts, and worker throughput.
- [x] Define rollback plan for failed releases.

## Deployment Validation

- [ ] Run backend tests before release (`pytest tests/`).
- [ ] Validate auth flow, job submission, progress polling, and results rendering in staging.
- [ ] Validate retry behavior for failed jobs in staging.
- [ ] Validate rate-limit responses return HTTP 429 with structured error envelope.
- [ ] Smoke test frontend-to-backend CORS behavior from production domain.

## Implemented Artifacts

- `docker-compose.prod.yml`
- `.env.production.example`
- `backend/entrypoint.api.sh`
- `scripts/backup-postgres.sh`
- `scripts/firewall-setup.sh`
- `scripts/rollback.sh`
