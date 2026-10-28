"""Convert a user-downloaded CFPB CSV into deduplicated, stratified splits.

No download occurs automatically. Product labels are routing proxies, not intent labels.
Run from repository root: python scripts/import_cfpb.py --input /path/to/complaints.csv
"""
import argparse
import csv
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ['bank_account', 'credit_card', 'credit_reporting', 'debt_collection', 'loan', 'money_transfer']


def map_product(product: str):
    value = product.lower()
    if 'credit reporting' in value or 'consumer report' in value:
        return 'credit_reporting'
    if 'debt collection' in value:
        return 'debt_collection'
    if 'credit card' in value or 'prepaid card' in value:
        return 'credit_card'
    if 'checking' in value or 'savings account' in value or 'bank account' in value:
        return 'bank_account'
    if 'money transfer' in value or 'money service' in value:
        return 'money_transfer'
    if any(term in value for term in ['mortgage', 'loan', 'vehicle lease']):
        return 'loan'
    return None


def normalize(text: str):
    text = re.sub(r'\bX{2,}\b', 'REDACTED', text)
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
    text = re.sub(r'(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)', '[NUMBER]', text)
    return ' '.join(text.split())


def convert(source: Path, target: Path, max_per_class=2000, seed=42):
    if max_per_class < 20:
        raise ValueError('Use at least 20 examples per class to support three splits.')
    randomizer = random.Random(seed)
    buckets, counts, seen = defaultdict(list), Counter(), set()
    read_count = duplicates = 0
    with source.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not {'Product', 'Consumer complaint narrative'} <= set(reader.fieldnames or []):
            raise ValueError('Expected CFPB CSV columns: Product and Consumer complaint narrative.')
        for row in reader:
            read_count += 1
            category = map_product(row.get('Product', ''))
            narrative = normalize(row.get('Consumer complaint narrative') or '')
            if category is None or len(narrative) < 40:
                continue
            digest = hashlib.sha256(narrative.lower().encode()).hexdigest()
            if digest in seen:
                duplicates += 1
                continue
            seen.add(digest)
            counts[category] += 1
            # Reservoir sampling avoids taking only the beginning of a sorted export.
            if len(buckets[category]) < max_per_class:
                buckets[category].append(narrative)
            else:
                position = randomizer.randrange(counts[category])
                if position < max_per_class:
                    buckets[category][position] = narrative
    missing = [c for c in CATEGORIES if len(buckets[c]) < 20]
    if missing:
        raise ValueError('Need at least 20 nonempty unique narratives for each category. Missing: ' + ', '.join(missing))
    target.parent.mkdir(parents=True, exist_ok=True)
    split_counts = Counter()
    with target.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['text', 'category', 'split'], lineterminator='\n')
        writer.writeheader()
        for category in CATEGORIES:
            rows = buckets[category]
            randomizer.shuffle(rows)
            train_end, validation_end = int(len(rows) * 0.7), int(len(rows) * 0.85)
            for index, narrative in enumerate(rows):
                split = 'train' if index < train_end else 'validation' if index < validation_end else 'test'
                writer.writerow({'text': narrative, 'category': category, 'split': split})
                split_counts[split] += 1
    report = {'source': 'CFPB user-provided export', 'source_filename': source.name, 'seed': seed,
              'scanned_rows': read_count, 'exact_duplicates_skipped': duplicates,
              'sampled_per_class': {c: len(buckets[c]) for c in CATEGORIES}, 'splits': dict(split_counts),
              'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'limitation': 'Exact deduplication only. Check near-duplicates and temporal leakage. Product categories are proxy labels; no urgency or sentiment ground truth is provided.'}
    target.with_suffix('.metadata.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'data' / 'cfpb.csv')
    parser.add_argument('--max-per-class', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(convert(args.input, args.output, args.max_per_class, args.seed), indent=2))
