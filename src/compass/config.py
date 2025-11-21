"""
COMPASS Configuration Management.

Loads configuration from environment variables following 12-factor app principles.
"""
from enum import Enum
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    """COMPASS application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Environment = Field(default=Environment.DEV, description="Application environment")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")

    # Redis Configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")

    # PostgreSQL Configuration
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="compass", description="PostgreSQL database")
    postgres_user: str = Field(default="compass", description="PostgreSQL user")
    postgres_password: str = Field(default="compass_dev", description="PostgreSQL password")

    # LLM Provider Settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    default_llm_provider: str = Field(default="openai", description="Default LLM provider")
    default_model_name: str = Field(default="gpt-4o-mini", description="Default model name")
    orchestrator_model: str = Field(default="gpt-4", description="Model for orchestrator")

    # Investigation Limits
    max_investigation_timeout_seconds: int = Field(
        default=300, description="Maximum investigation timeout in seconds"
    )
    default_cost_budget_usd: float = Field(
        default=10.0, description="Default cost budget per investigation in USD"
    )
    critical_cost_budget_usd: float = Field(
        default=20.0, description="Cost budget for critical investigations in USD"
    )
    max_parallel_agents: int = Field(default=7, description="Maximum parallel agents")
    agent_timeout: int = Field(default=120, description="Agent timeout in seconds")

    # Observability Stack Configuration
    # Grafana
    grafana_url: Optional[str] = Field(default=None, description="Grafana API URL")
    grafana_token: Optional[str] = Field(default=None, description="Grafana service account token")
    grafana_ui_url: Optional[str] = Field(default=None, description="Grafana UI URL for dashboards")

    # Tempo (Distributed Tracing)
    tempo_url: Optional[str] = Field(default=None, description="Tempo URL")
    tempo_mcp_url: Optional[str] = Field(default=None, description="Tempo MCP endpoint URL")

    # Loki (Log Aggregation)
    loki_url: Optional[str] = Field(default=None, description="Loki URL")
    loki_query_url: Optional[str] = Field(default=None, description="Loki query endpoint URL")

    # Mimir/Prometheus (Metrics)
    mimir_url: Optional[str] = Field(default=None, description="Mimir URL")
    prometheus_url: Optional[str] = Field(default=None, description="Prometheus URL")

    # OTLP (OpenTelemetry Protocol)
    otlp_http_endpoint: Optional[str] = Field(
        default=None, description="OTLP HTTP endpoint for sending telemetry"
    )
    otlp_grpc_endpoint: Optional[str] = Field(
        default=None, description="OTLP gRPC endpoint for sending telemetry"
    )

    # Feature Flags
    enable_learning: bool = Field(default=True, description="Enable learning from investigations")
    enable_caching: bool = Field(default=True, description="Enable LLM response caching")
    enable_observability: bool = Field(default=True, description="Enable OpenTelemetry tracing")

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# Global settings instance
settings = Settings()
