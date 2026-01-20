import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastRAG"
    API_V1_STR: str = "/api/v1"
    
    # DATABASE
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ragdb"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # Fallback to SQLite if no POSTGRES params or explicit sqlite request
        # For this fallback scenario, we prioritize SQLite
        if self.POSTGRES_HOST == "localhost" and self.POSTGRES_PASSWORD == "postgres":
             # Default values usually mean env not set for Prod, so use SQLite for local ease
             return "sqlite:///./ragdb.db"
        
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # REDIS
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # CHROMA
    CHROMA_PERSISTENCE_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "documents"

    # LLM
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
