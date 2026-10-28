# Verification record

Recorded for the initial delivery on 28 October 2026.

| Check | Result |
| --- | --- |
| Backend tests | **31 passed**, 1 PostgreSQL-only test skipped |
| Backend application statement coverage | **94%**, seed loader excluded; not a measure of model quality |
| Frontend workflow tests | **7 passed** |
| TypeScript checking and Vite production build | **Passed** |
| Clean-checkout startup without a saved model | **Passed**: in-memory training, 18 seeded tickets, readable model metadata |
| Local SQLite migration upgrade | **Passed** |
| Alembic schema comparison after migration | **Passed**, no pending model/schema differences |
| PostgreSQL table DDL compilation | **Passed**, compilation only |
| Python source compilation | **Passed** |
| Compose and CI YAML / JSON metadata parsing | **Passed** |
| Demo classifier training/evaluation | **Completed**, 96 train / 24 validation / 24 test; metrics in `artifacts/metrics.json` |

The 38 passing automated tests cover creation, classification, retrieval, uncertain input, review gating, edited-draft approval invalidation, stale ticket versions, stale policy versions, rejection, resolution, audit history, API authentication, filtering/pagination, CSV formula protection, synthetic CFPB import, training vocabulary leakage, provider failure fallback, and the main UI actions.

## Not verified in this environment

- **Docker image builds and live PostgreSQL:** Docker was not available. PostgreSQL runtime testing is configured in GitHub Actions but has not been executed here. Compiling PostgreSQL DDL is not a substitute for that integration test.
- **Browser rendering / visual QA:** the managed preview environment could not run the Python backend (`No module named uvicorn`). The application build and jsdom component tests passed; desktop/mobile layout has not been inspected in a real browser here.
- **Live paid LLM calls:** no provider credentials were used. The Responses API adapter was tested with mocked success, timeout, malformed, incomplete, missing-citation, and invalid-citation responses.
- **Real CFPB data or production accuracy:** no real dataset was downloaded or used for training. The importer was tested on a synthetic CSV shaped like the public export.
- **Hosted deployment / remote GitHub repository:** the delivery is a complete source repository archive. It has not been published to a hosting service or pushed into a user's GitHub account.

The installed Starlette test client emitted a deprecation warning about its future HTTP client backend. Tests still passed with the pinned application dependencies. Revisit the test-client dependency when upgrading FastAPI/Starlette.

## Reproduce

```bash
.venv/bin/python -m pytest --cov=backend/app
npm --prefix frontend test
npm --prefix frontend run build
```

Use `.venv\Scripts\python.exe` for the Python command on Windows. See the root README for setup and `.github/workflows/ci.yml` for PostgreSQL/container validation once pushed to GitHub.
