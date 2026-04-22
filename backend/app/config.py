"""Application settings loaded via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    google_cloud_project: str = "capgemini-capstone-494100"
    gcs_bucket_name: str = "capgemini-capstone-494100-corpus"
    vertex_ai_location: str = "us-central1"
    vector_search_index_id: str = ""
    vector_search_endpoint_id: str = ""
    backend_url: str = ""


def get_settings() -> Settings:
    return Settings()
