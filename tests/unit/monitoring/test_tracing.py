"""Tests for OpenTelemetry tracing module."""

from unittest.mock import MagicMock, patch, call
import pytest

from compass.monitoring import tracing
from compass.monitoring.tracing import SpanAttributes


class TestInitTracing:
    """Tests for init_tracing function."""

    @patch("compass.monitoring.tracing.BatchSpanProcessor")
    @patch("compass.monitoring.tracing.OTLPSpanExporter")
    @patch("compass.monitoring.tracing.trace.set_tracer_provider")
    @patch("compass.monitoring.tracing._instrument_libraries")
    def test_with_otlp_endpoint(
        self, mock_instrument, mock_set_provider, mock_otlp_exporter, mock_processor
    ):
        """Test initialization with OTLP endpoint."""
        tracer = tracing.init_tracing(
            service_name="test-service",
            service_version="1.0.0",
            environment="production",
            otlp_endpoint="tempo:4317",
        )

        # Verify OTLP exporter was created
        mock_otlp_exporter.assert_called_once_with(
            endpoint="tempo:4317",
            insecure=True,
        )

        # Verify tracer provider was set
        mock_set_provider.assert_called_once()

        # Verify libraries were instrumented
        mock_instrument.assert_called_once()

        # Verify tracer returned
        assert tracer is not None

    @patch("compass.monitoring.tracing.BatchSpanProcessor")
    @patch("compass.monitoring.tracing.ConsoleSpanExporter")
    @patch("compass.monitoring.tracing.trace.set_tracer_provider")
    @patch("compass.monitoring.tracing._instrument_libraries")
    def test_with_console_export(
        self, mock_instrument, mock_set_provider, mock_console_exporter, mock_processor
    ):
        """Test initialization with console export."""
        tracer = tracing.init_tracing(
            service_name="test-service",
            console_export=True,
        )

        # Verify console exporter was created
        mock_console_exporter.assert_called_once()

        # Verify tracer provider was set
        mock_set_provider.assert_called_once()

        # Verify libraries were instrumented
        mock_instrument.assert_called_once()

        assert tracer is not None

    @patch("compass.monitoring.tracing.BatchSpanProcessor")
    @patch("compass.monitoring.tracing.OTLPSpanExporter")
    @patch("compass.monitoring.tracing.ConsoleSpanExporter")
    @patch("compass.monitoring.tracing.trace.set_tracer_provider")
    @patch("compass.monitoring.tracing._instrument_libraries")
    def test_with_both_exporters(
        self,
        mock_instrument,
        mock_set_provider,
        mock_console_exporter,
        mock_otlp_exporter,
        mock_processor,
    ):
        """Test initialization with both OTLP and console exporters."""
        tracer = tracing.init_tracing(
            service_name="test-service",
            otlp_endpoint="tempo:4317",
            console_export=True,
        )

        # Both exporters should be created
        mock_otlp_exporter.assert_called_once()
        mock_console_exporter.assert_called_once()

        assert tracer is not None


class TestInstrumentLibraries:
    """Tests for _instrument_libraries function."""

    @patch("compass.monitoring.tracing.SQLAlchemyInstrumentor")
    @patch("compass.monitoring.tracing.RedisInstrumentor")
    def test_instruments_all_libraries(
        self, mock_redis, mock_sqlalchemy
    ):
        """Test that all available libraries are instrumented."""
        mock_sqlalchemy_inst = MagicMock()
        mock_redis_inst = MagicMock()

        mock_sqlalchemy.return_value = mock_sqlalchemy_inst
        mock_redis.return_value = mock_redis_inst

        tracing._instrument_libraries()

        # Verify instrumentors were called
        mock_sqlalchemy_inst.instrument.assert_called_once()
        mock_redis_inst.instrument.assert_called_once()

    @patch("compass.monitoring.tracing.SQLAlchemyInstrumentor")
    @patch("compass.monitoring.tracing.RedisInstrumentor")
    @patch("compass.monitoring.tracing.logger")
    def test_handles_instrumentation_failure(
        self, mock_logger, mock_redis, mock_sqlalchemy
    ):
        """Test that instrumentation failures are logged but don't crash."""
        mock_sqlalchemy_inst = MagicMock()
        mock_sqlalchemy_inst.instrument.side_effect = Exception("Instrumentation failed")
        mock_sqlalchemy.return_value = mock_sqlalchemy_inst

        # Should not raise exception
        tracing._instrument_libraries()

        # Verify warning was logged
        mock_logger.warning.assert_called()


class TestTraceInvestigation:
    """Tests for trace_investigation context manager."""

    @patch("compass.monitoring.tracing.trace.get_tracer")
    def test_creates_span_with_attributes(self, mock_get_tracer):
        """Test that investigation span is created with correct attributes."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        with tracing.trace_investigation(
            investigation_id="inv-123",
            priority="critical",
            incident_type="database",
        ) as span:
            pass

        # Verify span attributes were set
        assert mock_span.set_attribute.call_count >= 3
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.INVESTIGATION_ID, "inv-123"
        )
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.INVESTIGATION_PRIORITY, "critical"
        )
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.INVESTIGATION_INCIDENT_TYPE, "database"
        )

    @patch("compass.monitoring.tracing.trace.get_tracer")
    def test_sets_ok_status_on_success(self, mock_get_tracer):
        """Test that OK status is set when no exception occurs."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        with tracing.trace_investigation("inv-123", "routine", "network"):
            pass

        # Verify OK status was set
        mock_span.set_status.assert_called_once()

    @patch("compass.monitoring.tracing.trace.get_tracer")
    def test_records_exception_on_failure(self, mock_get_tracer):
        """Test that exceptions are recorded in the span."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        with pytest.raises(ValueError):
            with tracing.trace_investigation("inv-123", "routine", "api"):
                raise ValueError("Test error")

        # Verify exception was recorded
        mock_span.record_exception.assert_called_once()
        mock_span.set_status.assert_called_once()


class TestTraceAgentCall:
    """Tests for trace_agent_call context manager."""

    @patch("compass.monitoring.tracing.trace.get_tracer")
    def test_creates_span_with_attributes(self, mock_get_tracer):
        """Test that agent call span is created with correct attributes."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        with tracing.trace_agent_call(
            agent_type="database",
            role="worker",
            phase="observe",
        ) as span:
            pass

        # Verify span attributes
        assert mock_span.set_attribute.call_count >= 3
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.AGENT_TYPE, "database"
        )
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.AGENT_ROLE, "worker"
        )
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.INVESTIGATION_PHASE, "observe"
        )


class TestTraceLLMCall:
    """Tests for trace_llm_call context manager."""

    @patch("compass.monitoring.tracing.trace.get_tracer")
    def test_creates_span_with_attributes(self, mock_get_tracer):
        """Test that LLM call span is created with correct attributes."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        with tracing.trace_llm_call(
            provider="openai",
            model="gpt-4o-mini",
        ) as span:
            pass

        # Verify span attributes
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.LLM_PROVIDER, "openai"
        )
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.LLM_MODEL, "gpt-4o-mini"
        )


class TestTraceHypothesisGeneration:
    """Tests for trace_hypothesis_generation context manager."""

    @patch("compass.monitoring.tracing.trace.get_tracer")
    def test_creates_span_with_attributes(self, mock_get_tracer):
        """Test that hypothesis generation span is created."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        with tracing.trace_hypothesis_generation(hypothesis_id="hyp-456") as span:
            pass

        # Verify hypothesis ID attribute
        mock_span.set_attribute.assert_called_with(
            SpanAttributes.HYPOTHESIS_ID, "hyp-456"
        )


class TestAddInvestigationPhaseEvent:
    """Tests for add_investigation_phase_event function."""

    @patch("compass.monitoring.tracing.trace.get_current_span")
    def test_adds_event_to_current_span(self, mock_get_span):
        """Test that phase event is added to current span."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_get_span.return_value = mock_span

        tracing.add_investigation_phase_event(
            phase="observe",
            metadata={"agent_count": 5},
        )

        # Verify event was added
        mock_span.add_event.assert_called_once_with(
            "phase.observe",
            attributes={"phase": "observe", "agent_count": 5},
        )

    @patch("compass.monitoring.tracing.trace.get_current_span")
    def test_handles_no_current_span(self, mock_get_span):
        """Test that function handles case when no span is active."""
        mock_get_span.return_value = None

        # Should not raise exception
        tracing.add_investigation_phase_event(phase="decide")

    @patch("compass.monitoring.tracing.trace.get_current_span")
    def test_handles_non_recording_span(self, mock_get_span):
        """Test that function handles non-recording span."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = False
        mock_get_span.return_value = mock_span

        tracing.add_investigation_phase_event(phase="act")

        # Should not add event if not recording
        mock_span.add_event.assert_not_called()


class TestAddHumanDecisionEvent:
    """Tests for add_human_decision_event function."""

    @patch("compass.monitoring.tracing.trace.get_current_span")
    def test_adds_event_with_all_attributes(self, mock_get_span):
        """Test that human decision event is added with all attributes."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_get_span.return_value = mock_span

        tracing.add_human_decision_event(
            decision_type="hypothesis_selection",
            confidence=75,
            agreed_with_ai=True,
            decision_time_ms=45000,
        )

        # Verify event was added with correct attributes
        mock_span.add_event.assert_called_once_with(
            "human.decision",
            attributes={
                SpanAttributes.HUMAN_DECISION_TYPE: "hypothesis_selection",
                SpanAttributes.HUMAN_CONFIDENCE: 75,
                SpanAttributes.HUMAN_AGREED_WITH_AI: True,
                SpanAttributes.HUMAN_DECISION_TIME_MS: 45000,
            },
        )


class TestAddCostTracking:
    """Tests for add_cost_tracking function."""

    @patch("compass.monitoring.tracing.trace.get_current_span")
    def test_sets_cost_attributes(self, mock_get_span):
        """Test that cost tracking attributes are set on current span."""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_get_span.return_value = mock_span

        tracing.add_cost_tracking(
            input_tokens=1500,
            output_tokens=500,
            cached_tokens=200,
            cost_usd=0.042,
        )

        # Verify all cost attributes were set
        assert mock_span.set_attribute.call_count == 4
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.LLM_INPUT_TOKENS, 1500
        )
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.LLM_OUTPUT_TOKENS, 500
        )
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.LLM_CACHED_TOKENS, 200
        )
        mock_span.set_attribute.assert_any_call(
            SpanAttributes.LLM_COST_USD, 0.042
        )


class TestTracedDecorator:
    """Tests for @traced decorator."""

    @patch("compass.monitoring.tracing.trace.get_tracer")
    def test_decorates_sync_function(self, mock_get_tracer):
        """Test that decorator works with synchronous functions."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        @tracing.traced(attributes={"component": "test"})
        def test_function():
            return "result"

        result = test_function()

        # Verify function executed and returned correctly
        assert result == "result"

        # Verify span was created
        mock_tracer.start_as_current_span.assert_called_once()

        # Verify custom attribute was set
        mock_span.set_attribute.assert_called_with("component", "test")

    @patch("compass.monitoring.tracing.trace.get_tracer")
    @pytest.mark.asyncio
    async def test_decorates_async_function(self, mock_get_tracer):
        """Test that decorator works with asynchronous functions."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        @tracing.traced(span_name="custom_span")
        async def async_test_function():
            return "async result"

        result = await async_test_function()

        # Verify function executed and returned correctly
        assert result == "async result"

        # Verify span was created
        mock_tracer.start_as_current_span.assert_called_once()

    @patch("compass.monitoring.tracing.trace.get_tracer")
    def test_records_exception_in_decorated_function(self, mock_get_tracer):
        """Test that exceptions are recorded when decorated function fails."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        @tracing.traced()
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        # Verify exception was recorded
        mock_span.record_exception.assert_called_once()
        mock_span.set_status.assert_called()


class TestSpanAttributes:
    """Tests for SpanAttributes constants."""

    def test_investigation_attributes_defined(self):
        """Test that investigation attribute constants are defined."""
        assert hasattr(SpanAttributes, "INVESTIGATION_ID")
        assert hasattr(SpanAttributes, "INVESTIGATION_PRIORITY")
        assert hasattr(SpanAttributes, "INVESTIGATION_INCIDENT_TYPE")
        assert hasattr(SpanAttributes, "INVESTIGATION_PHASE")

    def test_agent_attributes_defined(self):
        """Test that agent attribute constants are defined."""
        assert hasattr(SpanAttributes, "AGENT_TYPE")
        assert hasattr(SpanAttributes, "AGENT_ROLE")
        assert hasattr(SpanAttributes, "AGENT_SPAN_OF_CONTROL")

    def test_hypothesis_attributes_defined(self):
        """Test that hypothesis attribute constants are defined."""
        assert hasattr(SpanAttributes, "HYPOTHESIS_ID")
        assert hasattr(SpanAttributes, "HYPOTHESIS_CONFIDENCE")
        assert hasattr(SpanAttributes, "HYPOTHESIS_DISPROOF_ATTEMPTS")

    def test_llm_attributes_defined(self):
        """Test that LLM attribute constants are defined."""
        assert hasattr(SpanAttributes, "LLM_PROVIDER")
        assert hasattr(SpanAttributes, "LLM_MODEL")
        assert hasattr(SpanAttributes, "LLM_INPUT_TOKENS")
        assert hasattr(SpanAttributes, "LLM_OUTPUT_TOKENS")
        assert hasattr(SpanAttributes, "LLM_CACHED_TOKENS")
        assert hasattr(SpanAttributes, "LLM_COST_USD")

    def test_human_decision_attributes_defined(self):
        """Test that human decision attribute constants are defined."""
        assert hasattr(SpanAttributes, "HUMAN_DECISION_TYPE")
        assert hasattr(SpanAttributes, "HUMAN_CONFIDENCE")
        assert hasattr(SpanAttributes, "HUMAN_AGREED_WITH_AI")
        assert hasattr(SpanAttributes, "HUMAN_DECISION_TIME_MS")
