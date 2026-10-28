import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def app(tmp_path):
    settings = Settings(database_url=f'sqlite:///{tmp_path / "test.db"}', seed_demo=True,
                        api_key='', draft_provider='extractive', openai_api_key='', openai_model='', _env_file=None)
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def complaint():
    return {'customer_name': 'Test Customer', 'subject': 'Duplicate charge on credit card',
            'body': 'My credit card statement lists a duplicate merchant charge for the same purchase. I am frustrated and need help disputing it.',
            'channel': 'email'}
