"""
Metric Threshold Validation Disproof Strategy.

This strategy validates that hypothesis metric claims match observed metric values.
If a hypothesis claims "pool at 95% utilization" but the metric shows 45%, the
hypothesis is disproven.

Example:
    Hypothesis: "Connection pool at 95% utilization causing timeouts"
    Claim: db_connection_pool_utilization >= 0.95
    Query: db_connection_pool_utilization from Prometheus
    Result: Actual value is 0.45 (45%)
    Conclusion: Hypothesis DISPROVEN (claimed >= 95%, observed 45%)

Algorithm:
    1. Extract metric claims from hypothesis metadata
    2. Query Prometheus for current metric values
    3. Compare claimed thresholds vs observed values
    4. If any claim not supported (outside tolerance) → DISPROVEN
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
HIGH_EVIDENCE_CONFIDENCE = 0.9  # Confidence for DIRECT metric evidence
THRESHOLD_TOLERANCE = 0.05  # 5% tolerance for threshold matching

# Supported comparison operators
OPERATORS = {
    ">=": lambda observed, threshold: observed >= (threshold - THRESHOLD_TOLERANCE),
    "<=": lambda observed, threshold: observed <= (threshold + THRESHOLD_TOLERANCE),
    ">": lambda observed, threshold: observed > (threshold - THRESHOLD_TOLERANCE),
    "<": lambda observed, threshold: observed < (threshold + THRESHOLD_TOLERANCE),
    "==": lambda observed, threshold: abs(observed - threshold) <= THRESHOLD_TOLERANCE,
    "!=": lambda observed, threshold: abs(observed - threshold) > THRESHOLD_TOLERANCE,
}


class MetricThresholdValidationStrategy:
    """
    Disproof strategy that validates hypothesis metric claims against observed values.

    Queries Prometheus to check if claimed metric thresholds match reality.
    """

    def __init__(self, prometheus_client: Any):
        """
        Initialize metric threshold validation strategy.

        Args:
            prometheus_client: Client for querying Prometheus metrics
        """
        self.prometheus = prometheus_client

    def attempt_disproof(self, hypothesis: Hypothesis) -> DisproofAttempt:
        """
        Attempt to disprove hypothesis by validating metric claims.

        This method queries Prometheus to check if the hypothesis's claimed
        metric thresholds match observed reality. If claims are not supported
        by actual metrics, the hypothesis is disproven.

        Required hypothesis metadata:
            - metric_claims (Dict): Dictionary of metric claims
              {
                  "metric_name": {
                      "threshold": float,
                      "operator": str (>=, <=, >, <, ==, !=),
                      "description": str (optional)
                  }
              }

        Args:
            hypothesis: Hypothesis to test with metadata containing metric_claims

        Returns:
            DisproofAttempt with one of:
                - disproven=True: Metric claims not supported by observations
                - disproven=False: Claims supported OR test inconclusive
        """
        try:
            # Extract metric claims from hypothesis metadata
            metric_claims = hypothesis.metadata.get("metric_claims", {})

            if not metric_claims:
                logger.debug("No metric_claims in hypothesis metadata", hypothesis_id=hypothesis.id)
                return self._inconclusive_result("No metric claims provided in hypothesis metadata")

            logger.info(
                "Validating metric claims",
                claim_count=len(metric_claims),
                metrics=list(metric_claims.keys()),
            )

            # Validate each metric claim
            unsupported_claims = []
            supported_claims = []

            for metric_name, claim in metric_claims.items():
                threshold = claim.get("threshold")
                operator = claim.get("operator", ">=")
                description = claim.get("description", f"{metric_name} {operator} {threshold}")

                if threshold is None:
                    logger.warning(f"Metric claim missing threshold: {metric_name}")
                    continue

                # Query Prometheus for current metric value
                try:
                    result = self.prometheus.query(metric_name)

                    if not result or len(result) == 0:
                        logger.warning(f"No data returned for metric: {metric_name}")
                        continue

                    # Extract metric value from Prometheus response
                    observed_value = self._extract_metric_value(result[0])

                    if observed_value is None:
                        logger.warning(f"Could not extract value from metric: {metric_name}")
                        continue

                    # Check if claim is supported
                    claim_supported = self._validate_threshold(
                        observed=observed_value,
                        threshold=threshold,
                        operator=operator,
                    )

                    if claim_supported:
                        supported_claims.append({
                            "metric": metric_name,
                            "claimed": f"{operator} {threshold}",
                            "observed": observed_value,
                            "description": description,
                        })
                        logger.debug(
                            "Metric claim supported",
                            metric=metric_name,
                            observed=observed_value,
                            threshold=threshold,
                        )
                    else:
                        unsupported_claims.append({
                            "metric": metric_name,
                            "claimed": f"{operator} {threshold}",
                            "observed": observed_value,
                            "description": description,
                        })
                        logger.info(
                            "Metric claim NOT supported",
                            metric=metric_name,
                            observed=observed_value,
                            threshold=threshold,
                            operator=operator,
                        )

                except Exception as e:
                    logger.warning(f"Error querying metric {metric_name}: {e}")
                    continue

            # If any claims are unsupported → hypothesis DISPROVEN
            if unsupported_claims:
                evidence_list = []
                for claim in unsupported_claims:
                    evidence = Evidence(
                        source=f"prometheus://{claim['metric']}",
                        data={
                            "claimed": claim["claimed"],
                            "observed": claim["observed"],
                        },
                        interpretation=f"{claim['description']}: claimed {claim['claimed']}, observed {claim['observed']}",
                        quality=EvidenceQuality.DIRECT,
                        supports_hypothesis=False,  # Contradicts hypothesis
                        confidence=HIGH_EVIDENCE_CONFIDENCE,
                    )
                    evidence_list.append(evidence)

                unsupported_desc = ", ".join([
                    f"{c['metric']} (claimed {c['claimed']}, observed {c['observed']})"
                    for c in unsupported_claims
                ])

                return DisproofAttempt(
                    strategy="metric_threshold_validation",
                    method="Queried Prometheus to validate metric claims",
                    expected_if_true=f"Metrics should match claimed thresholds",
                    observed=f"{len(unsupported_claims)} claim(s) not supported: {unsupported_desc}",
                    disproven=True,
                    evidence=evidence_list,
                    reasoning=f"Metric claims not supported by observations. {len(unsupported_claims)} of {len(metric_claims)} claims failed validation.",
                )

            elif supported_claims:
                # All claims supported → hypothesis SURVIVES
                supported_desc = ", ".join([
                    f"{c['metric']} (claimed {c['claimed']}, observed {c['observed']})"
                    for c in supported_claims
                ])

                return DisproofAttempt(
                    strategy="metric_threshold_validation",
                    method="Queried Prometheus to validate metric claims",
                    expected_if_true=f"Metrics should match claimed thresholds",
                    observed=f"All {len(supported_claims)} claim(s) supported: {supported_desc}",
                    disproven=False,
                    reasoning=f"All metric claims supported by observations. {len(supported_claims)} of {len(metric_claims)} claims validated successfully.",
                )

            else:
                # No claims could be validated (all queries failed)
                return self._inconclusive_result("Unable to validate any metric claims (queries failed or no data)")

        except Exception as e:
            # Handle errors gracefully
            logger.error(f"Error in metric threshold validation strategy: {e}", exc_info=True)
            return DisproofAttempt(
                strategy="metric_threshold_validation",
                method="Validate metric claims against observed values",
                expected_if_true="Metric values should match claimed thresholds",
                observed=f"Error querying metrics: {str(e)}",
                disproven=False,
                reasoning=f"Error occurred during metric validation: {str(e)}",
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
            strategy="metric_threshold_validation",
            method="Validate metric claims against observed values",
            expected_if_true="Metric values should match claimed thresholds",
            observed=observed_message,
            disproven=False,
            reasoning=f"Cannot validate metrics: {observed_message}",
        )

    def _extract_metric_value(self, prometheus_result: Dict[str, Any]) -> Optional[float]:
        """
        Extract metric value from Prometheus query result.

        Prometheus returns: {"metric": {...}, "value": [timestamp, "value_string"]}

        Args:
            prometheus_result: Single result from Prometheus query

        Returns:
            Float value, or None if extraction failed
        """
        try:
            value_pair = prometheus_result.get("value", [])
            if len(value_pair) >= 2:
                # Value is second element, typically a string
                value_str = value_pair[1]
                return float(value_str)
            return None
        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"Failed to extract metric value: {e}")
            return None

    def _validate_threshold(self, observed: float, threshold: float, operator: str) -> bool:
        """
        Validate if observed value meets threshold criteria.

        Uses tolerance (THRESHOLD_TOLERANCE) to account for minor variations.

        Args:
            observed: Observed metric value
            threshold: Claimed threshold value
            operator: Comparison operator (>=, <=, >, <, ==, !=)

        Returns:
            True if claim is supported (within tolerance), False otherwise
        """
        if operator not in OPERATORS:
            logger.warning(f"Unsupported operator: {operator}, defaulting to >=")
            operator = ">="

        comparison_func = OPERATORS[operator]
        return comparison_func(observed, threshold)
