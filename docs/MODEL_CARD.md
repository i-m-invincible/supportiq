# Model card

## Purpose and training data

The baseline routes English financial-service complaints into six broad groups: bank accounts, credit cards, money transfers, credit reporting, debt collection, and loans. `other` is an abstention output, not a trained seventh class.

The included dataset is hand-authored synthetic text: 16 training, 4 validation, and 4 test narratives per category (96 / 24 / 24 total). Demo tickets are separate fixtures, not evaluation data. All names and scenarios are fictional. No real customer records or CFPB narratives are bundled.

## Features and estimator

`TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, max_features=40000)` feeds `LogisticRegression(C=4.0, class_weight='balanced', max_iter=1500, random_state=42)` inside a scikit-learn Pipeline.

The vectorizer learns vocabulary and IDF only from the training split. The classifier is not fit on validation or test data. Input rows are checked for exact normalized duplicates and required class coverage in each split. The model returns class probabilities, but their calibration has not been established.

At inference, the largest score must reach 0.45 and the text must contain some known features; otherwise the routing category is `other` and the human-review flag is set. The threshold is a configurable demonstration choice, not a statistically optimized deployment threshold.

Positive feature contributions are computed as TF-IDF values multiplied by the predicted class coefficient. They indicate which observed features support that class score; they do not explain all contrastive class effects or establish causality.

## Evaluation and reporting

`artifacts/metrics.json` reports accuracy, macro F1, a per-class report, a confusion matrix, acceptance coverage, and accepted-only accuracy. Coverage is the fraction of examples whose maximum class score exceeds the threshold. Metrics use the same split definitions and model that the training command saves.

The included test split is very small and intentionally straightforward. A perfect score on these 24 examples is a fixture smoke check, **not** evidence of generalization or a resume-ready accuracy claim. Scores can also move with library versions. The artifact records the data hash and scikit-learn version.

The runtime loads only a trusted local joblib artifact and requires its scikit-learn version to match. Never load an arbitrary downloaded pickle/joblib: it can execute code. Retrain when changing scikit-learn versions.

## CFPB extension

The importer works on a user-downloaded CSV, maps product labels to the six groups, skips empty narratives, performs exact-text deduplication before splitting, samples each class with reservoir sampling, and assigns 70% / 15% / 15% splits. It does not automatically fetch data.

The default cap is 2,000 examples per category. This makes the evaluation closer to balanced than to live complaint frequency; report both per-class metrics and results on a separate realistic prevalence sample. Product grouping is only a routing proxy. Some CFPB product names combine distinct products, so manually inspect the mapping.

Before making real-world claims:

1. Inspect sampled records and confirm category definitions.
2. Remove near-duplicates and repeated templates across splits, not just exact copies.
3. Hold out a later time period and, where possible, unseen companies to test transfer.
4. Tune feature settings and review threshold on validation only, then freeze them.
5. Evaluate once on the untouched test set, report macro F1, per-class recall, confusion, calibration, coverage, and class distribution.
6. Evaluate uncertainty handling on unrelated topics, short messages, multilingual input, and deliberately ambiguous complaints.
7. Define a monitoring plan before deployment: review rates, category drift, overrides, and failure examples.

## Other intelligence components

Urgency is a transparent phrase matcher, not a learned predictor. It detects configured fraud, access, hardship, and repeated-complaint signals. Sentiment is a small keyword count. Both can misread negation, sarcasm, mixed sentiment, or regional wording. There are no ground-truth urgency or sentiment labels in the shipped data.

Retrieval is lexical, based on TF-IDF paragraph vectors, cosine similarity, at least two shared informative terms, and a small category ranking boost. It can miss synonyms, overvalue overlapping words, and retrieve irrelevant passages. The evidence UI is part of the quality workflow, not proof that retrieval is correct.

Extractive drafts preserve the retrieved text. Optional LLM drafts check output completion and allowed citation IDs, but **do not** perform claim-level entailment verification. An LLM can still attach a valid citation to an unsupported claim. Human review remains required.

## Intended and excluded uses

Intended: student portfolio demonstrations, workflow learning, explainable baseline experiments, synthetic-data testing, and supervised prototyping.

Excluded without substantial additional evaluation and controls: automated financial decisions, legal advice, deciding debt validity, guaranteeing refunds, handling production customer data, multilingual triage, and autonomous customer communication.
