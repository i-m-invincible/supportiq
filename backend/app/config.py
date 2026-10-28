from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    database_url: str = f'sqlite:///{ROOT / "supportiq.db"}'
    auto_create_schema: bool = True
    seed_demo: bool = True
    api_key: str = ''
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    data_dir: Path = ROOT / 'data'
    model_path: Path = ROOT / 'artifacts' / 'classifier.joblib'
    classification_threshold: float = Field(default=0.45, ge=0, le=1)
    retrieval_threshold: float = Field(default=0.09, ge=0, le=1)
    draft_provider: Literal['extractive', 'openai'] = 'extractive'
    openai_api_key: str = ''
    openai_model: str = ''
    llm_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
