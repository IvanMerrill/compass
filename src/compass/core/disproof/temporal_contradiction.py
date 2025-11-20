"""
Temporal Contradiction Disproof Strategy.

This strategy checks if the observed issue existed BEFORE the suspected cause.
If so, the suspected cause cannot be the root cause, disproving the hypothesis.

Example:
    Hypothesis: "Connection pool exhaustion caused by deployment at 10:30"
    Query: db_connection_pool_utilization from 09:30 to 11:30
    Result: Pool was already exhausted at 08:00 (2.5 hours before deployment)
    Conclusion: Hypothesis DISPROVEN (issue predates suspected cause)

Algorithm:
    1. Extract suspected cause time from hypothesis metadata
    2. Query metric history from 1 hour before to 1 hour after
    3. Find when issue first appeared (metric >= threshold)
    4. If issue started >5 minutes before suspected cause → DISPROVEN
    5. Otherwise → hypothesis SURVIVES
"""
from datetime import datetime, timedelta, timezone
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
QUERY_TIME_WINDOW_HOURS = 1  # Hours before/after suspected cause to query
QUERY_STEP_SECONDS = 60  # Metric query resolution (1 minute)
ISSUE_THRESHOLD = 0.9  # Threshold for "issue detected" (90% for utilization)
TEMPORAL_BUFFER_MINUTES = 5  # Buffer to account for timing uncertainty
HIGH_EVIDENCE_CONFIDENCE = 0.9  # Confidence for DIRECT temporal evidence


class TemporalContradictionStrategy:
    """
    Disproof strategy that checks temporal relationships between cause and effect.

    If the observed issue existed BEFORE the suspected cause, the causal
    relationship is disproven.
    """

    def __init__(self, grafana_client: Any):
        """
        Initialize temporal contradiction strategy.

        Args:
            grafana_client: Client for querying Grafana metrics
        """
        self.grafana = grafana_client

    def attempt_disproof(self, hypothesis: Hypothesis) -> DisproofAttempt:
        """
        Attempt to disprove hypothesis by checking temporal relationships.

        This method queries metric history to determine if the observed issue
        existed BEFORE the suspected cause. If so, the causal relationship is
        disproven.

        Required hypothesis metadata:
            - suspected_time (str): ISO format datetime of suspected cause
            - metric (str): Metric name to query (e.g., "db_connection_pool_utilization")

        Args:
            hypothesis: Hypothesis to test with metadata containing suspected_time and metric

        Returns:
            DisproofAttempt with one of:
                - disproven=True: Issue predates suspected cause
                - disproven=False: Timing supports hypothesis OR test inconclusive
        """
        try:
            # Extract suspected cause time from hypothesis metadata
            suspected_time = self._parse_suspected_time(hypothesis)

            if suspected_time is None:
                logger.debug("No suspected_time in hypothesis metadata", hypothesis_id=hypothesis.id)
                return self._inconclusive_result("No suspected time provided in hypothesis metadata")

            # Extract metric to query from hypothesis metadata
            metric = hypothesis.metadata.get("metric", "")
            if not metric:
                logger.debug("No metric in hypothesis metadata", hypothesis_id=hypothesis.id)
                return self._inconclusive_result("No metric specified in hypothesis metadata")

            # Query Grafana for metric history
            start_time = suspected_time - timedelta(hours=QUERY_TIME_WINDOW_HOURS)
            end_time = suspected_time + timedelta(hours=QUERY_TIME_WINDOW_HOURS)

            logger.info(
                "Querying Grafana for temporal analysis",
                metric=metric,
                suspected_time=suspected_time.isoformat(),
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
            )

            time_series = self.grafana.query_range(
                query=metric,
                start=start_time,
                end=end_time,
                step=QUERY_STEP_SECONDS,
            )

            # Analyze: Did issue exist BEFORE suspected cause?
            issue_start_time = self._find_issue_start_time(time_series, suspected_time)

            if issue_start_time is None:
                logger.debug("No clear issue detected in time series", metric=metric)
                return self._inconclusive_result("No clear issue threshold detected in metrics")

            # Check if issue started BEFORE suspected cause (with temporal buffer)
            time_buffer = timedelta(minutes=TEMPORAL_BUFFER_MINUTES)

            if issue_start_time < (suspected_time - time_buffer):
                # Issue existed BEFORE cause → hypothesis DISPROVEN
                duration_before = suspected_time - issue_start_time

                evidence = Evidence(
                    source=f"grafana://{metric}",
                    data={"issue_start": issue_start_time.isoformat(), "suspected_time": suspected_time.isoformat()},
                    interpretation=f"Issue started {duration_before.total_seconds() / 60:.1f} minutes before suspected cause",
                    quality=EvidenceQuality.DIRECT,
                    supports_hypothesis=False,  # Contradicts hypothesis
                    confidence=HIGH_EVIDENCE_CONFIDENCE,
                )

                return DisproofAttempt(
                    strategy="temporal_contradiction",
                    method="Queried metric history to check temporal relationship",
                    expected_if_true=f"Issue should start at or after {suspected_time.isoformat()}",
                    observed=f"Issue started at {issue_start_time.isoformat()} ({duration_before.total_seconds() / 60:.1f} min before)",
                    disproven=True,
                    evidence=[evidence],
                    reasoning=f"Observed issue existed before suspected cause, disproving causal relationship. Issue detected {duration_before.total_seconds() / 60:.1f} minutes before suspected cause.",
                )

            else:
                # Issue started AFTER (or very close to) suspected cause → hypothesis SURVIVES
                return DisproofAttempt(
                    strategy="temporal_contradiction",
                    method="Queried metric history to check temporal relationship",
                    expected_if_true=f"Issue should start at or after {suspected_time.isoformat()}",
                    observed=f"Issue started at {issue_start_time.isoformat()}",
                    disproven=False,
                    reasoning="Timing supports hypothesis - issue started at or after suspected cause",
                )

        except Exception as e:
            # Handle errors gracefully
            logger.error(f"Error in temporal contradiction strategy: {e}", exc_info=True)
            return DisproofAttempt(
                strategy="temporal_contradiction",
                method="Check if issue existed before suspected cause",
                expected_if_true="Issue should start at or after suspected cause time",
                observed=f"Error querying metrics: {str(e)}",
                disproven=False,
                reasoning=f"Error occurred during temporal analysis: {str(e)}",
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
            strategy="temporal_contradiction",
            method="Check if issue existed before suspected cause",
            expected_if_true="Issue should start at or after suspected cause time",
            observed=observed_message,
            disproven=False,
            reasoning=f"Cannot determine temporal relationship: {observed_message}",
        )

    def _parse_suspected_time(self, hypothesis: Hypothesis) -> Optional[datetime]:
        """
        Extract suspected cause time from hypothesis metadata.

        Args:
            hypothesis: Hypothesis to extract time from

        Returns:
            Datetime of suspected cause, or None if not found
        """
        suspected_time_str = hypothesis.metadata.get("suspected_time")

        if not suspected_time_str:
            return None

        try:
            # Parse ISO format datetime
            if isinstance(suspected_time_str, str):
                # Handle both 'Z' suffix and explicit timezone
                if suspected_time_str.endswith("Z"):
                    suspected_time_str = suspected_time_str[:-1] + "+00:00"

                return datetime.fromisoformat(suspected_time_str)
            elif isinstance(suspected_time_str, datetime):
                return suspected_time_str
            else:
                return None

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse suspected_time: {e}")
            return None

    def _find_issue_start_time(
        self, time_series: List[Dict[str, Any]], suspected_time: datetime
    ) -> Optional[datetime]:
        """
        Find when the issue first started based on metric values.

        Scans time series data to find the first data point where the metric
        exceeds ISSUE_THRESHOLD (default: 0.9 for utilization metrics).

        Args:
            time_series: List of time series data points with 'time' and 'value' keys
            suspected_time: Suspected cause time for context (unused but kept for future)

        Returns:
            Datetime when issue first detected, or None if threshold never exceeded
        """
        if not time_series:
            logger.debug("Empty time series provided")
            return None

        for data_point in time_series:
            try:
                value = data_point.get("value", 0)
                time_str = data_point.get("time", "")

                # Parse time
                if isinstance(time_str, str):
                    if time_str.endswith("Z"):
                        time_str = time_str[:-1] + "+00:00"
                    point_time = datetime.fromisoformat(time_str)
                elif isinstance(time_str, datetime):
                    point_time = time_str
                else:
                    continue

                # Check if value exceeds threshold
                if float(value) >= ISSUE_THRESHOLD:
                    return point_time

            except (ValueError, TypeError, KeyError) as e:
                logger.debug(f"Skipping invalid data point: {e}")
                continue

        return None
