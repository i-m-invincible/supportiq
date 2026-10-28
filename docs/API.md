# API guide

Interactive OpenAPI documentation: `http://localhost:8000/docs`.

Business endpoints use `/api/v1`. When `API_KEY` is nonempty, every business endpoint requires `X-API-Key`. `/health` is public and checks the database connection. Blank `API_KEY` is intended only for the local demonstration.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Readiness check |
| GET | `/api/v1/meta` | Model metadata and configuration flags; never provider keys |
| GET | `/api/v1/tickets` | Search/filter/page tickets |
| POST | `/api/v1/tickets` | Create and analyze a complaint |
| GET | `/api/v1/tickets/{id}` | Read ticket state |
| PATCH | `/api/v1/tickets/{id}` | Assign, reroute, change priority, resolve, reopen |
| POST | `/api/v1/tickets/{id}/draft` | Retrieve evidence and generate a draft |
| PUT | `/api/v1/tickets/{id}/draft` | Save a response edit; resets approval |
| POST | `/api/v1/tickets/{id}/review` | Approve or reject |
| GET | `/api/v1/tickets/{id}/audit` | Read chronological events |
| POST | `/api/v1/analyze` | Analyze without storing a ticket |
| GET | `/api/v1/policies` | List policies; `q` also returns ranked excerpts |
| POST | `/api/v1/policies` | Create a policy |
| PUT | `/api/v1/policies/{id}` | Update or deactivate a policy |
| GET | `/api/v1/analytics` | Counts, distributions, seven-day UTC trend |
| GET | `/api/v1/export/tickets.csv` | Export summary columns; escapes spreadsheet formulas |

## Complaint example

```bash
curl -X POST http://localhost:8000/api/v1/tickets \
  -H 'Content-Type: application/json' \
  -d '{"customer_name":"Demo Customer","subject":"Duplicate card purchase","body":"My credit card statement shows two charges for one merchant purchase. Please review the duplicate charge.","channel":"email"}'
```

Response fields include `id`, `version`, `analysis`, `category`, `priority`, `due_at`, `draft_text`, and `status`. Use the actual returned ID and version in subsequent requests; creation may already have recorded multiple internal updates.

Generate a draft:

```http
POST /api/v1/tickets/T-RETURNED-ID/draft
Content-Type: application/json

{"expected_version":2}
```

Approve after reading the draft and sources:

```http
POST /api/v1/tickets/T-RETURNED-ID/review
Content-Type: application/json

{"expected_version":3,"decision":"approve","reviewer":"Your Name","note":"Checked source relevance and claims."}
```

The versions above are illustrative. Always use the latest API result.

## Query and validation rules

`GET /tickets` supports `q` (max 200 characters), `status`, `priority`, `category`, `offset` (nonnegative), and `limit` (1–100). Search covers ID, subject, narrative, and customer name; `%` and `_` are treated literally, not as SQL wildcards.

Statuses: `open`, `in_review`, `approved`, `resolved`. Priority: `critical`, `high`, `medium`, `low`. Categories: `credit_card`, `bank_account`, `money_transfer`, `credit_reporting`, `debt_collection`, `loan`, `other`.

Review SLAs are demo operational choices: critical 2 hours, high 8, medium 24, low 48. They are not legal response deadlines.

Common errors:

- `401`: invalid or missing configured workspace key.
- `404`: missing ticket or policy.
- `409`: stale version, invalid workflow transition, or stale/unavailable policy evidence.
- `422`: input validation failure or unsupported citation edit.

Citation validation checks that referenced IDs belong to the retrieved evidence. It does not automatically determine whether each sentence is entailed by that evidence. Policies with no matching evidence cannot be used to approve an AI draft.

There are no automatic delivery endpoints, file-upload routes, or arbitrary URL-fetching routes.
