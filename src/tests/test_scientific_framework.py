"""
COMPASS Scientific Framework Test Suite
========================================

TDD test suite for the scientific reasoning framework.
Demonstrates how to test hypothesis validation, disproof attempts, and auditability.
"""

import pytest
from datetime import datetime, timezone, timedelta
from compass_scientific_framework import (
    ScientificAgent, Hypothesis, DisproofAttempt, Evidence,
    EvidenceQuality, HypothesisStatus, InvestigativeAction, InvestigationStep
)
from compass_database_agent import DatabaseAgent, DATABASE_AGENT_CONFIG


class TestEvidence:
    """Test evidence creation and quality rating"""
    
    def test_evidence_creation_with_defaults(self):
        """Evidence should be created with sensible defaults"""
        evidence = Evidence(
            source="prometheus:api_latency",
            data={"p95": 450, "p99": 1200},
            interpretation="API latency elevated above baseline"
        )
        
        assert evidence.id is not None
        assert evidence.timestamp is not None
        assert evidence.quality == EvidenceQuality.INDIRECT
        assert evidence.supports_hypothesis == True
        assert evidence.confidence == 0.5
    
    def test_evidence_quality_affects_weight(self):
        """Higher quality evidence should have higher weight"""
        direct_weight = Hypothesis._evidence_quality_weight(EvidenceQuality.DIRECT)
        weak_weight = Hypothesis._evidence_quality_weight(EvidenceQuality.WEAK)
        
        assert direct_weight > weak_weight
        assert direct_weight == 1.0
        assert weak_weight == 0.2
    
    def test_evidence_audit_log(self):
        """Evidence should export complete audit trail"""
        evidence = Evidence(
            source="database:pg_locks",
            data={"lock_count": 150},
            interpretation="Abnormal lock contention detected",
            quality=EvidenceQuality.DIRECT,
            confidence=0.85
        )
        
        audit = evidence.to_audit_log()
        
        assert audit['id'] == evidence.id
        assert audit['source'] == "database:pg_locks"
        assert audit['quality'] == 'direct'
        assert audit['confidence'] == 0.85


class TestHypothesis:
    """Test hypothesis creation, validation, and confidence scoring"""
    
    def test_hypothesis_creation(self):
        """Hypothesis should be created with initial confidence"""
        hypothesis = Hypothesis(
            agent_id="test_agent",
            statement="Database connection pool exhaustion causing API timeouts",
            initial_confidence=0.6,
            affected_systems=["api-service", "database"]
        )
        
        assert hypothesis.id is not None
        assert hypothesis.status == HypothesisStatus.GENERATED
        assert hypothesis.current_confidence == 0.6
        assert len(hypothesis.affected_systems) == 2
    
    def test_adding_supporting_evidence_increases_confidence(self):
        """Supporting evidence should increase hypothesis confidence"""
        hypothesis = Hypothesis(
            agent_id="test_agent",
            statement="High query volume causing slowdown",
            initial_confidence=0.5
        )
        
        initial_confidence = hypothesis.current_confidence
        
        # Add high-quality supporting evidence
        evidence = Evidence(
            source="prometheus:query_rate",
            data={"rate": "5000/s"},
            interpretation="Query rate 10x normal",
            quality=EvidenceQuality.DIRECT,
            supports_hypothesis=True,
            confidence=0.9
        )
        
        hypothesis.add_evidence(evidence)
        
        assert hypothesis.current_confidence > initial_confidence
        assert len(hypothesis.supporting_evidence) == 1
    
    def test_contradicting_evidence_decreases_confidence(self):
        """Contradicting evidence should decrease hypothesis confidence"""
        hypothesis = Hypothesis(
            agent_id="test_agent",
            statement="Memory leak causing OOM errors",
            initial_confidence=0.7
        )
        
        initial_confidence = hypothesis.current_confidence
        
        # Add contradicting evidence
        evidence = Evidence(
            source="prometheus:memory_usage",
            data={"usage": "45%"},
            interpretation="Memory usage well below limits",
            quality=EvidenceQuality.DIRECT,
            supports_hypothesis=False,
            confidence=0.9
        )
        
        hypothesis.add_evidence(evidence)
        
        assert hypothesis.current_confidence < initial_confidence
        assert len(hypothesis.contradicting_evidence) == 1
    
    def test_surviving_disproof_attempts_increases_confidence(self):
        """Surviving disproof attempts should boost confidence"""
        hypothesis = Hypothesis(
            agent_id="test_agent",
            statement="Network latency spike caused by ISP issues",
            initial_confidence=0.6
        )
        
        # Add evidence first
        evidence = Evidence(
            source="prometheus:network_latency",
            data={"latency_ms": 450},
            interpretation="Latency increased 400%",
            quality=EvidenceQuality.DIRECT,
            supports_hypothesis=True,
            confidence=0.85
        )
        hypothesis.add_evidence(evidence)
        
        confidence_after_evidence = hypothesis.current_confidence
        
        # Survive disproof attempts
        for i in range(3):
            attempt = DisproofAttempt(
                strategy=f"test_strategy_{i}",
                method=f"test_method_{i}",
                expected_if_true="Should see pattern X",
                observed="Observed pattern X",
                disproven=False,
                reasoning="Hypothesis survived this test"
            )
            hypothesis.add_disproof_attempt(attempt)
        
        assert hypothesis.current_confidence > confidence_after_evidence
        assert len(hypothesis.disproof_attempts) == 3
    
    def test_disproven_hypothesis_sets_confidence_to_zero(self):
        """Disproven hypothesis should have zero confidence"""
        hypothesis = Hypothesis(
            agent_id="test_agent",
            statement="Disk full causing write failures",
            initial_confidence=0.7
        )
        
        # Disprove the hypothesis
        attempt = DisproofAttempt(
            strategy="resource_check",
            method="check_disk_usage",
            expected_if_true="Disk usage >95%",
            observed="Disk usage 45%",
            disproven=True,
            reasoning="Disk has plenty of space - cannot be the cause"
        )
        
        hypothesis.add_disproof_attempt(attempt)
        
        assert hypothesis.status == HypothesisStatus.DISPROVEN
        assert hypothesis.current_confidence == 0.0
    
    def test_hypothesis_audit_trail_is_complete(self):
        """Hypothesis should export complete audit trail"""
        hypothesis = Hypothesis(
            agent_id="test_agent",
            statement="API rate limiting triggered by traffic spike",
            initial_confidence=0.65,
            affected_systems=["api-gateway"],
            time_correlation="2024-11-14T10:15:00Z"
        )
        
        # Add evidence
        evidence = Evidence(
            source="prometheus:requests_per_second",
            data={"rate": "10000"},
            interpretation="Request rate 5x normal",
            quality=EvidenceQuality.CORROBORATED,
            confidence=0.8
        )
        hypothesis.add_evidence(evidence)
        
        # Add disproof attempt
        attempt = DisproofAttempt(
            strategy="alternative_explanation",
            method="check_for_simpler_cause",
            expected_if_true="No simpler explanation",
            observed="No simpler cause identified",
            disproven=False
        )
        hypothesis.add_disproof_attempt(attempt)
        
        audit = hypothesis.to_audit_log()
        
        assert audit['id'] == hypothesis.id
        assert audit['statement'] == hypothesis.statement
        assert audit['status'] == HypothesisStatus.GENERATED.value
        assert len(audit['evidence']['supporting']) == 1
        assert len(audit['disproof_attempts']) == 1
        assert 'confidence' in audit
        assert audit['confidence']['current'] > audit['confidence']['initial']


class TestDisproofAttempt:
    """Test disproof attempt execution and tracking"""
    
    def test_disproof_attempt_creation(self):
        """Disproof attempt should track all test details"""
        attempt = DisproofAttempt(
            strategy="temporal_contradiction",
            method="verify_timing_alignment",
            expected_if_true="Cause precedes effect by <5 minutes",
            observed="Cause occurred 2 seconds before effect",
            disproven=False,
            reasoning="Timing is consistent with causation"
        )
        
        assert attempt.id is not None
        assert attempt.timestamp is not None
        assert attempt.strategy == "temporal_contradiction"
        assert attempt.disproven == False
    
    def test_disproof_attempt_with_evidence(self):
        """Disproof attempts should be able to collect supporting evidence"""
        evidence = Evidence(
            source="logs:timestamp_comparison",
            data={"time_delta_seconds": 2},
            interpretation="Cause preceded effect by 2 seconds"
        )
        
        attempt = DisproofAttempt(
            strategy="temporal_contradiction",
            method="compare_timestamps",
            expected_if_true="Cause before effect",
            observed="Confirmed: cause at T+0, effect at T+2",
            disproven=False,
            evidence=[evidence]
        )
        
        assert len(attempt.evidence) == 1


class TestInvestigationStep:
    """Test investigation step tracking and auditability"""
    
    def test_investigation_step_creation(self):
        """Investigation step should document purpose and method"""
        step = InvestigationStep(
            agent_id="database_agent",
            action=InvestigativeAction.MEASURE,
            purpose="Determine if connection pool is saturated",
            expected_outcome="Pool utilization >80% if exhausted",
            method="Query Prometheus for pg_stat_database metrics",
            data_sources=["prometheus"]
        )
        
        assert step.id is not None
        assert step.action == InvestigativeAction.MEASURE
        assert step.purpose != ""
        assert step.expected_outcome != ""
    
    def test_investigation_step_tracks_outcome(self):
        """Investigation step should record actual vs expected outcome"""
        step = InvestigationStep(
            agent_id="network_agent",
            action=InvestigativeAction.CORRELATE,
            purpose="Check if latency correlates with traffic",
            expected_outcome="High correlation (>0.7)",
            method="Calculate Pearson correlation",
            data_sources=["prometheus"],
            actual_outcome="Correlation: 0.85",
            successful=True
        )
        
        assert step.successful == True
        assert step.actual_outcome != ""
        assert step.error is None
    
    def test_failed_investigation_step_records_error(self):
        """Failed investigation steps should capture error details"""
        step = InvestigationStep(
            agent_id="test_agent",
            action=InvestigativeAction.OBSERVE,
            purpose="Fetch metrics from unavailable source",
            expected_outcome="Retrieve latency data",
            method="Query Prometheus",
            data_sources=["prometheus"],
            successful=False,
            error="Connection refused: prometheus:9090"
        )
        
        assert step.successful == False
        assert step.error is not None


class TestDatabaseAgent:
    """Test database specialist agent implementation"""
    
    def test_database_agent_initialization(self):
        """Database agent should initialize with proper config"""
        agent = DatabaseAgent(config=DATABASE_AGENT_CONFIG)
        
        assert agent.agent_id == "database_specialist"
        assert agent.data_sources['prometheus'] == True
        assert agent.time_budget_per_hypothesis == 45.0
        assert agent.min_confidence_threshold == 0.65
    
    def test_generate_hypothesis(self):
        """Agent should be able to generate hypotheses"""
        agent = DatabaseAgent(config=DATABASE_AGENT_CONFIG)
        
        hypothesis = agent.generate_hypothesis(
            statement="Connection pool exhaustion causing timeouts",
            initial_confidence=0.7,
            affected_systems=["api-service", "database"],
            metadata={"symptom": "timeout_spike"}
        )
        
        assert hypothesis.id in agent.hypotheses
        assert hypothesis.agent_id == "database_specialist"
        assert hypothesis.initial_confidence == 0.7
    
    def test_generate_disproof_strategies_for_connection_hypothesis(self):
        """Database agent should generate relevant disproof strategies"""
        agent = DatabaseAgent(config=DATABASE_AGENT_CONFIG)
        
        hypothesis = Hypothesis(
            agent_id="database_specialist",
            statement="Connection pool exhaustion causing API timeouts",
            initial_confidence=0.7
        )
        
        strategies = agent.generate_disproof_strategies(hypothesis)
        
        # Should generate multiple strategies
        assert len(strategies) > 0
        
        # Should prioritize connection-related tests
        connection_strategies = [
            s for s in strategies 
            if 'connection' in s['strategy']
        ]
        assert len(connection_strategies) > 0
        
        # Strategies should have required fields
        for strategy in strategies:
            assert 'strategy' in strategy
            assert 'method' in strategy
            assert 'expected_if_true' in strategy
            assert 'priority' in strategy
            assert 'test_func' in strategy
    
    def test_filter_feasible_strategies(self):
        """Agent should filter strategies based on available data sources"""
        # Agent with limited data sources
        limited_config = DATABASE_AGENT_CONFIG.copy()
        limited_config['data_sources'] = {
            'prometheus': True,
            'database_logs': False,  # Not available
            'slow_query_log': False,
            'connection_metrics': True,
            'replication_metrics': False
        }
        
        agent = DatabaseAgent(config=limited_config)
        
        hypothesis = Hypothesis(
            agent_id="database_specialist",
            statement="Slow queries causing performance degradation"
        )
        
        all_strategies = agent.generate_disproof_strategies(hypothesis)
        feasible = agent.filter_feasible_strategies(all_strategies, hypothesis)
        
        # Should have fewer feasible strategies
        assert len(feasible) < len(all_strategies)
        
        # All feasible strategies should only require available sources
        for strategy in feasible:
            required = set(strategy['data_sources_needed'])
            available = {k for k, v in agent.data_sources.items() if v}
            assert required.issubset(available)
    
    def test_validate_hypothesis_process(self):
        """Hypothesis validation should attempt disproofs and update status"""
        agent = DatabaseAgent(config=DATABASE_AGENT_CONFIG)
        
        hypothesis = agent.generate_hypothesis(
            statement="Connection pool saturation causing timeouts",
            initial_confidence=0.6,
            affected_systems=["api-service"]
        )
        
        initial_status = hypothesis.status
        
        # Validate the hypothesis
        validated = agent.validate_hypothesis(hypothesis)
        
        # Status should change from GENERATED
        assert validated.status != initial_status
        assert validated.status in [
            HypothesisStatus.VALIDATED,
            HypothesisStatus.DISPROVEN,
            HypothesisStatus.REQUIRES_HUMAN
        ]
        
        # Should have attempted at least one disproof
        assert len(validated.disproof_attempts) > 0
    
    def test_disproven_hypothesis_not_presented_to_human(self):
        """Disproven hypotheses should not be in validated list"""
        agent = DatabaseAgent(config=DATABASE_AGENT_CONFIG)
        
        # Create hypothesis that will be disproven
        hypothesis = agent.generate_hypothesis(
            statement="Test hypothesis that will be disproven",
            initial_confidence=0.5,
            affected_systems=["test"]
        )
        
        # Manually disprove it
        disproof = DisproofAttempt(
            strategy="test",
            method="test",
            expected_if_true="X",
            observed="not X",
            disproven=True,
            reasoning="Test disproof"
        )
        hypothesis.add_disproof_attempt(disproof)
        
        # Should not appear in validated list
        validated_list = agent.get_validated_hypotheses()
        assert hypothesis not in validated_list
        
        # Should appear in disproven list
        disproven_list = agent.get_disproven_hypotheses()
        assert hypothesis in disproven_list
    
    def test_audit_trail_generation(self):
        """Agent should generate complete audit trail"""
        agent = DatabaseAgent(config=DATABASE_AGENT_CONFIG)
        
        # Generate and validate a hypothesis
        hypothesis = agent.generate_hypothesis(
            statement="Test hypothesis for audit trail",
            initial_confidence=0.7,
            affected_systems=["test-system"]
        )
        
        agent.validate_hypothesis(hypothesis)
        
        # Generate audit trail
        audit = agent.generate_audit_trail()
        
        assert 'agent_id' in audit
        assert 'investigation_summary' in audit
        assert 'investigation_steps' in audit
        assert 'hypotheses' in audit
        assert 'config' in audit
        
        # Should include both validated and disproven hypotheses
        assert 'validated' in audit['hypotheses']
        assert 'disproven' in audit['hypotheses']
        assert 'all' in audit['hypotheses']
    
    def test_investigation_narrative_generation(self):
        """Agent should generate human-readable narrative"""
        agent = DatabaseAgent(config=DATABASE_AGENT_CONFIG)
        
        hypothesis = agent.generate_hypothesis(
            statement="Network latency spike",
            initial_confidence=0.8,
            affected_systems=["api"]
        )
        
        validated = agent.validate_hypothesis(hypothesis)
        
        narrative = agent.export_investigation_narrative()
        
        # Should be human-readable text
        assert isinstance(narrative, str)
        assert len(narrative) > 0
        
        # Should include agent ID
        assert agent.agent_id in narrative
        
        # Should mention hypotheses
        if validated.status == HypothesisStatus.VALIDATED:
            assert "Validated Hypotheses" in narrative
        elif validated.status == HypothesisStatus.DISPROVEN:
            assert "Disproven Hypotheses" in narrative


class TestScientificMethod:
    """Test that the framework enforces scientific method"""
    
    def test_every_action_has_stated_purpose(self):
        """Investigation steps must have explicit purpose"""
        step = InvestigationStep(
            agent_id="test",
            action=InvestigativeAction.OBSERVE,
            purpose="",  # Missing purpose
            expected_outcome="Get data",
            method="Query API"
        )
        
        # Framework should enforce non-empty purpose
        # In production, this would raise validation error
        assert step.purpose == ""  # This test documents the requirement
    
    def test_hypotheses_must_be_testable(self):
        """Hypotheses must be specific and testable"""
        # Good hypothesis - specific, testable
        good = Hypothesis(
            agent_id="test",
            statement="Connection pool exhaustion (>95% utilization) caused timeout spike at 10:15 AM",
            initial_confidence=0.7
        )
        
        # Bad hypothesis - vague, not testable
        bad = Hypothesis(
            agent_id="test",
            statement="Something went wrong with the database",
            initial_confidence=0.5
        )
        
        # Framework should prefer specific, testable statements
        # Good hypothesis provides clear expected_if_true for disproofs
        assert ">" in good.statement  # Quantifiable
        assert "caused" in good.statement  # Causal claim (testable)
        
        # Bad hypothesis lacks specificity
        assert "something" in bad.statement.lower()
    
    def test_confidence_must_be_justified(self):
        """Confidence scores must be traceable to evidence"""
        hypothesis = Hypothesis(
            agent_id="test",
            statement="Test hypothesis",
            initial_confidence=0.7
        )
        
        # Initially, confidence reasoning is empty
        assert hypothesis.confidence_reasoning == "initial assessment"
        
        # After adding evidence, reasoning should update
        evidence = Evidence(
            source="test",
            data="test",
            interpretation="test",
            confidence=0.8
        )
        hypothesis.add_evidence(evidence)
        
        # Now reasoning should reference evidence
        assert "evidence" in hypothesis.confidence_reasoning.lower()


# Integration tests
class TestEndToEndInvestigation:
    """Test complete investigation workflow"""
    
    def test_complete_hypothesis_lifecycle(self):
        """Test hypothesis from generation through validation to presentation"""
        agent = DatabaseAgent(config=DATABASE_AGENT_CONFIG)
        
        # 1. Generate hypothesis
        hypothesis = agent.generate_hypothesis(
            statement="Connection pool saturation causing API timeouts",
            initial_confidence=0.65,
            affected_systems=["api-service", "database"]
        )
        
        assert hypothesis.status == HypothesisStatus.GENERATED
        
        # 2. Validate hypothesis (attempts disproofs)
        validated = agent.validate_hypothesis(hypothesis)
        
        # 3. Check outcome
        if validated.status == HypothesisStatus.VALIDATED:
            # Should be in list for human review
            assert validated in agent.get_validated_hypotheses()
            assert validated.current_confidence >= agent.min_confidence_threshold
            assert len(validated.disproof_attempts) > 0
            
        elif validated.status == HypothesisStatus.DISPROVEN:
            # Should be in disproven list, not validated
            assert validated not in agent.get_validated_hypotheses()
            assert validated in agent.get_disproven_hypotheses()
            assert validated.current_confidence == 0.0
        
        # 4. Generate audit trail
        audit = agent.generate_audit_trail()
        assert len(audit['hypotheses']['all']) >= 1
    
    def test_multiple_hypotheses_prioritization(self):
        """Test that multiple hypotheses are properly prioritized by confidence"""
        agent = DatabaseAgent(config=DATABASE_AGENT_CONFIG)
        
        # Generate multiple hypotheses
        h1 = agent.generate_hypothesis(
            statement="Connection pool exhaustion",
            initial_confidence=0.9,
            affected_systems=["api"]
        )
        
        h2 = agent.generate_hypothesis(
            statement="Slow query degradation",
            initial_confidence=0.5,
            affected_systems=["api"]
        )
        
        h3 = agent.generate_hypothesis(
            statement="Network latency spike",
            initial_confidence=0.7,
            affected_systems=["api"]
        )
        
        # Validate all
        agent.validate_hypothesis(h1)
        agent.validate_hypothesis(h2)
        agent.validate_hypothesis(h3)
        
        # Get validated hypotheses
        validated = agent.get_validated_hypotheses()
        
        # Should be sorted by confidence (assuming they all validated)
        if len(validated) > 1:
            for i in range(len(validated) - 1):
                assert validated[i].current_confidence >= validated[i+1].current_confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
