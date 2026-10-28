# SupportIQ — AI Customer Support Intelligence Platform

An end-to-end portfolio project that turns a customer complaint into a classified, prioritized ticket, retrieves relevant policy evidence, and prepares a response for a person to review.

**React + TypeScript · FastAPI · scikit-learn · SQLAlchemy · PostgreSQL / SQLite · Docker**

The complete local workflow runs **without an API key**. Optional OpenAI drafting uses the Responses API and falls back to policy excerpts when unavailable. No messages are sent to customers.

## What you can do

- Create complaints from email, chat, web, or phone; automatically classify six financial-product categories.
- Inspect model scores and the words that contribute to a prediction; route uncertain cases for human classification.
- See explainable urgency rules, review deadlines, and a simple sentiment heuristic.
- Search, add, edit, and deactivate policy documents. Retrieval returns versioned excerpts with source IDs.
- Generate a draft, inspect its evidence, edit it, approve or reject it, and resolve or reopen the ticket.
- Track an audit history and prevent stale edits or approval against an outdated policy.
- Filter and paginate the inbox, export a spreadsheet-safe CSV, and explore live database analytics.
- Use the model playground without creating a ticket.
- Import a downloaded CFPB CSV, train a reproducible baseline, and generate evaluation reports.

**Scope:** this is a runnable, single-workspace demonstration, not a production customer-support service. It includes 144 hand-authored synthetic narratives, 18 fictional customer tickets, and 12 fictional policies. It is not trained on CFPB data by default. Synthetic scores are not real-world performance claims.

## Fastest start: Docker

Install Docker Desktop with Compose. From the extracted `supportiq` folder:

```bash
docker compose up --build
```

Open:

- App: **http://localhost:8080**
- API docs: **http://localhost:8000/docs**
- Health: **http://localhost:8080/health**

The first build downloads dependencies, trains the small demo classifier, migrates PostgreSQL, and seeds the workspace. Later starts reuse the database volume. The ports bind to your own computer by default.

```bash
docker compose down
```

This stops containers while retaining the database. See [deployment notes](docs/DEPLOYMENT.md) before exposing the application to others.

## Local setup on Windows (PowerShell)

Use **Python 3.12** and **Node.js 22.12+**. Run these inside the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
npm install --prefix frontend
Copy-Item .env.example .env
npm run dev
```

Open **http://localhost:5173**. The API starts at **http://127.0.0.1:8000/docs**. You do not need to activate the virtual environment. SQLite is the default local database. `Ctrl+C` stops both services.

## Local setup on macOS / Linux

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
npm ci --prefix frontend
cp .env.example .env
npm run dev
```

If port 5173 is occupied, Vite prints the available URL. The API uses port 8000; stop an existing service using it before running this project. Run frontend-only development with `npm --prefix frontend run dev` and the backend separately with `.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload`.

## Try the complete workflow

1. Open **Inbox** and select **Card charged twice for one order**, or create your own synthetic complaint.
2. Read the suggested category, priority explanation, and uncertainty score. Adjust routing if necessary.
3. Click **Generate draft**, then expand the policy evidence and check its relevance.
4. Edit the response and click **Save edits**. Enter a reviewer name and approve it.
5. Click **Mark resolved**. Open **Activity** to inspect the audit history.
6. Try an unrelated astronomy complaint: it should get an uncertain classification and no policy-based approval.
7. Edit a cited policy after generating another draft. Approval should be blocked until the draft is regenerated.

Approving records an internal review. There is no email, WhatsApp, CRM, or ticket-provider integration and no automatic delivery.

## What is actually “AI” here?

| Component | Implementation | Limit |
| --- | --- | --- |
| Complaint category | Learned TF-IDF + multiclass logistic regression | Small synthetic baseline; retrain and evaluate on real narratives |
| Uncertainty | Maximum class score with a 0.45 review threshold | Scores are not calibrated probabilities of correctness |
| Explanation | TF-IDF value × class coefficient for positive features | Local feature contribution, not a causal explanation |
| Urgency | Explicit keyword/phrase rules with reasons | Can miss negation, context, and unseen wording |
| Sentiment | Small positive/negative keyword heuristic | Not a trained sentiment model |
| Policy retrieval | TF-IDF cosine similarity over paragraph chunks | Lexical retrieval; no neural embeddings or vector database |
| Default draft | Retrieved policy excerpts in a deterministic template | Retrieval-assisted drafting, not an LLM in local mode |
| Optional LLM draft | OpenAI Responses API using retrieved context | Citation IDs are validated; claim-level faithfulness still requires human review |

The optional LLM mode is a retrieval-augmented generation (RAG) path. The no-key mode exercises the same evidence and review workflow using extracts. This distinction is deliberate and should be preserved in an interview.

## Training and real-data path

To explicitly save the demo model and metrics:

```bash
# macOS / Linux, from repository root
PYTHONPATH=backend .venv/bin/python -m app.ml.training
```

```powershell
# Windows PowerShell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m app.ml.training
```

If no model file exists, application startup trains the demo pipeline in memory. `artifacts/metrics.json` includes held-out scores, a confusion matrix, data hash, model version, and limitations. The included split is 96 train / 24 validation / 24 test, with disjoint exact narratives.

To use real complaint narratives:

1. Download a CSV export from the [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/). Include `Product` and `Consumer complaint narrative`. Use a sufficiently broad sample covering all six supported category groups.
2. Run the importer. It skips empty narratives, removes exact duplicates, samples each category with reservoir sampling, and creates stratified train / validation / test splits.
3. Train using those splits and restart the backend.

```bash
python scripts/import_cfpb.py --input /path/to/download.csv --max-per-class 2000
PYTHONPATH=backend .venv/bin/python -m app.ml.training --data data/cfpb.csv --dataset-kind cfpb
```

On Windows, replace the second command with `.\.venv\Scripts\python.exe -m app.ml.training --data data/cfpb.csv --dataset-kind cfpb` after setting `$env:PYTHONPATH` above.

The importer maps **product categories**, not complaint intent. It does not produce urgency or sentiment labels. Near-duplicate and time-based evaluation are still needed before claiming generalization. CFPB data reflects submitted complaints, not a representative sample of all customers.

See [the model card](docs/MODEL_CARD.md) for evaluation design and limitations.

## Optional LLM drafting

Edit `.env` at the repository root:

```dotenv
DRAFT_PROVIDER=openai
OPENAI_API_KEY=your_api_project_key
OPENAI_MODEL=your_responses_compatible_model
```

Restart the backend, or recreate the API container. Model availability depends on your API project; there is no hard-coded paid model. **API billing is separate from ChatGPT subscriptions.** Never put an LLM key in frontend code. Missing configuration, timeouts, malformed responses, incomplete responses, and invalid citation IDs produce an explicit extractive fallback.

Outbound complaint text has best-effort email / long-number redaction; this is **not** a complete anonymizer. Names, addresses, context, and policy text may remain. Use synthetic data unless you have an appropriate data-handling process. No live paid API call was made during development; provider behavior was tested with mocked responses.

## Repository map

```text
backend/app/             API, database models, validation, seed loader
backend/app/ml/          Training and evaluation pipeline
backend/app/services/    Classification, urgency, retrieval, drafting
backend/tests/           Workflow, model, import and PostgreSQL tests
backend/alembic/         Versioned schema migration
frontend/src/            React dashboard, inbox, policies and model lab
frontend/src/test/       UI workflow tests
data/                    Synthetic training data and demo fixtures
artifacts/               Evaluation reports; local model artifacts ignored
scripts/                 Development launcher and CFPB importer
docs/                    Architecture, API, model card, deployment, interview guide
.github/workflows/       Backend, frontend and Docker CI
compose.yaml             PostgreSQL + FastAPI + React/Nginx
```

## Verification

```bash
.venv/bin/python -m pytest --cov=backend/app
npm --prefix frontend test
npm --prefix frontend run build
```

Windows: use `.\.venv\Scripts\python.exe -m pytest --cov=backend/app` for the first command.

[VALIDATION.md](docs/VALIDATION.md) records the checks actually run and the remaining environment limits. A configured GitHub Actions workflow also exercises PostgreSQL and Docker once this repository is pushed; its presence is not a claim that CI has already run.

## Put it on your GitHub

The download is a complete source archive. Create an **empty** repository named `supportiq` on your own GitHub account, then run from this folder:

```bash
git init
git add .
git commit -m "Build SupportIQ customer support intelligence platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/supportiq.git
git push -u origin main
```

Keep `.env`, databases, customer exports, and downloaded complaint datasets out of Git. The project was built with AI coding assistance; learn and customize it before presenting it as work you can explain. [INTERVIEW_GUIDE.md](docs/INTERVIEW_GUIDE.md) provides a walkthrough and focused questions.

## License and sources

Original project code is under [MIT](LICENSE). Third-party dependencies retain their own licenses. The bundled fixture data and fictional policies were authored for this demonstration. CFPB data is not redistributed in this repository. Primary references and dataset provenance are in [SOURCES.md](docs/SOURCES.md).
