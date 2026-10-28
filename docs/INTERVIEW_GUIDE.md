# SupportIQ interview guide

## A clear 60-second explanation

“SupportIQ helps a support agent process financial-service complaints. A FastAPI backend classifies each complaint with a TF-IDF and logistic regression pipeline. Separate rules flag urgency and estimate sentiment. When the agent requests a response, the application retrieves relevant policy paragraphs and creates a cited draft. The agent can edit, approve, reject, and resolve it through a React dashboard. SQL stores the tickets and audit events, and version checks prevent stale edits. The project runs without an API key using policy extracts, with an optional LLM drafting path. The included dataset is synthetic; I would evaluate on real complaints before claiming deployment accuracy.”

Use this after you can explain and demonstrate each component. Describe AI coding assistance honestly, and distinguish your own changes and experiments from the generated starting point.

## A five-minute demo

1. **Overview:** show counts from the database, the seven-day chart, and the review queue. Explain that they are based on demo records.
2. **Create a complaint:** use a duplicate card charge. Inspect category score, urgency, feature terms, and review SLA.
3. **Generate a draft:** open a citation and compare the paragraph with the response.
4. **Edit and approve:** show that edits must be saved, enter your name, approve, and resolve. Nothing is emailed.
5. **Show a failure:** try an unrelated telescope complaint, or change a source policy before approval. Explain why the system asks for another review.
6. **Show code and tests:** follow the request from the route to the classifier, retrieval, draft service, and transaction. Show one concurrency test and one provider-failure test.

## Questions you should be able to answer

| Question | What your answer should cover |
| --- | --- |
| Why this project? | Complaints contain unstructured text, while support operations need structured routing, priorities, and auditable responses. |
| Why TF-IDF and logistic regression? | Cheap, fast CPU baseline; measurable and explainable; compare against stronger models only after establishing a baseline. |
| Why not just use a chatbot? | The task includes persistent tickets, policy management, review states, version checks, and source inspection. |
| What does TF-IDF measure? | Term frequency adjusted by how common a term is across training documents; bigrams capture short phrases. |
| Why use a Pipeline? | Training-only preprocessing and consistent inference vocabulary/order; avoid fitting vocabulary on test data. |
| Why is logistic regression suitable for text? | Sparse high-dimensional input and linear class scores; regularization controls weights. |
| Is 80% confidence the same as 80% correctness? | No. It is a model score. Calibration and representative evaluation are needed to interpret it as reliability. |
| What happens with unrelated text? | A low maximum score or no known features triggers `other`; retrieval may abstain, and source-free drafts cannot be approved. This is imperfect out-of-domain detection. |
| How do you calculate urgency? | Transparent phrase rules with explanations. It is not learned and may mishandle negation. |
| What is RAG here? | Retrieve policy chunks, pass them to an optional LLM, and produce a cited draft. Default mode uses exact extracts rather than a generative model. |
| Why chunk policies? | Focus evidence on a paragraph rather than a whole document; maintain stable policy/chunk/version metadata. |
| Why cosine similarity? | L2-normalized TF-IDF vectors compare weighted term overlap without raw document-length dominance. |
| What does the category boost do? | A small ranking bonus after real lexical evidence, so a predicted category cannot invent a source match. |
| Can a citation be wrong? | Yes. A valid ID only proves that a source was retrieved. It does not prove that every generated sentence is supported. |
| What if the provider fails? | Use a deterministic cited extractive fallback and show the reason. Never silently pretend the LLM succeeded. |
| How do you reduce prompt injection? | Treat complaint and policy text as untrusted input, separate instructions from data, expose no action tools, validate citations, and require review. This does not prove immunity. |
| What if two agents edit one ticket? | `expected_version` rejects stale clients; SQLAlchemy also checks the version in the update condition. |
| What if a policy changes? | Citation snapshots record the version. Approval checks the current active version and requests regeneration if it changed. |
| Why PostgreSQL and SQLite? | SQLite lowers local setup effort; PostgreSQL supports a shared service. Both use the same ORM and migration schema. |
| How would you evaluate it? | Macro F1 and per-class recall for routing, calibration and abstention coverage, retrieval recall/ranking on labeled queries, and claim-level human assessment for drafts. |
| Why not quote the synthetic accuracy? | The small authored test set is easy and not representative. Use it only as a smoke check. |
| What would you change for production? | Real identities/roles, privacy controls, evaluation, monitoring, rate limits, background jobs, cached retrieval, SQL aggregates, and approved policies. |

## Learn the code in this order

1. `backend/app/models.py`: understand one ticket and its related events.
2. `backend/app/main.py`: trace creation, draft generation, approval, and resolution.
3. `backend/app/ml/training.py`: explain the split, vectorizer, classifier, metrics, and threshold.
4. `backend/app/services/intelligence.py`: understand class scores, contributions, rules, and redaction limits.
5. `backend/app/services/retrieval.py`: manually calculate a small term-overlap example and explain the unrelated-query guard.
6. `backend/app/services/drafting.py`: compare extractive and LLM paths and inspect error handling.
7. `frontend/src/components/TicketDetail.tsx`: follow versioned mutations and the human review controls.
8. `backend/tests/test_workflow.py`: break an invariant intentionally and watch its regression test catch it.

## Improvements that would make this project your own

Choose two or three and keep an experiment log:

- Import real CFPB data, audit the mapping, and compare logistic regression with a linear SVM.
- Build a labeled policy retrieval set and compare lexical retrieval with sentence embeddings. Report recall@k and incorrect-match rates.
- Annotate a small urgency dataset, including negation and hard cases, and compare rules with a trained model.
- Add real OIDC sign-in and separate agent/reviewer/policy-editor roles.
- Add feedback capture and measure category overrides across different score bands.
- Improve multilingual handling for a carefully defined language pair and evaluate it separately.

## Honest resume wording

After running and understanding the system, adapt these to what you actually completed:

- Developed a customer-support workflow using FastAPI, React, and SQL persistence, with complaint routing, policy retrieval, and human-reviewed response drafts.
- Implemented a TF-IDF/logistic-regression baseline with held-out evaluation, uncertainty handling, and feature-contribution inspection.
- Added versioned policy citations, optimistic concurrency checks, audit events, and automated workflow tests.

Only claim real-data scores, a live deployment, embeddings, a trained sentiment model, or production users if you later build and verify those parts. Do not turn synthetic test results into an accuracy claim.
