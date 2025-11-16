"""Tests for configuration management."""
from pathlib import Path

import pytest

from compass.config import Environment, LogLevel, Settings


def test_settings_defaults():
    """Test that settings have sensible defaults."""
    settings = Settings()

    assert settings.environment == Environment.DEV
    assert settings.log_level == LogLevel.INFO
    assert settings.redis_host == "localhost"
    assert settings.redis_port == 6379
    assert settings.postgres_host == "localhost"
    assert settings.postgres_port == 5432


def test_redis_url_without_password():
    """Test Redis URL generation without password."""
    settings = Settings(redis_host="testhost", redis_port=6380, redis_db=1)

    assert settings.redis_url == "redis://testhost:6380/1"


def test_redis_url_with_password():
    """Test Redis URL generation with password."""
    settings = Settings(
        redis_host="testhost", redis_port=6380, redis_db=1, redis_password="secret"
    )

    assert settings.redis_url == "redis://:secret@testhost:6380/1"


def test_postgres_url():
    """Test PostgreSQL URL generation."""
    settings = Settings(
        postgres_host="testhost",
        postgres_port=5433,
        postgres_db="testdb",
        postgres_user="testuser",
        postgres_password="testpass",
    )

    assert settings.postgres_url == "postgresql://testuser:testpass@testhost:5433/testdb"


def test_environment_from_env_var(monkeypatch: pytest.MonkeyPatch):
    """Test loading environment from environment variable."""
    monkeypatch.setenv("ENVIRONMENT", "prod")

    settings = Settings()

    assert settings.environment == Environment.PROD


def test_investigation_limits():
    """Test investigation limit settings."""
    settings = Settings()

    assert settings.max_investigation_timeout_seconds == 300
    assert settings.default_cost_budget_usd == 10.0
    assert settings.critical_cost_budget_usd == 20.0
    assert settings.max_parallel_agents == 7


def test_feature_flags():
    """Test feature flag settings."""
    settings = Settings()

    assert settings.enable_learning is True
    assert settings.enable_caching is True
    assert settings.enable_observability is True


def test_llm_provider_settings():
    """Test LLM provider configuration."""
    settings = Settings()

    assert settings.default_llm_provider == "openai"
    assert settings.default_model_name == "gpt-4o-mini"
    assert settings.orchestrator_model == "gpt-4"


def test_settings_env_file_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that .env file overrides defaults."""
    env_file = tmp_path / ".env"
    env_file.write_text("ENVIRONMENT=test\nLOG_LEVEL=DEBUG\n")

    monkeypatch.chdir(tmp_path)

    settings = Settings()

    assert settings.environment == Environment.TEST
    assert settings.log_level == LogLevel.DEBUG
