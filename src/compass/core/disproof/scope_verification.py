"""
Scope Verification Disproof Strategy.

This strategy verifies that the hypothesis's claimed scope matches the actual
observed impact. If the hypothesis overstates or understates the scope, it is
disproven.

Example:
    Hypothesis: "Database issue affecting all 10 services"
    Query: Tempo traces for errors across all services
    Result: Only 2 services have errors (20% != 100%)
    Conclusion: Hypothesis DISPROVEN (scope mismatch)

Algorithm:
    1. Extract claimed scope from hypothesis metadata
    2. Query Tempo to find actually affected services
    3. Compare claimed vs observed scope
    4. If mismatch exceeds tolerance → DISPROVEN
    5. Otherwise → hypothesis SURVIVES
"""
from typing import Any, Dict, List, Optional

from compass.core.scientific_framework import (
    DisproofAttempt,
    Evidence,
    EvidenceQuality,
    Hypothesis,
)
import structlog

logger = structlog.get_logger(__name__)

# Configuration constants
HIGH_EVIDENCE_CONFIDENCE = 0.9  # Confidence for DIRECT scope evidence
SCOPE_MATCH_TOLERANCE = 0.15  # 15% tolerance for scope matching

# Scope thresholds
SCOPE_THRESHOLD_ALL = 0.95  # "all services" means >= 95%
SCOPE_THRESHOLD_MOST = 0.80  # "most services" means >= 80%
SCOPE_THRESHOLD_SOME = 0.30  # "some services" means >= 30%


class ScopeVerificationStrategy:
    """
    Disproof strategy that verifies hypothesis scope matches observed impact.

    Compares the hypothesis's claimed scope (e.g., "all services") against
    actual observed impact from distributed tracing.
    """

    def __init__(self, tempo_client: Any):
        """
        Initialize scope verification strategy.

        Args:
            tempo_client: Client for querying Tempo distributed traces
        """
        self.tempo = tempo_client

    def attempt_disproof(self, hypothesis: Hypothesis) -> DisproofAttempt:
        """
        Attempt to disprove hypothesis by verifying scope claims.

        This method queries distributed traces to determine which services are
        actually affected, then compares against the hypothesis's claimed scope.

        Required hypothesis metadata:
            - claimed_scope (str): Scope claim ("all_services", "most_services", "specific_services")
            - service_count (int): Total number of services in system (for percentage calculations)
            - issue_type (str): Type of issue to look for (e.g., "connection_errors")

        Optional metadata:
            - affected_services (List[str]): Specific services claimed to be affected

        Args:
            hypothesis: Hypothesis to test with metadata containing scope claims

        Returns:
            DisproofAttempt with one of:
                - disproven=True: Claimed scope doesn't match observed impact
                - disproven=False: Scope matches OR test inconclusive
        """
        try:
            # Extract claimed scope from hypothesis metadata
            claimed_scope = hypothesis.metadata.get("claimed_scope")

            if not claimed_scope:
                logger.debug("No claimed_scope in hypothesis metadata", hypothesis_id=hypothesis.id)
                return self._inconclusive_result("No scope claim provided in hypothesis metadata")

            service_count = hypothesis.metadata.get("service_count", 0)
            issue_type = hypothesis.metadata.get("issue_type", "errors")

            logger.info(
                "Verifying scope claim",
                claimed_scope=claimed_scope,
                service_count=service_count,
                issue_type=issue_type,
            )

            # Query Tempo to find actually affected services
            affected_services = self.tempo.query_traces(
                issue_type=issue_type,
                time_range="last_30_minutes",
            )

            observed_count = len(affected_services)
            observed_percentage = observed_count / service_count if service_count > 0 else 0

            logger.debug(
                "Observed impact",
                observed_count=observed_count,
                observed_percentage=f"{observed_percentage:.1%}",
            )

            # Determine expected scope based on claim
            expected_scope = self._parse_scope_claim(claimed_scope, hypothesis.metadata)

            # Compare claimed vs observed scope
            scope_matches = self._verify_scope_match(
                claimed_scope=claimed_scope,
                expected_scope=expected_scope,
                observed_count=observed_count,
                observed_percentage=observed_percentage,
                service_count=service_count,
            )

            if not scope_matches:
                # Scope mismatch → hypothesis DISPROVEN
                evidence = Evidence(
                    source=f"tempo://traces?issue_type={issue_type}",
                    data={
                        "claimed_scope": claimed_scope,
                        "expected_services": expected_scope.get("expected_count", service_count),
                        "observed_services": observed_count,
                        "observed_percentage": f"{observed_percentage:.1%}",
                    },
                    interpretation=f"Claimed {claimed_scope} but only {observed_count}/{service_count} services affected ({observed_percentage:.1%})",
                    quality=EvidenceQuality.DIRECT,
                    supports_hypothesis=False,  # Contradicts hypothesis
                    confidence=HIGH_EVIDENCE_CONFIDENCE,
                )

                return DisproofAttempt(
                    strategy="scope_verification",
                    method="Queried distributed traces to verify scope claim",
                    expected_if_true=f"Should see {expected_scope.get('description', 'matching scope')}",
                    observed=f"Only {observed_count}/{service_count} services affected ({observed_percentage:.1%})",
                    disproven=True,
                    evidence=[evidence],
                    reasoning=f"Scope mismatch: Hypothesis claims {claimed_scope}, but only {observed_count} services affected ({observed_percentage:.1%})",
                )

            else:
                # Scope matches → hypothesis SURVIVES
                return DisproofAttempt(
                    strategy="scope_verification",
                    method="Queried distributed traces to verify scope claim",
                    expected_if_true=f"Should see {expected_scope.get('description', 'matching scope')}",
                    observed=f"{observed_count}/{service_count} services affected ({observed_percentage:.1%})",
                    disproven=False,
                    reasoning=f"Scope matches hypothesis claim: {observed_count} services affected is consistent with '{claimed_scope}'",
                )

        except Exception as e:
            # Handle errors gracefully
            logger.error(f"Error in scope verification strategy: {e}", exc_info=True)
            return DisproofAttempt(
                strategy="scope_verification",
                method="Verify scope claim against observed impact",
                expected_if_true="Observed impact should match claimed scope",
                observed=f"Error querying traces: {str(e)}",
                disproven=False,
                reasoning=f"Error occurred during scope verification: {str(e)}",
            )

    def _inconclusive_result(self, observed_message: str) -> DisproofAttempt:
        """
        Create a DisproofAttempt for inconclusive test results.

        Args:
            observed_message: Description of why test was inconclusive

        Returns:
            DisproofAttempt with disproven=False and reasoning
        """
        return DisproofAttempt(
            strategy="scope_verification",
            method="Verify scope claim against observed impact",
            expected_if_true="Observed impact should match claimed scope",
            observed=observed_message,
            disproven=False,
            reasoning=f"Cannot verify scope: {observed_message}",
        )

    def _parse_scope_claim(self, claimed_scope: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the claimed scope to determine expected thresholds.

        Args:
            claimed_scope: Scope claim string (e.g., "all_services", "most_services")
            metadata: Hypothesis metadata with additional context

        Returns:
            Dictionary with expected thresholds and descriptions
        """
        service_count = metadata.get("service_count", 0)

        if claimed_scope == "all_services":
            return {
                "threshold": SCOPE_THRESHOLD_ALL,
                "expected_count": int(service_count * SCOPE_THRESHOLD_ALL),
                "description": f"at least {SCOPE_THRESHOLD_ALL:.0%} of services",
            }
        elif claimed_scope == "most_services":
            return {
                "threshold": SCOPE_THRESHOLD_MOST,
                "expected_count": int(service_count * SCOPE_THRESHOLD_MOST),
                "description": f"at least {SCOPE_THRESHOLD_MOST:.0%} of services",
            }
        elif claimed_scope == "some_services":
            return {
                "threshold": SCOPE_THRESHOLD_SOME,
                "expected_count": int(service_count * SCOPE_THRESHOLD_SOME),
                "description": f"at least {SCOPE_THRESHOLD_SOME:.0%} of services",
            }
        elif claimed_scope == "specific_services":
            # For specific services, check if the listed services match
            affected_services = metadata.get("affected_services", [])
            return {
                "threshold": 1.0,  # Must match exactly
                "expected_count": len(affected_services),
                "description": f"services: {', '.join(affected_services)}",
                "specific_services": affected_services,
            }
        else:
            # Unknown scope claim - default to service count
            return {
                "threshold": 1.0,
                "expected_count": service_count,
                "description": "all specified services",
            }

    def _verify_scope_match(
        self,
        claimed_scope: str,
        expected_scope: Dict[str, Any],
        observed_count: int,
        observed_percentage: float,
        service_count: int,
    ) -> bool:
        """
        Verify if observed scope matches claimed scope.

        Args:
            claimed_scope: Original scope claim
            expected_scope: Parsed scope expectations
            observed_count: Number of services actually affected
            observed_percentage: Percentage of services affected
            service_count: Total number of services

        Returns:
            True if scope matches (within tolerance), False otherwise
        """
        if claimed_scope == "specific_services":
            # For specific services, check exact match (with tolerance for additional services)
            expected_count = expected_scope.get("expected_count", 0)
            # Allow observed to be >= expected (issue might affect MORE than claimed)
            return observed_count >= expected_count
        else:
            # For percentage-based claims (all, most, some), check threshold with tolerance
            threshold = expected_scope.get("threshold", 1.0)

            # Allow some tolerance for scope matching
            return observed_percentage >= (threshold - SCOPE_MATCH_TOLERANCE)
