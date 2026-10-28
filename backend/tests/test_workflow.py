from sqlalchemy.orm.exc import StaleDataError

from app.models import Ticket


def create(client, complaint):
    result = client.post('/api/v1/tickets', json=complaint)
    assert result.status_code == 201, result.text
    return result.json()


def generate(client, ticket):
    response = client.post(f'/api/v1/tickets/{ticket["id"]}/draft', json={'expected_version': ticket['version']})
    assert response.status_code == 200, response.text
    return response.json()


def review(client, ticket, decision='approve'):
    return client.post(f'/api/v1/tickets/{ticket["id"]}/review', json={'expected_version': ticket['version'], 'decision': decision, 'reviewer': 'Test Reviewer', 'note': 'Compared draft against sources.'})


def test_create_classifies_and_audits(client, complaint):
    ticket = create(client, complaint)
    assert ticket['category'] == 'credit_card'
    assert ticket['sentiment'] == 'negative'
    assert ticket['analysis']['top_features']
    assert ticket['status'] == 'open'
    events = client.get(f'/api/v1/tickets/{ticket["id"]}/audit').json()
    assert events[0]['action'] == 'created'


def test_full_human_review_workflow(client, complaint):
    ticket = generate(client, create(client, complaint))
    assert ticket['status'] == 'in_review'
    assert '[POL-CARD-01]' in ticket['draft_text']
    assert ticket['draft_meta']['provider'] == 'extractive'
    assert ticket['draft_meta']['requires_approval'] is True
    edited = client.put(f'/api/v1/tickets/{ticket["id"]}/draft', json={'expected_version': ticket['version'], 'text': ticket['draft_text'] + '\nWe will check the details.'})
    assert edited.status_code == 200
    approved = review(client, edited.json())
    assert approved.status_code == 200, approved.text
    assert approved.json()['status'] == 'approved'
    assert approved.json()['approved_by'] == 'Test Reviewer'
    resolved = client.patch(f'/api/v1/tickets/{ticket["id"]}', json={'expected_version': approved.json()['version'], 'status': 'resolved'})
    assert resolved.status_code == 200
    actions = [e['action'] for e in client.get(f'/api/v1/tickets/{ticket["id"]}/audit').json()]
    assert actions == ['created', 'draft_generated', 'draft_edited', 'approved', 'updated']


def test_review_requires_draft_and_resolution_requires_approval(client, complaint):
    ticket = create(client, complaint)
    assert review(client, ticket).status_code == 409
    assert client.patch(f'/api/v1/tickets/{ticket["id"]}', json={'expected_version': ticket['version'], 'status': 'resolved'}).status_code == 409


def test_stale_edits_rejected(client, complaint):
    ticket = create(client, complaint)
    url = f'/api/v1/tickets/{ticket["id"]}'
    first = client.patch(url, json={'expected_version': ticket['version'], 'assignee': 'Reviewer One'})
    assert first.status_code == 200
    second = client.patch(url, json={'expected_version': ticket['version'], 'assignee': 'Reviewer Two'})
    assert second.status_code == 409
    assert client.get(url).json()['assignee'] == 'Reviewer One'


def test_database_version_counter_blocks_concurrent_flush(app, client, complaint):
    ticket = create(client, complaint)
    with app.state.session_factory() as one, app.state.session_factory() as two:
        a, b = one.get(Ticket, ticket['id']), two.get(Ticket, ticket['id'])
        a.assignee, b.assignee = 'Reviewer One', 'Reviewer Two'
        one.commit()
        try:
            two.commit()
            assert False, 'Expected optimistic concurrency protection'
        except StaleDataError:
            two.rollback()


def test_editing_approved_response_revokes_approval(client, complaint):
    ticket = review(client, generate(client, create(client, complaint))).json()
    response = client.put(f'/api/v1/tickets/{ticket["id"]}/draft', json={'expected_version': ticket['version'], 'text': ticket['draft_text'] + '\nThank you.'})
    assert response.status_code == 200
    assert response.json()['status'] == 'in_review'
    assert response.json()['approved_by'] is None


def test_rejection_keeps_history(client, complaint):
    ticket = generate(client, create(client, complaint))
    result = review(client, ticket, 'reject')
    assert result.status_code == 200
    assert result.json()['status'] == 'open'
    assert client.get(f'/api/v1/tickets/{ticket["id"]}/audit').json()[-1]['action'] == 'rejected'


def test_reclassifying_clears_draft(client, complaint):
    ticket = generate(client, create(client, complaint))
    updated = client.patch(f'/api/v1/tickets/{ticket["id"]}', json={'expected_version': ticket['version'], 'category': 'bank_account'})
    assert updated.status_code == 200
    assert updated.json()['draft_text'] is None
    assert updated.json()['status'] == 'open'


def test_stale_policy_blocks_approval(client, complaint):
    ticket = generate(client, create(client, complaint))
    citation = ticket['draft_meta']['citations'][0]
    policy = next(p for p in client.get('/api/v1/policies').json()['items'] if p['id'] == citation['policy_id'])
    update = {k: policy[k] for k in ['title', 'category', 'body', 'source', 'active']}
    update['body'] += '\n\nUpdated policy content for this regression test.'
    update['expected_version'] = policy['version']
    assert client.put('/api/v1/policies/' + policy['id'], json=update).status_code == 200
    result = review(client, ticket)
    assert result.status_code == 409
    assert 'policy changed' in result.json()['detail']


def test_no_sources_cannot_be_approved(client):
    ticket = create(client, {'customer_name': 'Test Customer', 'subject': 'Astronomy telescope issue', 'body': 'The telescope mirror and nebula observation magnification are unsuitable for astrophotography.', 'channel': 'web'})
    drafted = generate(client, ticket)
    assert not drafted['draft_meta']['citations']
    assert review(client, drafted).status_code == 409
    assert 'specialist' in drafted['draft_text'].lower()


def test_unknown_citations_rejected(client, complaint):
    ticket = generate(client, create(client, complaint))
    response = client.put(f'/api/v1/tickets/{ticket["id"]}/draft', json={'expected_version': ticket['version'], 'text': ticket['draft_text'] + ' Guaranteed refund [POL-FAKE].'})
    assert response.status_code == 422


def test_validation_and_not_found(client, complaint):
    assert client.post('/api/v1/tickets', json={**complaint, 'body': 'short'}).status_code == 422
    assert client.post('/api/v1/tickets', json={**complaint, 'status': 'approved'}).status_code == 422
    assert client.get('/api/v1/tickets/missing').status_code == 404
    assert client.get('/api/v1/tickets?limit=1000').status_code == 422


def test_filters_pagination_and_analytics(client, complaint):
    before = client.get('/api/v1/analytics').json()['total']
    create(client, complaint)
    page = client.get('/api/v1/tickets?limit=2&offset=0&category=credit_card').json()
    assert len(page['items']) == 2
    assert all(t['category'] == 'credit_card' for t in page['items'])
    assert client.get('/api/v1/tickets?q=%25').json()['total'] == 0  # literal %, not wildcard
    assert client.get('/api/v1/analytics').json()['total'] == before + 1


def test_csv_export_protects_formula_cells(client, complaint):
    create(client, {**complaint, 'customer_name': '=HYPERLINK("malicious")'})
    result = client.get('/api/v1/export/tickets.csv')
    assert result.status_code == 200
    assert "'=HYPERLINK" in result.text
    assert 'text/csv' in result.headers['content-type']


def test_policy_crud_and_version_conflict(client):
    payload = {'title': 'Telescope replacement policy', 'category': 'other', 'body': 'For a telescope mirror replacement, record the device serial and send it to the optics support queue.', 'source': 'Synthetic test policy'}
    created = client.post('/api/v1/policies', json=payload)
    assert created.status_code == 201
    policy = created.json()
    result = client.get('/api/v1/policies?q=telescope%20mirror').json()
    assert result['matches'][0]['policy_id'] == policy['id']
    update = {**payload, 'active': False, 'expected_version': policy['version']}
    assert client.put('/api/v1/policies/' + policy['id'], json=update).status_code == 200
    assert client.put('/api/v1/policies/' + policy['id'], json=update).status_code == 409
    assert not client.get('/api/v1/policies?q=telescope%20mirror').json()['matches']
