"""Leakage-aware text pipeline. Fit vocabulary and classifier on train only."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

CATEGORIES = ['bank_account', 'credit_card', 'credit_reporting', 'debt_collection', 'loan', 'money_transfer']


def read_rows(path: Path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not {'text', 'category', 'split'} <= set(rows[0]):
        raise ValueError('CSV must have text, category, split columns.')
    seen: dict[str, str] = {}
    for row in rows:
        if row['category'] not in CATEGORIES or row['split'] not in {'train', 'validation', 'test'}:
            raise ValueError('Unknown category or split in dataset.')
        key = ' '.join(row['text'].lower().split())
        if not key:
            raise ValueError('Empty narrative.')
        if key in seen:
            raise ValueError('Duplicate narrative detected; deduplicate before splitting.')
        seen[key] = row['split']
    for split in ['train', 'validation', 'test']:
        if set(r['category'] for r in rows if r['split'] == split) != set(CATEGORIES):
            raise ValueError(f'{split} must include all six categories.')
    return rows


def fit_pipeline(rows):
    training = [r for r in rows if r['split'] == 'train']
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, max_features=40000)),
        ('classifier', LogisticRegression(C=4.0, max_iter=1500, class_weight='balanced', random_state=42)),
    ])
    pipeline.fit([r['text'] for r in training], [r['category'] for r in training])
    return pipeline


def evaluate(pipeline, rows, split, threshold=0.45):
    sample = [r for r in rows if r['split'] == split]
    texts, labels = [r['text'] for r in sample], [r['category'] for r in sample]
    probabilities = pipeline.predict_proba(texts)
    predictions = pipeline.classes_[probabilities.argmax(axis=1)]
    accepted = probabilities.max(axis=1) >= threshold
    return {
        'samples': len(sample),
        'accuracy': float(accuracy_score(labels, predictions)),
        'macro_f1': float(f1_score(labels, predictions, average='macro')),
        'coverage_at_threshold': float(accepted.mean()),
        'accuracy_on_accepted': float(accuracy_score([y for y, keep in zip(labels, accepted) if keep], predictions[accepted])) if accepted.any() else None,
        'classification_report': classification_report(labels, predictions, output_dict=True, zero_division=0),
        'confusion_matrix': confusion_matrix(labels, predictions, labels=CATEGORIES).tolist(),
    }


def train(dataset: Path, output: Path, dataset_kind='synthetic_demo'):
    rows = read_rows(dataset)
    pipeline = fit_pipeline(rows)
    metadata = {
        'model': 'TF-IDF (1–2 grams) + logistic regression',
        'dataset_kind': dataset_kind,
        'dataset_sha256': hashlib.sha256(dataset.read_bytes()).hexdigest(),
        'sklearn_version': sklearn.__version__,
        'train_samples': sum(r['split'] == 'train' for r in rows),
        'categories': CATEGORIES,
        'threshold': 0.45,
        'validation': evaluate(pipeline, rows, 'validation'),
        'test': evaluate(pipeline, rows, 'test'),
        'caveat': 'Synthetic demo scores are smoke tests, not evidence of real-world accuracy.' if dataset_kind == 'synthetic_demo' else 'Product labels are routing proxies, not independently annotated complaint intent. Validate domain transfer.',
    }
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump({'pipeline': pipeline, 'metadata': metadata}, output / 'classifier.joblib')
    (output / 'metrics.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return metadata


if __name__ == '__main__':
    from app.config import ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=ROOT / 'data' / 'complaints.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts')
    parser.add_argument('--dataset-kind', choices=['synthetic_demo', 'cfpb'], default='synthetic_demo')
    args = parser.parse_args()
    report = train(args.data, args.output, args.dataset_kind)
    print(json.dumps({k: report[k] for k in ['model', 'train_samples', 'dataset_kind', 'caveat']}, indent=2))
    print(f"Test macro F1: {report['test']['macro_f1']:.3f}")
