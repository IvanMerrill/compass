"""
COMPASS - Comprehensive Observability Multi-Agent Platform for Adaptive System Solutions.

AI-powered incident investigation platform using parallel OODA loops and scientific methodology.
"""
from compass.config import settings
from compass.logging import setup_logging
from compass.observability import setup_observability

# Initialize logging and observability on module import
setup_logging(settings)
setup_observability(settings)

__version__ = "0.1.0"
__all__ = ["settings"]
