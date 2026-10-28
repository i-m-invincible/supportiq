# Sources and provenance

These primary references informed API usage and the design. The source code, demo narratives, tickets, and policies in this repository were written for this project; they were not copied from another project repository.

- [FastAPI — testing lifecycle events](https://fastapi.tiangolo.com/advanced/testing-events/): use `TestClient` as a context manager so application lifespan initialization runs.
- [scikit-learn — Pipeline](https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html): combine transformations and an estimator in one fitting/prediction path.
- [scikit-learn — TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html): lexical feature extraction.
- [SQLAlchemy — version counters](https://docs.sqlalchemy.org/en/20/orm/versioning.html): detect stale ORM updates with a version column.
- [OpenAI — text generation](https://developers.openai.com/api/docs/guides/text): the Responses API and extraction of text from message output items; do not assume the first output item is always text.
- [CFPB — Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/): source for optional user-downloaded complaint data. Its complaints are not a statistical sample of all consumer experiences.

The importer uses CSV columns from the public export and records its output hash. No CFPB data download or real-data model training was performed for the initial delivery. The fictional policies do not represent CFPB rules, any real bank's policies, or legal obligations.

See `frontend/package-lock.json` and `backend/requirements.txt` for the dependency versions. Dependency licenses are separate from the project MIT license. No remote visual assets or fonts are required at runtime.
