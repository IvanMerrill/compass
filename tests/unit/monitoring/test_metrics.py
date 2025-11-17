"""Tests for OpenTelemetry metrics module."""

from unittest.mock import MagicMock, patch, call
import pytest

from compass.monitoring import metrics


class TestGetMeter:
    """Tests for get_meter function."""

    def test_returns_meter_instance(self):
        """Test that get_meter returns a meter instance."""
        meter = metrics.get_meter()
        assert meter is not None

    def test_returns_same_instance_on_subsequent_calls(self):
        """Test that get_meter returns the same instance."""
        meter1 = metrics.get_meter()
        meter2 = metrics.get_meter()
        assert meter1 is meter2


class TestInitMetrics:
    """Tests for init_metrics function."""

    @patch("compass.monitoring.metrics.PeriodicExportingMetricReader")
    @patch("compass.monitoring.metrics.OTLPMetricExporter")
    @patch("compass.monitoring.metrics.metrics.set_meter_provider")
    def test_with_otlp_endpoint(
        self, mock_set_provider, mock_otlp_exporter, mock_reader
    ):
        """Test initialization with OTLP endpoint."""
        meter = metrics.init_metrics(
            service_name="test-service",
            service_version="1.0.0",
            environment="production",
            otlp_endpoint="localhost:4317",
        )

        # Verify OTLP exporter was created
        mock_otlp_exporter.assert_called_once_with(
            endpoint="localhost:4317",
            insecure=True,
        )

        # Verify meter provider was set
        mock_set_provider.assert_called_once()

        # Verify meter returned
        assert meter is not None

    @patch("compass.monitoring.metrics.PeriodicExportingMetricReader")
    @patch("compass.monitoring.metrics.ConsoleMetricExporter")
    @patch("compass.monitoring.metrics.metrics.set_meter_provider")
    def test_with_console_export(
        self, mock_set_provider, mock_console_exporter, mock_reader
    ):
        """Test initialization with console export."""
        meter = metrics.init_metrics(
            service_name="test-service",
            console_export=True,
        )

        # Verify console exporter was created
        mock_console_exporter.assert_called_once()

        # Verify meter provider was set
        mock_set_provider.assert_called_once()

        assert meter is not None

    @patch("compass.monitoring.metrics.metrics.set_meter_provider")
    def test_with_custom_exporter(self, mock_set_provider):
        """Test initialization with custom exporter."""
        custom_exporter = MagicMock()

        meter = metrics.init_metrics(
            service_name="test-service",
            custom_exporter=custom_exporter,
        )

        # Verify meter provider was set
        mock_set_provider.assert_called_once()

        assert meter is not None

    @patch("compass.monitoring.metrics.logger")
    def test_logs_warning_when_no_exporters(self, mock_logger):
        """Test that a warning is logged when no exporters are configured."""
        meter = metrics.init_metrics(
            service_name="test-service",
        )

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        assert meter is not None


class TestTrackingFunctions:
    """Tests for metric tracking functions."""

    @patch("compass.monitoring.metrics._create_investigation_counter")
    def test_track_investigation_started(self, mock_create_counter):
        """Test tracking investigation start."""
        mock_counter = MagicMock()
        mock_create_counter.return_value = mock_counter

        metrics.track_investigation_started(
            incident_type="database",
            priority="critical",
        )

        mock_counter.add.assert_called_once_with(
            1,
            attributes={
                "incident_type": "database",
                "priority": "critical",
                "status": "started",
            },
        )

    @patch("compass.monitoring.metrics._create_investigation_counter")
    @patch("compass.monitoring.metrics._create_investigation_duration_histogram")
    @patch("compass.monitoring.metrics._create_investigation_cost_histogram")
    def test_track_investigation_completed(
        self, mock_cost_hist, mock_duration_hist, mock_counter
    ):
        """Test tracking investigation completion."""
        mock_counter_inst = MagicMock()
        mock_duration_inst = MagicMock()
        mock_cost_inst = MagicMock()

        mock_counter.return_value = mock_counter_inst
        mock_duration_hist.return_value = mock_duration_inst
        mock_cost_hist.return_value = mock_cost_inst

        metrics.track_investigation_completed(
            incident_type="network",
            priority="routine",
            duration_seconds=120.5,
            total_cost_usd=0.75,
            outcome="resolved",
        )

        # Verify counter was incremented
        mock_counter_inst.add.assert_called_once()

        # Verify duration was recorded
        mock_duration_inst.record.assert_called_once_with(
            120.5,
            attributes={"phase": "total", "outcome": "resolved"},
        )

        # Verify cost was recorded
        mock_cost_inst.record.assert_called_once_with(
            0.75,
            attributes={
                "agent_type": "orchestrator",
                "model": "mixed",
                "priority": "routine",
            },
        )

    @patch("compass.monitoring.metrics._create_hypothesis_counter")
    def test_track_hypothesis_generated_high_confidence(self, mock_create_counter):
        """Test tracking hypothesis with high confidence."""
        mock_counter = MagicMock()
        mock_create_counter.return_value = mock_counter

        metrics.track_hypothesis_generated(
            agent_type="database",
            confidence=0.85,
        )

        mock_counter.add.assert_called_once_with(
            1,
            attributes={
                "agent_type": "database",
                "confidence_level": "high",
            },
        )

    @patch("compass.monitoring.metrics._create_hypothesis_counter")
    def test_track_hypothesis_generated_medium_confidence(self, mock_create_counter):
        """Test tracking hypothesis with medium confidence."""
        mock_counter = MagicMock()
        mock_create_counter.return_value = mock_counter

        metrics.track_hypothesis_generated(
            agent_type="network",
            confidence=0.65,
        )

        mock_counter.add.assert_called_once_with(
            1,
            attributes={
                "agent_type": "network",
                "confidence_level": "medium",
            },
        )

    @patch("compass.monitoring.metrics._create_hypothesis_counter")
    def test_track_hypothesis_generated_low_confidence(self, mock_create_counter):
        """Test tracking hypothesis with low confidence."""
        mock_counter = MagicMock()
        mock_create_counter.return_value = mock_counter

        metrics.track_hypothesis_generated(
            agent_type="application",
            confidence=0.3,
        )

        mock_counter.add.assert_called_once_with(
            1,
            attributes={
                "agent_type": "application",
                "confidence_level": "low",
            },
        )

    @patch("compass.monitoring.metrics._create_agent_calls_counter")
    @patch("compass.monitoring.metrics._create_agent_latency_histogram")
    @patch("compass.monitoring.metrics._create_agent_tokens_counter")
    def test_track_agent_call_success(
        self, mock_tokens, mock_latency, mock_calls
    ):
        """Test tracking successful agent call."""
        mock_calls_inst = MagicMock()
        mock_latency_inst = MagicMock()
        mock_tokens_inst = MagicMock()

        mock_calls.return_value = mock_calls_inst
        mock_latency.return_value = mock_latency_inst
        mock_tokens.return_value = mock_tokens_inst

        metrics.track_agent_call(
            agent_type="database",
            phase="observe",
            latency_seconds=1.5,
            input_tokens=500,
            output_tokens=200,
            cached_tokens=50,
            model="gpt-4o-mini",
            success=True,
        )

        # Verify call counter
        mock_calls_inst.add.assert_called_once_with(
            1,
            attributes={
                "agent_type": "database",
                "phase": "observe",
                "status": "success",
            },
        )

        # Verify latency histogram
        mock_latency_inst.record.assert_called_once_with(
            1.5,
            attributes={
                "agent_type": "database",
                "phase": "observe",
            },
        )

        # Verify token counters (3 calls: input, output, cached)
        assert mock_tokens_inst.add.call_count == 3

    @patch("compass.monitoring.metrics._create_agent_calls_counter")
    @patch("compass.monitoring.metrics._create_agent_latency_histogram")
    @patch("compass.monitoring.metrics._create_agent_tokens_counter")
    def test_track_agent_call_no_cached_tokens(
        self, mock_tokens, mock_latency, mock_calls
    ):
        """Test tracking agent call without cached tokens."""
        mock_tokens_inst = MagicMock()
        mock_tokens.return_value = mock_tokens_inst

        metrics.track_agent_call(
            agent_type="network",
            phase="decide",
            latency_seconds=0.5,
            input_tokens=100,
            output_tokens=50,
            cached_tokens=0,
            model="claude-haiku",
            success=True,
        )

        # Verify only 2 token calls (no cached)
        assert mock_tokens_inst.add.call_count == 2

    @patch("compass.monitoring.metrics._create_human_decision_time_histogram")
    def test_track_human_decision_high_confidence(self, mock_create_histogram):
        """Test tracking human decision with high confidence."""
        mock_histogram = MagicMock()
        mock_create_histogram.return_value = mock_histogram

        metrics.track_human_decision(
            decision_type="hypothesis_selection",
            decision_time_seconds=45.0,
            confidence=80,
            agreed_with_ai=True,
        )

        mock_histogram.record.assert_called_once_with(
            45.0,
            attributes={
                "decision_type": "hypothesis_selection",
                "agreed_with_ai": "true",
                "confidence_level": "high",
            },
        )

    @patch("compass.monitoring.metrics._create_human_decision_time_histogram")
    def test_track_human_decision_medium_confidence(self, mock_create_histogram):
        """Test tracking human decision with medium confidence."""
        mock_histogram = MagicMock()
        mock_create_histogram.return_value = mock_histogram

        metrics.track_human_decision(
            decision_type="evidence_evaluation",
            decision_time_seconds=30.0,
            confidence=60,
            agreed_with_ai=False,
        )

        mock_histogram.record.assert_called_once_with(
            30.0,
            attributes={
                "decision_type": "evidence_evaluation",
                "agreed_with_ai": "false",
                "confidence_level": "medium",
            },
        )

    @patch("compass.monitoring.metrics._create_human_decision_time_histogram")
    def test_track_human_decision_low_confidence(self, mock_create_histogram):
        """Test tracking human decision with low confidence."""
        mock_histogram = MagicMock()
        mock_create_histogram.return_value = mock_histogram

        metrics.track_human_decision(
            decision_type="final_approval",
            decision_time_seconds=120.0,
            confidence=40,
            agreed_with_ai=True,
        )

        mock_histogram.record.assert_called_once_with(
            120.0,
            attributes={
                "decision_type": "final_approval",
                "agreed_with_ai": "true",
                "confidence_level": "low",
            },
        )

    @patch("compass.monitoring.metrics._create_cache_operations_counter")
    def test_track_cache_hit(self, mock_create_counter):
        """Test tracking cache hit."""
        mock_counter = MagicMock()
        mock_create_counter.return_value = mock_counter

        metrics.track_cache_operation(
            cache_type="hypothesis",
            hit=True,
        )

        mock_counter.add.assert_called_once_with(
            1,
            attributes={
                "cache_type": "hypothesis",
                "result": "hit",
            },
        )

    @patch("compass.monitoring.metrics._create_cache_operations_counter")
    def test_track_cache_miss(self, mock_create_counter):
        """Test tracking cache miss."""
        mock_counter = MagicMock()
        mock_create_counter.return_value = mock_counter

        metrics.track_cache_operation(
            cache_type="evidence",
            hit=False,
        )

        mock_counter.add.assert_called_once_with(
            1,
            attributes={
                "cache_type": "evidence",
                "result": "miss",
            },
        )

    @patch("compass.monitoring.metrics._create_errors_counter")
    def test_track_error(self, mock_create_counter):
        """Test tracking errors."""
        mock_counter = MagicMock()
        mock_create_counter.return_value = mock_counter

        metrics.track_error(
            error_type="rate_limit",
            component="llm_provider",
            severity="warning",
        )

        mock_counter.add.assert_called_once_with(
            1,
            attributes={
                "error_type": "rate_limit",
                "component": "llm_provider",
                "severity": "warning",
            },
        )

    @patch("compass.monitoring.metrics._create_hypothesis_disproof_counter")
    def test_track_hypothesis_disproof(self, mock_create_counter):
        """Test tracking hypothesis disproof attempt."""
        mock_counter = MagicMock()
        mock_create_counter.return_value = mock_counter

        metrics.track_hypothesis_disproof(
            strategy="temporal_correlation",
            outcome="disproven",
        )

        mock_counter.add.assert_called_once_with(
            1,
            attributes={
                "strategy": "temporal_correlation",
                "outcome": "disproven",
            },
        )

    @patch("compass.monitoring.metrics._create_agent_retries_counter")
    def test_track_agent_retry(self, mock_create_counter):
        """Test tracking agent retry."""
        mock_counter = MagicMock()
        mock_create_counter.return_value = mock_counter

        metrics.track_agent_retry(
            agent_type="database",
            reason="timeout",
        )

        mock_counter.add.assert_called_once_with(
            1,
            attributes={
                "agent_type": "database",
                "reason": "timeout",
            },
        )

    @patch("compass.monitoring.metrics._create_active_investigations_gauge")
    def test_track_active_investigations_change(self, mock_create_gauge):
        """Test tracking active investigations count change."""
        mock_gauge = MagicMock()
        mock_create_gauge.return_value = mock_gauge

        metrics.track_active_investigations_change(
            priority="critical",
            delta=1,
        )

        mock_gauge.add.assert_called_once_with(
            1,
            attributes={
                "priority": "critical",
            },
        )

    @patch("compass.monitoring.metrics._create_circuit_breaker_gauge")
    def test_track_circuit_breaker_closed(self, mock_create_gauge):
        """Test tracking circuit breaker in closed state."""
        mock_gauge = MagicMock()
        mock_create_gauge.return_value = mock_gauge

        metrics.track_circuit_breaker_state(
            service="llm_provider",
            circuit_name="openai",
            state="closed",
        )

        mock_gauge.add.assert_called_once_with(
            0,
            attributes={
                "service": "llm_provider",
                "circuit_name": "openai",
                "state": "closed",
            },
        )

    @patch("compass.monitoring.metrics._create_circuit_breaker_gauge")
    def test_track_circuit_breaker_half_open(self, mock_create_gauge):
        """Test tracking circuit breaker in half-open state."""
        mock_gauge = MagicMock()
        mock_create_gauge.return_value = mock_gauge

        metrics.track_circuit_breaker_state(
            service="llm_provider",
            circuit_name="anthropic",
            state="half_open",
        )

        mock_gauge.add.assert_called_once_with(
            1,
            attributes={
                "service": "llm_provider",
                "circuit_name": "anthropic",
                "state": "half_open",
            },
        )

    @patch("compass.monitoring.metrics._create_circuit_breaker_gauge")
    def test_track_circuit_breaker_open(self, mock_create_gauge):
        """Test tracking circuit breaker in open state."""
        mock_gauge = MagicMock()
        mock_create_gauge.return_value = mock_gauge

        metrics.track_circuit_breaker_state(
            service="mcp_server",
            circuit_name="prometheus",
            state="open",
        )

        mock_gauge.add.assert_called_once_with(
            2,
            attributes={
                "service": "mcp_server",
                "circuit_name": "prometheus",
                "state": "open",
            },
        )

    @patch("compass.monitoring.metrics._create_ai_override_counter")
    def test_track_ai_override(self, mock_create_counter):
        """Test tracking AI override."""
        mock_counter = MagicMock()
        mock_create_counter.return_value = mock_counter

        metrics.track_ai_override(
            decision_type="hypothesis_ranking",
            outcome="better",
        )

        mock_counter.add.assert_called_once_with(
            1,
            attributes={
                "decision_type": "hypothesis_ranking",
                "outcome": "better",
            },
        )

    @patch("compass.monitoring.metrics._create_external_api_latency_histogram")
    @patch("compass.monitoring.metrics._create_external_api_errors_counter")
    def test_track_external_api_call_success(
        self, mock_errors, mock_latency
    ):
        """Test tracking successful external API call."""
        mock_latency_inst = MagicMock()
        mock_latency.return_value = mock_latency_inst

        metrics.track_external_api_call(
            service="openai",
            endpoint="/v1/chat/completions",
            latency_seconds=0.8,
            success=True,
        )

        mock_latency_inst.record.assert_called_once_with(
            0.8,
            attributes={
                "service": "openai",
                "endpoint": "/v1/chat/completions",
            },
        )

        # Errors counter should not be called for success
        mock_errors.assert_not_called()

    @patch("compass.monitoring.metrics._create_external_api_latency_histogram")
    @patch("compass.monitoring.metrics._create_external_api_errors_counter")
    def test_track_external_api_call_failure(
        self, mock_errors, mock_latency
    ):
        """Test tracking failed external API call."""
        mock_latency_inst = MagicMock()
        mock_errors_inst = MagicMock()
        mock_latency.return_value = mock_latency_inst
        mock_errors.return_value = mock_errors_inst

        metrics.track_external_api_call(
            service="anthropic",
            endpoint="/v1/messages",
            latency_seconds=2.0,
            success=False,
            error_type="rate_limit",
        )

        # Both latency and errors should be tracked
        mock_latency_inst.record.assert_called_once()
        mock_errors_inst.add.assert_called_once_with(
            1,
            attributes={
                "service": "anthropic",
                "error_type": "rate_limit",
            },
        )

    @patch("compass.monitoring.metrics._create_cache_size_gauge")
    def test_track_cache_size(self, mock_create_gauge):
        """Test tracking cache size."""
        mock_gauge = MagicMock()
        mock_create_gauge.return_value = mock_gauge

        metrics.track_cache_size(
            cache_type="hypothesis",
            size_bytes=1024000,
        )

        mock_gauge.add.assert_called_once_with(
            1024000,
            attributes={
                "cache_type": "hypothesis",
            },
        )

    @patch("compass.monitoring.metrics._create_db_pool_size_gauge")
    @patch("compass.monitoring.metrics._create_db_pool_active_gauge")
    def test_track_db_pool_stats(self, mock_active, mock_size):
        """Test tracking database pool statistics."""
        mock_size_inst = MagicMock()
        mock_active_inst = MagicMock()
        mock_size.return_value = mock_size_inst
        mock_active.return_value = mock_active_inst

        metrics.track_db_pool_stats(
            pool_name="compass_primary",
            pool_size=20,
            active_connections=15,
        )

        mock_size_inst.add.assert_called_once_with(
            20,
            attributes={
                "pool_name": "compass_primary",
            },
        )

        mock_active_inst.add.assert_called_once_with(
            15,
            attributes={
                "pool_name": "compass_primary",
            },
        )

    @patch("compass.monitoring.metrics._create_db_query_duration_histogram")
    def test_track_db_query(self, mock_create_histogram):
        """Test tracking database query duration."""
        mock_histogram = MagicMock()
        mock_create_histogram.return_value = mock_histogram

        metrics.track_db_query(
            query_type="SELECT",
            duration_seconds=0.025,
        )

        mock_histogram.record.assert_called_once_with(
            0.025,
            attributes={
                "query_type": "SELECT",
            },
        )
