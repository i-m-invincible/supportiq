import csv

from scripts.import_cfpb import convert, map_product
from app.ml.training import read_rows


def test_import_mapping_dedup_and_stratified_splits(tmp_path):
    products = ['Credit card', 'Checking or savings account', 'Money transfer, virtual currency, or money service', 'Credit reporting', 'Debt collection', 'Mortgage']
    source = tmp_path / 'source.csv'
    with source.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Product', 'Consumer complaint narrative'])
        writer.writeheader()
        for product in products:
            for i in range(30):
                writer.writerow({'Product': product, 'Consumer complaint narrative': f'This synthetic complaint concerns {product} and unique incident number {i}.'})
        writer.writerow({'Product': 'Mortgage', 'Consumer complaint narrative': 'This synthetic complaint concerns Mortgage and unique incident number 0.'})
    target = tmp_path / 'prepared.csv'
    metadata = convert(source, target, max_per_class=20)
    rows = read_rows(target)
    assert len(rows) == 120
    assert metadata['exact_duplicates_skipped'] == 1
    assert {r['split'] for r in rows} == {'train', 'validation', 'test'}
    assert map_product('Something unsupported') is None
    assert map_product('Credit reporting or other personal consumer reports') == 'credit_reporting'
