import re

import joblib
import numpy as np
import sklearn

from app.ml.training import evaluate, fit_pipeline, read_rows

PRIORITY_HOURS = {'critical': 2, 'high': 8, 'medium': 24, 'low': 48}
URGENT_RULES = [
    ('critical', r'\b(stolen|identity theft|unauthori[sz]ed|fraud(?:ulent)?|account takeover)\b', 'Possible fraud or identity risk'),
    ('critical', r'\b(eviction|foreclosure|homeless|cannot (?:buy|afford) (?:food|medicine))\b', 'Potential immediate financial hardship'),
    ('high', r'\b(locked out|blocked|frozen|cannot access|can.t access|missing money|rent|overdue|threat(?:en(?:ing|ed)?)?|harass(?:ment|ing)?)\b', 'Access, deadline, or escalation risk'),
    ('high', r'\b(repeated|third time|weeks|urgent|unresolved)\b', 'Repeated or time-sensitive complaint'),
]
NEGATIVE = re.compile(r'\b(angry|frustrat\w*|terrible|unacceptable|worst|disappoint\w*|unhappy|upset|hate|furious|stress\w*|ridiculous)\b', re.I)
POSITIVE = re.compile(r'\b(thank(?:s|ful)?|helpful|excellent|happy|great|appreciate|resolved)\b', re.I)


def redact(text: str):
    """Best-effort outbound redaction, deliberately not a complete PII detector."""
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[ID]', text)
    text = re.sub(r'(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)', '[NUMBER]', text)
    return text


def urgency(text: str):
    matches = [(level, reason) for level, regex, reason in URGENT_RULES if re.search(regex, text, re.I)]
    if matches:
        return matches[0][0], list(dict.fromkeys(reason for _, reason in matches))
    if re.search(r'\b(how do|how can|what is|information|explain)\b', text, re.I):
        return 'low', ['Information request; no configured risk signal']
    return 'medium', ['Standard review; no configured high-risk signal']


def sentiment(text: str):
    negative, positive = len(NEGATIVE.findall(text)), len(POSITIVE.findall(text))
    return 'negative' if negative > positive else 'positive' if positive > negative else 'neutral'


class Intelligence:
    def __init__(self, settings):
        self.threshold = settings.classification_threshold
        if settings.model_path.exists():
            # Load only a locally trained, trusted artifact; pickle/joblib is executable data.
            bundle = joblib.load(settings.model_path)
            if bundle['metadata']['sklearn_version'] != sklearn.__version__:
                raise RuntimeError('Model scikit-learn version differs. Retrain with the current environment.')
            self.pipeline, self.metadata = bundle['pipeline'], bundle['metadata']
        else:
            rows = read_rows(settings.data_dir / 'complaints.csv')
            self.pipeline = fit_pipeline(rows)
            self.metadata = {
                'model': 'TF-IDF (1–2 grams) + logistic regression',
                'dataset_kind': 'synthetic_demo', 'sklearn_version': sklearn.__version__,
                'train_samples': sum(r['split'] == 'train' for r in rows),
                'test': evaluate(self.pipeline, rows, 'test'),
                'validation': evaluate(self.pipeline, rows, 'validation'),
                'caveat': 'Synthetic demo scores are smoke tests, not real-world performance.',
            }

    def analyze(self, text: str):
        cleaned = redact(text)
        probabilities = self.pipeline.predict_proba([cleaned])[0]
        index = int(np.argmax(probabilities))
        predicted = str(self.pipeline.classes_[index])
        confidence = float(probabilities[index])
        vector = self.pipeline.named_steps['tfidf'].transform([cleaned])
        in_vocabulary = vector.nnz > 0
        needs_review = confidence < self.threshold or not in_vocabulary
        features = self.pipeline.named_steps['tfidf'].get_feature_names_out()
        weights = self.pipeline.named_steps['classifier'].coef_[index]
        contributions = vector.toarray()[0] * weights
        top = sorted([(features[i], float(contributions[i])) for i in np.flatnonzero(contributions > 0)], key=lambda pair: pair[1], reverse=True)[:5]
        priority, reasons = urgency(cleaned)
        return {
            'category': 'other' if needs_review else predicted,
            'suggested_category': predicted,
            'confidence': round(confidence, 4),
            'needs_review': needs_review,
            'top_features': [{'term': term, 'contribution': round(value, 4)} for term, value in top],
            'probabilities': {str(c): round(float(p), 4) for c, p in zip(self.pipeline.classes_, probabilities)},
            'priority': priority, 'priority_reasons': reasons,
            'sentiment': sentiment(cleaned),
            'sentiment_method': 'keyword heuristic',
            'classification_method': 'TF-IDF + logistic regression',
            'threshold': self.threshold,
        }
