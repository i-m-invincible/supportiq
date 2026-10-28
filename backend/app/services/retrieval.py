"""Small-corpus lexical retrieval with stable, versioned policy citations."""
import re

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

GENERIC_WORDS = {'issue', 'issues', 'problem', 'problems', 'help', 'please', 'support', 'customer', 'request', 'contact', 'thank', 'thanks', 'need', 'needs'}


def retrieve(query: str, policies, category: str | None = None, threshold=0.09, limit=3):
    chunks = []
    for policy in policies:
        if not policy.active:
            continue
        # Category is a soft boost, never sufficient on its own to pass the threshold.
        for position, paragraph in enumerate(re.split(r'\n\s*\n', policy.body)):
            if paragraph.strip():
                chunks.append({'policy_id': policy.id, 'title': policy.title, 'category': policy.category,
                               'content': paragraph.strip(), 'chunk_id': f'{policy.id}:{position + 1}',
                               'version': policy.version, 'source': policy.source})
    if not chunks:
        return []
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words=sorted(set(ENGLISH_STOP_WORDS) | GENERIC_WORDS), sublinear_tf=True)
    try:
        matrix = vectorizer.fit_transform([f"{c['title']} {c['content']}" for c in chunks])
    except ValueError:
        return []
    scores = (matrix @ vectorizer.transform([query]).T).toarray().ravel()
    tokenize = vectorizer.build_tokenizer()
    stop_words = vectorizer.get_stop_words()
    query_terms = set(tokenize(query.lower())) - stop_words
    ranked = sorted(range(len(chunks)), key=lambda i: float(scores[i]) + (0.04 if chunks[i]['category'] == category else 0), reverse=True)
    results, seen = [], set()
    for i in ranked:
        source_terms = set(tokenize((chunks[i]['title'] + ' ' + chunks[i]['content']).lower())) - stop_words
        # A lone generic overlapping word can receive a high cosine score when
        # every other query word is out of vocabulary. Require lexical evidence.
        if len(query_terms & source_terms) < 2:
            continue
        if not np.isfinite(scores[i]) or scores[i] < threshold or chunks[i]['policy_id'] in seen:
            continue
        seen.add(chunks[i]['policy_id'])
        results.append({**chunks[i], 'score': round(float(scores[i]), 4)})
        if len(results) == limit:
            break
    return results
