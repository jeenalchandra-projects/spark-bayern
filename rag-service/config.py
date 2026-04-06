from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    llm_api_key: str
    llm_base_url: str = "https://router.requesty.ai/v1"
    llm_model: str = "mistral/mistral-large-latest"
    llm_app_title: str = "SPARK-Bayern"
    baybo_pdf_path: str = "/app/data/baybo.pdf"
    rag_top_k: int = 5
    port: int = 8002

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
