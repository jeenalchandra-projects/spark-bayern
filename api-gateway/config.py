# =============================================================================
# config.py — Configuration loader for the API Gateway
# =============================================================================
# WHAT THIS FILE DOES:
# Reads all environment variables from your .env file and makes them available
# as a single Python object called "settings".
#
# WHY WE DO IT THIS WAY:
# Instead of reading os.environ["SOME_KEY"] in every file, we read everything
# once here. If a required variable is missing, the app refuses to start and
# tells you exactly what's missing — no mysterious crashes later.
# =============================================================================

from pydantic_settings import BaseSettings  # Pydantic's settings management tool
from functools import lru_cache             # Caches the settings so we only load once


class Settings(BaseSettings):
    """
    All configuration for the API Gateway.
    Each attribute here maps directly to an environment variable in your .env file.
    The variable name in .env must match the attribute name (case-insensitive).
    """

    # --- LLM Settings ---
    llm_api_key: str          # Your Requesty API key
    llm_base_url: str = "https://router.requesty.ai/v1"
    llm_model: str = "mistral/mistral-large-latest"
    llm_app_title: str = "SPARK-Bayern"

    # --- Security ---
    demo_access_code: str     # Passphrase users must enter to access the app

    # --- Service URLs ---
    # These tell the gateway where to find the other services.
    # "quality-service" and "rag-service" are Docker service names —
    # Docker's internal network resolves them to the right container.
    quality_service_url: str = "http://quality-service:8001"
    rag_service_url: str = "http://rag-service:8002"
    translation_service_url: str = "http://translation-service:8003"

    # --- SPARK Integration ---
    spark_base_url: str = "disabled"

    # --- GDPR Settings ---
    max_upload_size_mb: int = 20
    result_ttl_seconds: int = 300

    # --- Server ---
    port: int = 8000

    class Config:
        # This tells Pydantic to look for a .env file in the current directory
        env_file = ".env"
        # Allow extra fields (in case .env has variables not listed above)
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Returns the settings object.
    The @lru_cache decorator means this function only runs once —
    after that it returns the cached result. This is efficient and ensures
    configuration is consistent throughout the app.
    """
    return Settings()
