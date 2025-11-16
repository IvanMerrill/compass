"""
COMPASS Specialist Agent Template
==================================

Template for creating new specialist agents that extend the scientific framework.

Copy this template to create new agents:
1. Inherit from ScientificAgent
2. Implement the three required abstract methods
3. Define domain-specific disproof strategies
4. Configure data sources and thresholds
5. Write comprehensive tests

This ensures all agents follow the same rigorous scientific methodology
while supporting domain-specific expertise.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from compass_scientific_framework import (
    ScientificAgent, Hypothesis, DisproofAttempt, Evidence,
    EvidenceQuality, InvestigativeAction
)


class TemplateSpecialistAgent(ScientificAgent):
    """
    Template for creating new specialist agents.
    
    Replace "Template" with your domain (e.g., Network, Application, Infrastructure).
    
    Focus areas should be listed here:
    - Key area 1 (e.g., Routing issues)
    - Key area 2 (e.g., DNS resolution)
    - Key area 3 (e.g., Load balancing)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Set agent_id to something descriptive
        super().__init__(agent_id="template_specialist", config=config)
        
        # Define which data sources this agent can use
        self.data_sources = self.config.get('data_sources', {
            'prometheus': True,
            'logs': True,
            'traces': True,
            # Add domain-specific sources
            'domain_specific_source': True
        })
        
        # Domain-specific thresholds for disproof tests
        self.thresholds = self.config.get('thresholds', {
            'example_threshold': 0.80,
            'another_threshold': 100,
        })
    
    def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
        """
        Generate domain-specific strategies to disprove a hypothesis.
        
        Think about:
        1. What would prove this hypothesis WRONG?
        2. What data can I check to disprove it?
        3. What are common false positives in my domain?
        
        Return strategies ordered by priority (highest first).
        """
        strategies = []
        
        # Extract key terms from hypothesis
        statement_lower = hypothesis.statement.lower()
        
        # ============================================================
        # Strategy Pattern 1: Temporal Contradiction
        # ============================================================
        # Check if timing makes sense for causation claim
        if any(term in statement_lower for term in ['caused', 'triggered', 'led to']):
            strategies.append({
                'strategy': 'temporal_contradiction',
                'method': 'verify_timing_alignment',
                'expected_if_true': 'Suspected cause should precede symptoms',
                'data_sources_needed': ['logs', 'prometheus'],
                'priority': 0.95,  # High priority - quick and definitive
                'test_func': self._test_temporal_alignment
            })
        
        # ============================================================
        # Strategy Pattern 2: Metric Contradiction
        # ============================================================
        # Check if metrics support the hypothesis
        # Example: "High CPU" hypothesis should show high CPU metrics
        if 'high' in statement_lower or 'increased' in statement_lower:
            strategies.append({
                'strategy': 'metric_contradiction',
                'method': 'verify_metric_actually_high',
                'expected_if_true': 'Relevant metrics should exceed thresholds',
                'data_sources_needed': ['prometheus'],
                'priority': 0.90,
                'test_func': self._test_metric_levels
            })
        
        # ============================================================
        # Strategy Pattern 3: Scope Mismatch
        # ============================================================
        # Does hypothesis explain ALL affected systems?
        # If only explains 20%, probably not root cause
        strategies.append({
            'strategy': 'scope_verification',
            'method': 'verify_hypothesis_explains_all_symptoms',
            'expected_if_true': 'Hypothesis should explain >80% of affected systems',
            'data_sources_needed': ['prometheus'],
            'priority': 0.75,
            'test_func': self._test_scope_coverage
        })
        
        # ============================================================
        # Strategy Pattern 4: Correlation Check
        # ============================================================
        # Does suspected cause correlate with symptoms?
        strategies.append({
            'strategy': 'correlation_analysis',
            'method': 'calculate_correlation_between_cause_and_effect',
            'expected_if_true': 'Correlation should be >0.7 for strong causation',
            'data_sources_needed': ['prometheus'],
            'priority': 0.80,
            'test_func': self._test_correlation
        })
        
        # ============================================================
        # Strategy Pattern 5: Alternative Explanation
        # ============================================================
        # Is there a simpler explanation?
        # Occam's Razor: prefer simpler hypotheses
        strategies.append({
            'strategy': 'alternative_explanation',
            'method': 'search_for_simpler_causes',
            'expected_if_true': 'No simpler explanation with equal/better evidence',
            'data_sources_needed': ['prometheus', 'logs'],
            'priority': 0.65,
            'test_func': self._test_alternative_explanations
        })
        
        # ============================================================
        # Add domain-specific strategies below
        # ============================================================
        
        # Example: Network-specific strategy
        # if 'network' in statement_lower or 'latency' in statement_lower:
        #     strategies.append({
        #         'strategy': 'packet_loss_verification',
        #         'method': 'check_packet_loss_metrics',
        #         'expected_if_true': 'Packet loss should be >1% if network is cause',
        #         'data_sources_needed': ['prometheus', 'network_metrics'],
        #         'priority': 0.90,
        #         'test_func': self._test_packet_loss
        #     })
        
        # Sort by priority (highest first)
        strategies.sort(key=lambda x: x['priority'], reverse=True)
        
        return strategies
    
    def filter_feasible_strategies(
        self, 
        strategies: List[Dict[str, Any]], 
        hypothesis: Hypothesis
    ) -> List[Dict[str, Any]]:
        """
        Filter to strategies where we have the required data sources.
        
        This prevents attempting tests that will fail due to missing data.
        """
        feasible = []
        
        for strategy in strategies:
            required_sources = set(strategy['data_sources_needed'])
            available_sources = {k for k, v in self.data_sources.items() if v}
            
            if required_sources.issubset(available_sources):
                feasible.append(strategy)
            else:
                # Log why we can't execute
                missing = required_sources - available_sources
                self._log_infeasible_strategy(strategy, missing, hypothesis.id)
        
        return feasible
    
    def attempt_disproof(
        self, 
        hypothesis: Hypothesis, 
        strategy: Dict[str, Any]
    ) -> DisproofAttempt:
        """
        Execute a single disproof attempt.
        
        Calls the test function defined in the strategy.
        Handles errors and tracks cost.
        """
        attempt = DisproofAttempt(
            strategy=strategy['strategy'],
            method=strategy['method'],
            expected_if_true=strategy['expected_if_true']
        )
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Execute the test function
            test_func = strategy['test_func']
            result = test_func(hypothesis, attempt)
            
            attempt.observed = result['observed']
            attempt.disproven = result['disproven']
            attempt.reasoning = result['reasoning']
            attempt.evidence = result.get('evidence', [])
            
        except Exception as e:
            # If test fails, don't disprove the hypothesis
            # Log error for debugging
            attempt.observed = f"Test failed with error: {str(e)}"
            attempt.disproven = False
            attempt.reasoning = "Unable to complete test due to error"
        
        # Track cost
        end_time = datetime.now(timezone.utc)
        attempt.cost = {
            'time_ms': (end_time - start_time).total_seconds() * 1000,
            'tokens': 0  # Update if LLM was used
        }
        
        return attempt
    
    # ============================================================
    # Test Implementation Functions
    # ============================================================
    # Implement these to perform actual data fetching and analysis
    
    def _test_temporal_alignment(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """
        Test if timing aligns with causation claim.
        
        Returns:
            {
                'observed': str - what was actually observed,
                'disproven': bool - true if hypothesis is disproven,
                'reasoning': str - explanation of why,
                'evidence': List[Evidence] - supporting evidence
            }
        """
        
        def execute_check():
            # TODO: Replace with actual data fetching
            # Example: Query logs for timestamps
            # timestamps = query_logs(hypothesis.affected_systems)
            # return timestamps
            return {
                'cause_time': '2024-11-14T10:15:00Z',
                'effect_time': '2024-11-14T10:15:05Z'
            }
        
        step = self.execute_investigation_step(
            action=InvestigativeAction.CORRELATE,
            purpose=f"Verify temporal alignment for: {hypothesis.statement}",
            expected_outcome="Cause should precede symptoms",
            method="Compare timestamps from logs",
            data_sources=['logs'],
            execution_func=execute_check,
            hypothesis_context=hypothesis.id
        )
        
        if step.successful:
            # TODO: Implement actual timing analysis
            # Parse timestamps, calculate delta
            # If cause AFTER effect: disproven = True
            
            time_delta_seconds = 5  # Placeholder
            
            if time_delta_seconds < 0:
                return {
                    'observed': f'Cause occurred {abs(time_delta_seconds)}s AFTER symptoms',
                    'disproven': True,
                    'reasoning': 'Temporal contradiction: effect cannot precede cause'
                }
            elif time_delta_seconds > 300:
                return {
                    'observed': f'Cause occurred {time_delta_seconds}s before symptoms',
                    'disproven': True,
                    'reasoning': 'Time gap too large for direct causation (>5 minutes)'
                }
            else:
                return {
                    'observed': f'Cause preceded symptoms by {time_delta_seconds}s',
                    'disproven': False,
                    'reasoning': 'Timing consistent with causation'
                }
        
        return {
            'observed': 'Unable to verify timing',
            'disproven': False,
            'reasoning': 'Insufficient data to test temporal alignment'
        }
    
    def _test_metric_levels(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Test if metrics actually show the claimed pattern"""
        
        def execute_check():
            # TODO: Query Prometheus/metrics system
            # Example: query_prometheus('rate(requests[5m])')
            return {'metric_value': 75, 'threshold': 80}
        
        step = self.execute_investigation_step(
            action=InvestigativeAction.MEASURE,
            purpose="Measure actual metric values during incident",
            expected_outcome="Metrics should exceed thresholds if hypothesis is correct",
            method="Query monitoring system",
            data_sources=['prometheus'],
            execution_func=execute_check,
            hypothesis_context=hypothesis.id
        )
        
        if step.successful:
            # TODO: Implement actual metric comparison
            metric_value = 75  # Placeholder
            threshold = 80
            
            if metric_value < threshold * 0.7:  # Well below threshold
                evidence = Evidence(
                    source="prometheus:example_metric",
                    data=f"Value: {metric_value}",
                    interpretation=f"Metric well below threshold ({metric_value} vs {threshold})",
                    quality=EvidenceQuality.DIRECT,
                    supports_hypothesis=False,
                    confidence=0.9
                )
                
                self.evidence_store[evidence.id] = evidence
                
                return {
                    'observed': f'Metric value {metric_value} well below threshold {threshold}',
                    'disproven': True,
                    'reasoning': 'Metrics do not support hypothesis',
                    'evidence': [evidence]
                }
            else:
                return {
                    'observed': f'Metric value {metric_value} near/above threshold {threshold}',
                    'disproven': False,
                    'reasoning': 'Metrics consistent with hypothesis'
                }
        
        return {
            'observed': 'Unable to retrieve metrics',
            'disproven': False,
            'reasoning': 'Test inconclusive'
        }
    
    def _test_scope_coverage(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Test if hypothesis explains all affected systems"""
        
        def execute_check():
            # TODO: Check which systems show symptoms
            return {
                'total_affected': 10,
                'explained_by_hypothesis': 9
            }
        
        step = self.execute_investigation_step(
            action=InvestigativeAction.ISOLATE,
            purpose="Determine scope of hypothesis coverage",
            expected_outcome="Hypothesis should explain >80% of symptoms",
            method="Check symptom presence across systems",
            data_sources=['prometheus'],
            execution_func=execute_check,
            hypothesis_context=hypothesis.id
        )
        
        if step.successful:
            total = 10
            explained = 9
            coverage = explained / total if total > 0 else 0
            
            if coverage < 0.5:  # Explains less than half
                return {
                    'observed': f'Hypothesis explains only {coverage:.0%} of affected systems',
                    'disproven': True,
                    'reasoning': 'Scope too limited to be root cause'
                }
            else:
                return {
                    'observed': f'Hypothesis explains {coverage:.0%} of affected systems',
                    'disproven': False,
                    'reasoning': f'Good scope coverage ({coverage:.0%})'
                }
        
        return {
            'observed': 'Unable to determine scope',
            'disproven': False,
            'reasoning': 'Test inconclusive'
        }
    
    def _test_correlation(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Test correlation between suspected cause and observed symptoms"""
        
        def execute_check():
            # TODO: Calculate actual correlation
            # Example: pearson_correlation(cause_metric, symptom_metric)
            return {'correlation': 0.35}
        
        step = self.execute_investigation_step(
            action=InvestigativeAction.CORRELATE,
            purpose="Calculate correlation between cause and symptoms",
            expected_outcome="Strong correlation (>0.7) if causation exists",
            method="Pearson correlation of time series",
            data_sources=['prometheus'],
            execution_func=execute_check,
            hypothesis_context=hypothesis.id
        )
        
        if step.successful:
            correlation = 0.35  # Placeholder
            
            if correlation < 0.5:
                return {
                    'observed': f'Weak correlation ({correlation:.2f}) between cause and symptoms',
                    'disproven': True,
                    'reasoning': 'Insufficient correlation for causal relationship'
                }
            else:
                return {
                    'observed': f'Correlation: {correlation:.2f}',
                    'disproven': False,
                    'reasoning': 'Correlation supports causation'
                }
        
        return {
            'observed': 'Unable to calculate correlation',
            'disproven': False,
            'reasoning': 'Test inconclusive'
        }
    
    def _test_alternative_explanations(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Search for simpler alternative explanations"""
        
        def execute_check():
            # TODO: Use heuristics or LLM to find alternatives
            # Check common causes in this domain
            return {'alternatives_found': []}
        
        step = self.execute_investigation_step(
            action=InvestigativeAction.ELIMINATE,
            purpose="Search for simpler alternative explanations",
            expected_outcome="No simpler explanation with equal evidence",
            method="Check common causes and patterns",
            data_sources=['prometheus', 'logs'],
            execution_func=execute_check,
            hypothesis_context=hypothesis.id
        )
        
        if step.successful:
            alternatives = []  # Placeholder
            
            if alternatives:
                return {
                    'observed': f'Found {len(alternatives)} simpler alternatives',
                    'disproven': True,
                    'reasoning': 'Simpler explanation available (Occam\'s Razor)'
                }
            else:
                return {
                    'observed': 'No simpler alternative found',
                    'disproven': False,
                    'reasoning': 'Current hypothesis is most parsimonious'
                }
        
        return {
            'observed': 'Unable to search alternatives',
            'disproven': False,
            'reasoning': 'Test inconclusive'
        }
    
    # ============================================================
    # Helper Methods
    # ============================================================
    
    def _log_infeasible_strategy(
        self, 
        strategy: Dict[str, Any], 
        missing_sources: set,
        hypothesis_id: str
    ):
        """Log when a strategy can't be executed"""
        # In production, send to logging system
        print(f"[{self.agent_id}] Cannot execute {strategy['strategy']} "
              f"for hypothesis {hypothesis_id} - "
              f"missing data sources: {missing_sources}")


# ============================================================
# Configuration Schema for New Agent
# ============================================================

TEMPLATE_AGENT_CONFIG = {
    # Base scientific framework settings (inherited)
    'time_budget_per_hypothesis': 60.0,
    'cost_budget_per_hypothesis': 10000,
    'max_disproof_attempts': 5,
    'min_confidence_threshold': 0.6,
    
    # Domain-specific data sources
    'data_sources': {
        'prometheus': True,
        'logs': True,
        'traces': True,
        # Add domain-specific sources here
        'domain_specific_source': True,
    },
    
    # Domain-specific thresholds for disproof tests
    'thresholds': {
        'example_metric_threshold': 0.80,
        'another_threshold': 100,
        # Add domain-specific thresholds here
    },
    
    # Domain-specific settings
    'domain_settings': {
        'example_setting': 'value',
        # Add domain-specific configuration here
    }
}


# ============================================================
# Usage Example
# ============================================================

if __name__ == "__main__":
    """
    Example of how to use the template to create a new agent.
    
    Steps:
    1. Copy this file to compass_<domain>_agent.py
    2. Rename TemplateSpecialistAgent to <Domain>Agent
    3. Implement domain-specific disproof strategies
    4. Implement test functions to query your data sources
    5. Configure data sources and thresholds
    6. Write comprehensive tests
    """
    
    # Create agent instance
    agent = TemplateSpecialistAgent(config=TEMPLATE_AGENT_CONFIG)
    
    # Generate a hypothesis
    hypothesis = agent.generate_hypothesis(
        statement="Example hypothesis for testing",
        initial_confidence=0.7,
        affected_systems=["system-a", "system-b"]
    )
    
    print(f"Generated hypothesis: {hypothesis.id}")
    print(f"Statement: {hypothesis.statement}")
    print(f"Initial confidence: {hypothesis.initial_confidence}")
    
    # Validate the hypothesis (attempts to disprove)
    validated = agent.validate_hypothesis(hypothesis)
    
    print(f"\nValidation complete:")
    print(f"Status: {validated.status.value}")
    print(f"Final confidence: {validated.current_confidence}")
    print(f"Disproof attempts: {len(validated.disproof_attempts)}")
    
    # Generate audit trail
    audit = agent.generate_audit_trail()
    print(f"\nInvestigation summary:")
    print(f"Total steps: {audit['investigation_summary']['total_steps']}")
    print(f"Hypotheses validated: {audit['investigation_summary']['hypotheses_validated']}")
    print(f"Hypotheses disproven: {audit['investigation_summary']['hypotheses_disproven']}")
    
    # Generate narrative for post-mortem
    narrative = agent.export_investigation_narrative()
    print(f"\n{'='*60}")
    print("Investigation Narrative:")
    print('='*60)
    print(narrative)
