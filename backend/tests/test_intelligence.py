from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import ROOT, Settings
from app.main import create_app
from app.ml.training import fit_pipeline, read_rows
from app.services.drafting import generate_draft
from app.services.intelligence import redact, sentiment, urgency
from app.services.retrieval import retrieve


def test_urgency_and_sentiment_explainability():
    priority, reasons = urgency('My credit card was stolen and unauthorized transactions appeared.')
    assert priority == 'critical' and reasons
    assert urgency('I am locked out of my account.')[0] == 'high'
    assert urgency('How can I check my statement?')[0] == 'low'
    assert sentiment('I am frustrated and angry about this terrible service.') == 'negative'


def test_redaction_before_outbound_calls():
    text = redact('Contact person@example.test, phone +1 212 555 1234 and ID 123-45-6789.')
    assert 'person@example.test' not in text
    assert '123-45-6789' not in text
    assert '212 555' not in text


def test_retrieval_does_not_create_matches_from_category_boost():
    policy = SimpleNamespace(id='POL-TEST', title='Card duplicate charge', body='Report a duplicate card transaction through the secure dispute form.', category='credit_card', active=True, version=1, source='test')
    assert retrieve('nebula telescope astrophotography', [policy], category='credit_card') == []
    assert retrieve('duplicate card transaction', [policy])[0]['policy_id'] == 'POL-TEST'


def test_training_vocabulary_excludes_held_out_words():
    rows = read_rows(ROOT / 'data' / 'complaints.csv')
    for row in rows:
        if row['split'] == 'test':
            row['text'] += ' heldoutuniquetoken'
    model = fit_pipeline(rows)
    assert 'heldoutuniquetoken' not in model.named_steps['tfidf'].vocabulary_


def test_duplicate_narratives_fail_validation(tmp_path):
    content = (ROOT / 'data' / 'complaints.csv').read_text()
    target = tmp_path / 'duplicates.csv'
    target.write_text(content + content.splitlines()[1] + '\n')
    with pytest.raises(ValueError, match='Duplicate'):
        read_rows(target)


def test_unknown_input_is_flagged_for_review(client):
    result = client.post('/api/v1/analyze', json={'text': 'quasar astrophotography nebula telescope spectroscopy'}).json()
    assert result['category'] == 'other'
    assert result['needs_review'] is True


@pytest.fixture
def citations():
    return [{'policy_id': 'POL-CARD-01', 'content': 'Submit a card dispute through the secure portal.', 'title': 'Card dispute', 'category': 'credit_card', 'version': 1, 'source': 'demo', 'score': 0.5, 'chunk_id': 'POL-CARD-01:1'}]


def test_local_drafts_never_call_external_api(monkeypatch, citations):
    def forbidden(*args, **kwargs):
        pytest.fail('Network must not be used in extractive mode')
    monkeypatch.setattr(httpx, 'post', forbidden)
    text, meta = generate_draft('A duplicate charge', citations, Settings(draft_provider='extractive', _env_file=None))
    assert '[POL-CARD-01]' in text
    assert meta['provider'] == 'extractive'


def test_llm_valid_response_and_outbound_redaction(monkeypatch, citations):
    def post(url, **kwargs):
        assert url.endswith('/responses')
        assert 'person@example.test' not in kwargs['json']['input']
        assert kwargs['json']['store'] is False
        return httpx.Response(200, request=httpx.Request('POST', url), json={'status': 'completed', 'output': [{'type': 'reasoning'}, {'type': 'message', 'content': [{'type': 'output_text', 'text': 'Please submit a card dispute through the secure portal. [POL-CARD-01]'}]}]})
    monkeypatch.setattr(httpx, 'post', post)
    text, meta = generate_draft('Contact person@example.test about the card charge.', citations, Settings(draft_provider='openai', openai_api_key='test-only', openai_model='test-model', _env_file=None))
    assert meta['provider'] == 'openai'
    assert '[POL-CARD-01]' in text


@pytest.mark.parametrize('mode', ['timeout', 'unknown_citation', 'no_citation', 'incomplete', 'invalid_json'])
def test_llm_failure_falls_back(monkeypatch, citations, mode):
    def post(url, **kwargs):
        if mode == 'timeout':
            raise httpx.TimeoutException('test timeout')
        if mode == 'invalid_json':
            return httpx.Response(200, request=httpx.Request('POST', url), text='not json')
        text = 'We can refund you immediately. ' + ('[POL-UNKNOWN]' if mode == 'unknown_citation' else '[POL-CARD-01]' if mode == 'incomplete' else '')
        return httpx.Response(200, request=httpx.Request('POST', url), json={'status': 'incomplete' if mode == 'incomplete' else 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': text}]}]})
    monkeypatch.setattr(httpx, 'post', post)
    text, meta = generate_draft('A charge', citations, Settings(draft_provider='openai', openai_api_key='test-only', openai_model='test-model', _env_file=None))
    assert meta['provider'] == 'extractive'
    assert meta['fallback_reason']
    assert 'refund you immediately' not in text


def test_api_key_guards_every_business_route(tmp_path):
    settings = Settings(database_url=f'sqlite:///{tmp_path / "auth.db"}', seed_demo=True, api_key='test-workspace-key', _env_file=None)
    with TestClient(create_app(settings)) as client:
        assert client.get('/health').status_code == 200
        for path in ['/tickets', '/analytics', '/policies', '/meta', '/export/tickets.csv']:
            assert client.get('/api/v1' + path).status_code == 401
        assert client.get('/api/v1/tickets', headers={'X-API-Key': 'wrong'}).status_code == 401
        assert client.get('/api/v1/tickets', headers={'X-API-Key': 'test-workspace-key'}).status_code == 200


def test_clean_checkout_starts_without_saved_model(tmp_path):
    settings = Settings(database_url=f'sqlite:///{tmp_path / "cold-start.db"}', model_path=tmp_path / 'absent.joblib',
                        seed_demo=True, api_key='', draft_provider='extractive', _env_file=None)
    with TestClient(create_app(settings)) as client:
        assert client.get('/api/v1/tickets').json()['total'] == 18
        metadata = client.get('/api/v1/meta').json()
        assert metadata['classifier']['dataset_kind'] == 'synthetic_demo'
        assert metadata['classifier']['train_samples'] == 96
        assert not settings.model_path.exists()  # startup training stays in memory
