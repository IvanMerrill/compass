"""
Disproof strategies for systematic hypothesis testing.

Following the scientific method, COMPASS actively attempts to DISPROVE hypotheses
rather than just collecting supporting evidence. Hypotheses that survive rigorous
disproof attempts gain higher confidence.

Available Strategies:
- TemporalContradictionStrategy: Check if issue existed before suspected cause
- ScopeVerificationStrategy: Verify hypothesis scope matches observed impact
- MetricThresholdValidationStrategy: Check if metrics support hypothesis claims
"""

from compass.core.disproof.temporal_contradiction import TemporalContradictionStrategy
from compass.core.disproof.scope_verification import ScopeVerificationStrategy

__all__ = ["TemporalContradictionStrategy", "ScopeVerificationStrategy"]
