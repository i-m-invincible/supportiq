import os

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.mark.skipif(not os.getenv('TEST_POSTGRES_URL'), reason='Requires migrated PostgreSQL; exercised by CI.')
def test_postgres_workflow():
    settings = Settings(database_url=os.environ['TEST_POSTGRES_URL'], auto_create_schema=False,
                        seed_demo=True, api_key='', draft_provider='extractive', _env_file=None)
    with TestClient(create_app(settings)) as client:
        created = client.post('/api/v1/tickets', json={'customer_name': 'CI Customer', 'subject': 'Duplicate credit card transaction', 'body': 'My credit card was billed twice for the same merchant purchase. Please check the duplicate charge.'})
        assert created.status_code == 201
        ticket = created.json()
        drafted = client.post(f'/api/v1/tickets/{ticket["id"]}/draft', json={'expected_version': ticket['version']})
        assert drafted.status_code == 200
        ticket = drafted.json()
        approved = client.post(f'/api/v1/tickets/{ticket["id"]}/review', json={'expected_version': ticket['version'], 'decision': 'approve', 'reviewer': 'CI Reviewer'})
        assert approved.status_code == 200
        assert approved.json()['approved_by'] == 'CI Reviewer'
