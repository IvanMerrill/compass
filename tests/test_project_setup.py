"""Tests to validate project setup and structure."""
import importlib.util
from pathlib import Path


def test_project_structure_exists():
    """Verify all key directories exist."""
    project_root = Path(__file__).parent.parent
    src_compass = project_root / "src" / "compass"

    # Core OODA directories
    assert (src_compass / "core" / "observe").is_dir(), "observe directory missing"
    assert (src_compass / "core" / "orient").is_dir(), "orient directory missing"
    assert (src_compass / "core" / "decide").is_dir(), "decide directory missing"
    assert (src_compass / "core" / "act").is_dir(), "act directory missing"

    # Agent directories
    assert (src_compass / "agents" / "orchestrator").is_dir(), "orchestrator directory missing"
    assert (src_compass / "agents" / "managers").is_dir(), "managers directory missing"
    assert (src_compass / "agents" / "workers").is_dir(), "workers directory missing"

    # Integration directories
    assert (src_compass / "integrations" / "mcp").is_dir(), "mcp directory missing"
    assert (src_compass / "integrations" / "observability").is_dir(), "observability directory missing"

    # Other core directories
    assert (src_compass / "cli").is_dir(), "cli directory missing"
    assert (src_compass / "api").is_dir(), "api directory missing"
    assert (src_compass / "state").is_dir(), "state directory missing"
    assert (src_compass / "learning").is_dir(), "learning directory missing"
    assert (src_compass / "monitoring").is_dir(), "monitoring directory missing"


def test_imports_work():
    """Verify Python packages import correctly."""
    # Test that compass package can be imported
    spec = importlib.util.find_spec("compass")
    assert spec is not None, "compass package not importable"

    # Verify package has proper __init__.py
    assert spec.origin is not None, "compass package has no __init__.py"

    # Import should work without errors
    import compass
    assert compass is not None


def test_dependencies_installed():
    """Verify key dependencies are available."""
    # Test core dependencies
    import pydantic
    import pytest
    import structlog

    # Verify versions are reasonable (not None)
    assert hasattr(pydantic, "VERSION") or hasattr(pydantic, "__version__")
    assert pytest is not None
    assert structlog is not None
