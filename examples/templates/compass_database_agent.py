"""
COMPASS Database Specialist Agent
==================================

Extends the scientific framework with database-specific investigation capabilities.
Demonstrates how specialist agents implement domain-specific disproof strategies.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from compass_scientific_framework import (
    ScientificAgent, Hypothesis, DisproofAttempt, Evidence,
    EvidenceQuality, InvestigativeAction
)


class DatabaseAgent(ScientificAgent):
    """
    Specialist agent for database-related incident investigation.
    
    Focuses on:
    - Connection pool issues
    - Query performance
    - Lock contention
    - Replication lag
    - Resource exhaustion (connections, disk, memory)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="database_specialist", config=config)
        
        # Database-specific data source connections
        self.data_sources = self.config.get('data_sources', {
            'prometheus': True,
            'database_logs': True,
            'slow_query_log': True,
            'connection_metrics': True,
            'replication_metrics': True
        })
    
    def generate_disproof_strategies(self, hypothesis: Hypothesis) -> List[Dict[str, Any]]:
        """
        Generate database-specific strategies to disprove a hypothesis.
        
        Common disproof strategies for database hypotheses:
        1. Temporal contradiction - timing doesn't align
        2. Scope mismatch - only affects subset, not root cause
        3. Metric contradiction - metrics show opposite pattern
        4. Alternative explanation - simpler cause exists
        5. Logical impossibility - can't be true given constraints
        """
        strategies = []
        
        # Extract hypothesis type from statement
        statement_lower = hypothesis.statement.lower()
        
        # Strategy 1: Check temporal alignment
        if any(term in statement_lower for term in ['caused', 'triggered', 'led to']):
            strategies.append({
                'strategy': 'temporal_contradiction',
                'method': 'verify_timing_alignment',
                'expected_if_true': 'Suspected cause timestamp precedes symptom timestamp',
                'data_sources_needed': ['prometheus', 'database_logs'],
                'priority': 0.9,  # High priority - quick to check
                'test_func': self._test_temporal_alignment
            })
        
        # Strategy 2: Check if connection-related hypothesis
        if 'connection' in statement_lower:
            strategies.append({
                'strategy': 'connection_metrics_contradiction',
                'method': 'check_connection_pool_metrics',
                'expected_if_true': 'Connection pool utilization should be high (>80%)',
                'data_sources_needed': ['prometheus', 'connection_metrics'],
                'priority': 0.95,
                'test_func': self._test_connection_metrics
            })
            
            strategies.append({
                'strategy': 'connection_timeout_pattern',
                'method': 'analyze_connection_timeout_distribution',
                'expected_if_true': 'Timeouts should correlate with pool exhaustion',
                'data_sources_needed': ['prometheus', 'database_logs'],
                'priority': 0.85,
                'test_func': self._test_connection_timeout_pattern
            })
        
        # Strategy 3: Check if query performance hypothesis
        if any(term in statement_lower for term in ['slow', 'query', 'performance']):
            strategies.append({
                'strategy': 'query_plan_analysis',
                'method': 'check_explain_plans_for_degradation',
                'expected_if_true': 'Query plans should show increased cost or missing indexes',
                'data_sources_needed': ['slow_query_log', 'database_logs'],
                'priority': 0.8,
                'test_func': self._test_query_performance
            })
            
            strategies.append({
                'strategy': 'query_volume_check',
                'method': 'verify_query_volume_increase',
                'expected_if_true': 'Query volume or complexity should increase at incident time',
                'data_sources_needed': ['prometheus'],
                'priority': 0.85,
                'test_func': self._test_query_volume
            })
        
        # Strategy 4: Check if lock contention hypothesis
        if any(term in statement_lower for term in ['lock', 'contention', 'deadlock']):
            strategies.append({
                'strategy': 'lock_metrics_validation',
                'method': 'check_lock_wait_time_increase',
                'expected_if_true': 'Lock wait times should spike during incident',
                'data_sources_needed': ['prometheus', 'database_logs'],
                'priority': 0.9,
                'test_func': self._test_lock_contention
            })
            
            strategies.append({
                'strategy': 'deadlock_frequency',
                'method': 'check_deadlock_occurrence_rate',
                'expected_if_true': 'Deadlock frequency should increase',
                'data_sources_needed': ['database_logs'],
                'priority': 0.85,
                'test_func': self._test_deadlock_frequency
            })
        
        # Strategy 5: Check if replication lag hypothesis
        if 'replication' in statement_lower or 'lag' in statement_lower:
            strategies.append({
                'strategy': 'replication_lag_validation',
                'method': 'measure_actual_replication_lag',
                'expected_if_true': 'Replication lag should exceed threshold during incident',
                'data_sources_needed': ['prometheus', 'replication_metrics'],
                'priority': 0.95,
                'test_func': self._test_replication_lag
            })
        
        # Strategy 6: Check if resource exhaustion hypothesis
        if any(term in statement_lower for term in ['memory', 'disk', 'cpu', 'resource']):
            strategies.append({
                'strategy': 'resource_utilization_check',
                'method': 'verify_resource_saturation',
                'expected_if_true': 'Resource utilization should exceed 85% during incident',
                'data_sources_needed': ['prometheus'],
                'priority': 0.9,
                'test_func': self._test_resource_exhaustion
            })
        
        # Strategy 7: Scope limitation check (always applicable)
        strategies.append({
            'strategy': 'scope_verification',
            'method': 'verify_hypothesis_explains_all_symptoms',
            'expected_if_true': 'Hypothesis should explain >80% of affected systems',
            'data_sources_needed': ['prometheus'],
            'priority': 0.7,
            'test_func': self._test_scope_coverage
        })
        
        # Strategy 8: Alternative simpler explanation
        strategies.append({
            'strategy': 'alternative_explanation',
            'method': 'search_for_simpler_causes',
            'expected_if_true': 'No simpler explanation with stronger evidence',
            'data_sources_needed': ['prometheus', 'database_logs'],
            'priority': 0.6,
            'test_func': self._test_alternative_explanations
        })
        
        # Sort by priority
        strategies.sort(key=lambda x: x['priority'], reverse=True)
        
        return strategies
    
    def filter_feasible_strategies(
        self, 
        strategies: List[Dict[str, Any]], 
        hypothesis: Hypothesis
    ) -> List[Dict[str, Any]]:
        """Filter to strategies where we have the required data sources"""
        feasible = []
        
        for strategy in strategies:
            required_sources = set(strategy['data_sources_needed'])
            available_sources = {k for k, v in self.data_sources.items() if v}
            
            if required_sources.issubset(available_sources):
                feasible.append(strategy)
            else:
                # Log why we can't execute this strategy
                missing = required_sources - available_sources
                self._log_infeasible_strategy(strategy, missing)
        
        return feasible
    
    def attempt_disproof(
        self, 
        hypothesis: Hypothesis, 
        strategy: Dict[str, Any]
    ) -> DisproofAttempt:
        """Execute a disproof attempt using the strategy's test function"""
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
            attempt.observed = f"Test failed: {str(e)}"
            attempt.disproven = False
            attempt.reasoning = "Unable to complete test due to error"
        
        # Track cost
        end_time = datetime.now(timezone.utc)
        attempt.cost = {
            'time_ms': (end_time - start_time).total_seconds() * 1000,
            'tokens': 0  # Updated if LLM was used
        }
        
        return attempt
    
    # ==================== Test Functions ====================
    # These would connect to actual data sources in production
    
    def _test_temporal_alignment(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Test if timing aligns with causation claim"""
        
        # Simulate checking temporal alignment
        # In production, this would query actual timestamps from logs/metrics
        
        def execute_check():
            # This is where actual data fetching happens
            # For now, return structure showing what real implementation would do
            return {
                'suspected_cause_time': '2024-11-14T10:15:00Z',
                'symptom_start_time': '2024-11-14T10:15:05Z',
                'time_delta_seconds': 5
            }
        
        step = self.execute_investigation_step(
            action=InvestigativeAction.CORRELATE,
            purpose=f"Verify temporal alignment for: {hypothesis.statement}",
            expected_outcome="Cause should precede symptoms by reasonable time window",
            method="Compare timestamps from logs and metrics",
            data_sources=['prometheus', 'database_logs'],
            execution_func=execute_check,
            hypothesis_context=hypothesis.id
        )
        
        # Analyze results
        if step.successful:
            # In real implementation, parse actual timing data
            # If cause happened AFTER symptoms, hypothesis is disproven
            time_delta = 5  # Placeholder
            
            if time_delta < 0:
                return {
                    'observed': f'Suspected cause occurred {abs(time_delta)}s AFTER symptoms began',
                    'disproven': True,
                    'reasoning': 'Temporal contradiction: effect cannot precede cause',
                    'evidence': []
                }
            elif time_delta > 300:  # 5 minutes
                return {
                    'observed': f'Suspected cause occurred {time_delta}s before symptoms - too long',
                    'disproven': True,
                    'reasoning': 'Time gap too large for direct causation',
                    'evidence': []
                }
            else:
                return {
                    'observed': f'Suspected cause preceded symptoms by {time_delta}s - plausible timing',
                    'disproven': False,
                    'reasoning': 'Temporal alignment is consistent with hypothesis',
                    'evidence': []
                }
        
        return {
            'observed': 'Unable to verify timing',
            'disproven': False,
            'reasoning': 'Insufficient data to test temporal alignment'
        }
    
    def _test_connection_metrics(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Test if connection pool metrics support the hypothesis"""
        
        def execute_check():
            # Query Prometheus for connection pool metrics
            # Example: rate(pg_stat_database_numbackends[5m])
            return {
                'pool_utilization_percent': 45,
                'max_connections': 100,
                'active_connections': 45,
                'waiting_connections': 2
            }
        
        step = self.execute_investigation_step(
            action=InvestigativeAction.MEASURE,
            purpose="Measure connection pool utilization during incident",
            expected_outcome="Pool utilization >80% if connection exhaustion is root cause",
            method="Query Prometheus pg_stat_database metrics",
            data_sources=['prometheus', 'connection_metrics'],
            execution_func=execute_check,
            hypothesis_context=hypothesis.id
        )
        
        if step.successful:
            utilization = 45  # Placeholder - would come from actual data
            
            if utilization < 60:
                evidence = Evidence(
                    source="prometheus:pg_stat_database_numbackends",
                    data=f"Pool utilization: {utilization}%",
                    interpretation=f"Connection pool had significant spare capacity ({100-utilization}%)",
                    quality=EvidenceQuality.DIRECT,
                    supports_hypothesis=False,
                    confidence=0.9
                )
                
                self.evidence_store[evidence.id] = evidence
                
                return {
                    'observed': f'Connection pool utilization was only {utilization}% - well below saturation',
                    'disproven': True,
                    'reasoning': 'Connection pool exhaustion requires near-100% utilization. Observed usage was low.',
                    'evidence': [evidence]
                }
            else:
                return {
                    'observed': f'Connection pool utilization was {utilization}% - approaching saturation',
                    'disproven': False,
                    'reasoning': 'Connection metrics consistent with pool pressure',
                    'evidence': []
                }
        
        return {
            'observed': 'Unable to retrieve connection metrics',
            'disproven': False,
            'reasoning': 'Test inconclusive due to data unavailability'
        }
    
    def _test_connection_timeout_pattern(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Analyze distribution of connection timeouts"""
        
        def execute_check():
            # Analyze log patterns for connection timeouts
            return {
                'timeout_rate': 0.02,  # 2%
                'timeout_correlation_with_pool': 0.15
            }
        
        step = self.execute_investigation_step(
            action=InvestigativeAction.CORRELATE,
            purpose="Check if timeouts correlate with pool exhaustion",
            expected_outcome="High correlation (>0.7) if pool is the cause",
            method="Correlate timeout rate with pool utilization",
            data_sources=['prometheus', 'database_logs'],
            execution_func=execute_check,
            hypothesis_context=hypothesis.id
        )
        
        if step.successful:
            correlation = 0.15  # Placeholder
            
            if correlation < 0.5:
                return {
                    'observed': f'Timeout correlation with pool utilization: {correlation} (weak)',
                    'disproven': True,
                    'reasoning': 'If pool exhaustion caused timeouts, correlation should be strong (>0.7)',
                    'evidence': []
                }
            else:
                return {
                    'observed': f'Timeout correlation with pool utilization: {correlation} (strong)',
                    'disproven': False,
                    'reasoning': 'Pattern consistent with pool-related timeouts',
                    'evidence': []
                }
        
        return {
            'observed': 'Unable to analyze timeout patterns',
            'disproven': False,
            'reasoning': 'Insufficient data for correlation analysis'
        }
    
    def _test_query_performance(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Check if query performance actually degraded"""
        
        def execute_check():
            # Compare query plans before/during incident
            return {
                'avg_query_time_before': 45,
                'avg_query_time_during': 47,
                'change_percent': 4.4
            }
        
        step = self.execute_investigation_step(
            action=InvestigativeAction.COMPARE,
            purpose="Compare query performance before/during incident",
            expected_outcome="Significant degradation (>20%) if query issue is root cause",
            method="Analyze slow query log and execution plans",
            data_sources=['slow_query_log', 'database_logs'],
            execution_func=execute_check,
            hypothesis_context=hypothesis.id
        )
        
        if step.successful:
            change_percent = 4.4  # Placeholder
            
            if abs(change_percent) < 10:
                return {
                    'observed': f'Query performance change: {change_percent}% (minimal)',
                    'disproven': True,
                    'reasoning': 'No significant query performance degradation detected',
                    'evidence': []
                }
            else:
                return {
                    'observed': f'Query performance degraded by {change_percent}%',
                    'disproven': False,
                    'reasoning': 'Significant performance change detected',
                    'evidence': []
                }
        
        return {
            'observed': 'Unable to compare query performance',
            'disproven': False,
            'reasoning': 'Query logs not available for comparison'
        }
    
    def _test_query_volume(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Check if query volume increased"""
        # Similar pattern to above
        return {
            'observed': 'Query volume remained stable',
            'disproven': False,
            'reasoning': 'Placeholder implementation'
        }
    
    def _test_lock_contention(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Check if lock wait times increased"""
        # Similar pattern to above
        return {
            'observed': 'Lock wait times did not increase',
            'disproven': False,
            'reasoning': 'Placeholder implementation'
        }
    
    def _test_deadlock_frequency(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Check deadlock occurrence rate"""
        return {
            'observed': 'No deadlocks detected during incident window',
            'disproven': False,
            'reasoning': 'Placeholder implementation'
        }
    
    def _test_replication_lag(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Measure replication lag"""
        return {
            'observed': 'Replication lag within normal bounds',
            'disproven': False,
            'reasoning': 'Placeholder implementation'
        }
    
    def _test_resource_exhaustion(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Check resource utilization"""
        return {
            'observed': 'Resource utilization normal',
            'disproven': False,
            'reasoning': 'Placeholder implementation'
        }
    
    def _test_scope_coverage(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Verify hypothesis explains most affected systems"""
        return {
            'observed': 'Hypothesis explains 95% of affected systems',
            'disproven': False,
            'reasoning': 'Broad scope coverage - consistent with root cause'
        }
    
    def _test_alternative_explanations(
        self, 
        hypothesis: Hypothesis, 
        attempt: DisproofAttempt
    ) -> Dict[str, Any]:
        """Search for simpler alternative explanations"""
        return {
            'observed': 'No simpler alternative found',
            'disproven': False,
            'reasoning': 'Current hypothesis is most parsimonious explanation'
        }
    
    def _log_infeasible_strategy(self, strategy: Dict[str, Any], missing_sources: set):
        """Log when a strategy can't be executed due to missing data sources"""
        # In production, this would go to logging system
        print(f"Cannot execute {strategy['strategy']} - missing data sources: {missing_sources}")


# Configuration example for Database Agent
DATABASE_AGENT_CONFIG = {
    # Base scientific framework settings
    'time_budget_per_hypothesis': 45.0,
    'cost_budget_per_hypothesis': 8000,
    'max_disproof_attempts': 5,
    'min_confidence_threshold': 0.65,
    
    # Database-specific settings
    'data_sources': {
        'prometheus': True,
        'database_logs': True,
        'slow_query_log': True,
        'connection_metrics': True,
        'replication_metrics': True
    },
    
    # Thresholds for disproof tests
    'thresholds': {
        'connection_pool_saturation': 0.80,
        'query_performance_degradation': 0.20,
        'replication_lag_seconds': 10,
        'scope_coverage_minimum': 0.80,
        'lock_wait_time_increase': 0.50
    }
}
