# =============================================================================
# config.py — All configuration for the consolidated backend
# =============================================================================
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    llm_api_key: str = ""
    llm_base_url: str = "https://router.requesty.ai/v1"
    llm_model: str = "mistral/mistral-large-latest"
    llm_app_title: str = "SPARK-Bayern"

    # Security
    demo_access_code: str = "demo"

    # GDPR
    max_upload_size_mb: int = 20
    result_ttl_seconds: int = 300

    # RAG
    rag_top_k: int = 5
    baybo_pdf_path: str = "/app/data/baybo.pdf"

    # Server — Railway injects PORT automatically
    port: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
