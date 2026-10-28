# Running and deployment

## Local application

The root development launcher starts FastAPI and Vite as child processes. It prefers `.venv/bin/python` on Unix and `.venv/Scripts/python.exe` on Windows. `PYTHON_BIN` may select a different interpreter. The API binds to 127.0.0.1; the frontend's development server may listen on network interfaces for tooling, so run it only on a trusted development machine.

Vite proxies `/api` and `/health` to FastAPI. No frontend API key or provider key is baked into a build. The UI can hold a configured workspace key in memory; reloading clears it.

SQLite is stored at the repository root by default. Initial tables are created automatically for convenience when `AUTO_CREATE_SCHEMA=true`. For a fresh database managed by migrations instead:

```bash
AUTO_CREATE_SCHEMA=false .venv/bin/alembic -c backend/alembic.ini upgrade head
```

Use migrations from the start for persistent environments. Do not run the initial migration over an existing auto-created database and assume it is safe; first compare schema and back up the data. A local demo database can be recreated separately when preserving its tickets is unnecessary.

## Docker Compose

Compose runs PostgreSQL 17, one FastAPI process, and Nginx serving the compiled React application. Startup order is gated by health checks. The API image trains the synthetic model during its build and runs Alembic before Uvicorn. Database records persist in the named `postgres_data` volume. Code changes need `docker compose up --build`.

Ports bind to 127.0.0.1: the app is available at 8080 and API docs at 8000. The database is not exposed to the host network. The PostgreSQL default password is intentionally a local demo value. Choose a strong alphanumeric value in `.env` before using a shared host. If using special characters in connection URLs, URL-encode them in a custom `DATABASE_URL` and update Compose accordingly.

The application supports only one startup seeding process. Keep the current single worker for the demo. For multiple replicas, run migrations and seed operations as one separate provisioning step, then start replicas with `AUTO_CREATE_SCHEMA=false` and `SEED_DEMO=false`.

`docker compose down` retains the data volume. Deleting the volume destroys its tickets and policies; perform that separately only when you intend to discard them.

## Environment configuration

| Variable | Default / purpose |
| --- | --- |
| `DATABASE_URL` | Local SQLite; SQLAlchemy URL for other environments |
| `AUTO_CREATE_SCHEMA` | `true` locally, `false` in Compose |
| `SEED_DEMO` | `true`; seeds sample policies/tickets only when their tables are empty |
| `API_KEY` | Empty for local demo; shared workspace protection when set |
| `CORS_ORIGINS` | Explicit localhost origins, comma-separated |
| `MODEL_PATH` | `artifacts/classifier.joblib`; absent file triggers in-memory demo training |
| `DATA_DIR` | Repository `data` folder |
| `CLASSIFICATION_THRESHOLD` | `0.45`; configured review threshold |
| `RETRIEVAL_THRESHOLD` | `0.09`; minimum lexical similarity plus shared-term guard |
| `DRAFT_PROVIDER` | `extractive` or `openai` |
| `OPENAI_API_KEY` | Server-side key, blank by default |
| `OPENAI_MODEL` | Explicit Responses-compatible model ID, blank by default |
| `LLM_TIMEOUT_SECONDS` | `20`; bounded drafting request |
| `VITE_API_BASE_URL` | Optional frontend build-time API origin; omit with the proxy |

The default frontend includes no remote fonts, scripts, or images. Once dependencies are installed, the local demo requires no external service. LLM mode sends redacted complaint text and selected policies to the configured OpenAI API.

## Before a real deployment

The project supplies building blocks, not a production-readiness claim. Specifically add:

- HTTPS, OIDC/SSO, authenticated reviewer identities, and role-based access for policy writers/reviewers.
- Per-tenant authorization if more than one organization shares an instance.
- Rate limits and resource budgets for the API and LLM provider.
- A reviewed data-retention/deletion plan, encrypted backups, and monitoring.
- Organization-approved policies; the samples are not legal or financial guidance.
- Real-data evaluation, calibrated thresholds where appropriate, and explicit claim-level drafting checks.
- Background jobs, index caching, and database aggregate queries when load warrants them.
- A backup/restore rehearsal and schema migration process.

The audit history preserves events through the API but cannot verify identities in shared-key mode or prevent administrators from editing the database. API keys are compared with a constant-time function; this is not a substitute for proper user authentication.

No hosted website, GitHub repository, API account, paid service, or external delivery channel is created automatically by these files.
