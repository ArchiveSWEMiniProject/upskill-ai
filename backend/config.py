from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost:5432/upskill_ai"
    evidence_storage_dir: str = "backend/storage/evidence"
    max_evidence_bytes: int = 5 * 1024 * 1024
    frontend_origin: str = "http://localhost:3000"


settings = Settings()
