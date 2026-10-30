"""Application configuration using Pydantic Settings.

Supports environment variables for PostgreSQL, Neo4j, LLM services, file storage, and CORS parameters.
"""

from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Configuration
    APP_NAME: str = "Enterprise Knowledge Copilot"
    PROJECT_NAME: str = "Enterprise Knowledge Copilot"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"

    # File Storage & Upload Configuration
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "data/uploads"

    @property
    def max_upload_size_bytes(self) -> int:
        """Return maximum allowable upload size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def upload_dir_path(self) -> Path:
        """Return resolved filesystem path to the upload directory."""
        path = Path(self.UPLOAD_DIR)
        if not path.is_absolute():
            # Resolve relative to project workspace or repository root
            path = Path(__file__).resolve().parent.parent.parent.parent / self.UPLOAD_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    # Database Configuration (PostgreSQL Async default)
    POSTGRES_USER: str = "copilot_user"
    POSTGRES_PASSWORD: str = "copilot_dev_password"
    POSTGRES_DB: str = "enterprise_knowledge"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = (
        "postgresql+asyncpg://copilot_user:copilot_dev_password@localhost:5432/enterprise_knowledge"
    )

    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Neo4j Graph Database Configuration (Step 9)
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "copilot_graph_dev_password"
    NEO4J_DATABASE: str = "neo4j"
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = 50
    NEO4J_CONNECTION_TIMEOUT: float = 30.0
    NEO4J_MAX_CONNECTION_LIFETIME: float = 3600.0

    @property
    def neo4j_effective_user(self) -> str:
        """Return effective Neo4j username supporting both NEO4J_USER and NEO4J_USERNAME."""
        return self.NEO4J_USER or self.NEO4J_USERNAME or "neo4j"

    # Auth & RBAC Configuration (Phases 18, 19, 20)
    JWT_SECRET_KEY: str = "enterprise-copilot-dev-secret-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    ENFORCE_DOCUMENT_RBAC: bool = True

    # LLM Generation Configuration (Phases 10, 11, 12)
    LLM_PROVIDER: str = ""  # "openai", "gemini", or "" (mock for local/test)
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: str = ""
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1500
    LLM_TIMEOUT_SECONDS: float = 45.0

    # GraphRAG Advanced Retrieval Configuration (Phases 1-8)
    GRAPHRAG_VECTOR_TOP_K: int = 10
    GRAPHRAG_VECTOR_MIN_SCORE: float = 0.30
    GRAPHRAG_VECTOR_WEIGHT: float = 0.50
    GRAPHRAG_GRAPH_WEIGHT: float = 0.50
    GRAPHRAG_EVIDENCE_WEIGHT: float = 0.20
    GRAPHRAG_RRF_K: int = 60
    GRAPHRAG_MAX_VECTOR_CANDIDATES: int = 40

    GRAPHRAG_GRAPH_MAX_DEPTH: int = 2
    GRAPHRAG_GRAPH_MAX_NODES: int = 50
    GRAPHRAG_GRAPH_MAX_EDGES: int = 100
    GRAPHRAG_GRAPH_MAX_PATHS: int = 20

    GRAPHRAG_MAX_CONTEXT_CHUNKS: int = 10
    GRAPHRAG_MAX_CONTEXT_CHARACTERS: int = 12000
    GRAPHRAG_MAX_PATHS: int = 15
    GRAPHRAG_MAX_GRAPH_ENTITIES: int = 30
    GRAPHRAG_MAX_GRAPH_RELATIONSHIPS: int = 60

    # Embedding & Vector Search Configuration (Step 6)
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_MAX_RETRIES: int = 3
    EMBEDDING_TIMEOUT_SECONDS: int = 60
    EMBEDDING_API_KEY: str = ""

    VECTOR_SEARCH_TOP_K: int = 8
    VECTOR_SEARCH_MAX_TOP_K: int = 50
    VECTOR_SIMILARITY_THRESHOLD: float = 0.0

    # Entity Extraction Configuration (Step 7)
    ENTITY_EXTRACTION_PROVIDER: str = ""          # "openai" or "" (empty → mock)
    ENTITY_EXTRACTION_MODEL: str = "gpt-4o-mini"
    ENTITY_EXTRACTION_BATCH_SIZE: int = 10
    ENTITY_EXTRACTION_MAX_RETRIES: int = 3
    ENTITY_EXTRACTION_TIMEOUT_SECONDS: int = 60
    ENTITY_EXTRACTION_MIN_CONFIDENCE: float = 0.50
    OPENAI_API_KEY: str = ""                      # Shared with embedding provider

    # Relationship Extraction Configuration (Step 8)
    RELATIONSHIP_EXTRACTION_PROVIDER: str = ""    # "openai" or "" (empty → mock)
    RELATIONSHIP_EXTRACTION_MODEL: str = "gpt-4o-mini"
    RELATIONSHIP_EXTRACTION_BATCH_SIZE: int = 10
    RELATIONSHIP_EXTRACTION_MAX_RETRIES: int = 3
    RELATIONSHIP_EXTRACTION_TIMEOUT_SECONDS: int = 60
    RELATIONSHIP_EXTRACTION_MIN_CONFIDENCE: float = 0.50

    @property
    def sync_database_url(self) -> str:
        """Return synchronous database URL for Alembic migrations."""
        url = self.DATABASE_URL
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
        elif url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://")
        return url

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
