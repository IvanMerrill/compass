"""
Proof of Concept: QueryGenerator Integration with Disproof Strategies

This demonstrates how QueryGenerator will enhance disproof strategies
with dynamic, AI-generated queries instead of simple hardcoded patterns.

Key Benefits:
1. Sophisticated queries: rate(), aggregations, complex filters
2. Context-aware: LLM generates queries based on hypothesis metadata
3. Cost-tracked: Every query tracked for budget management
4. Cached: Similar queries reused to reduce LLM costs

Integration Pattern:
-----------------
Before (simple):
    prometheus.query("cpu_usage")

After (dynamic):
    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Check if CPU usage spiked above 80%",
        context={
            "metric": "cpu_usage",
            "threshold": 0.80,
            "time_window": "5m",
            "service": "payment-service",
        }
    )
    generated = query_generator.generate_query(request)
    prometheus.query(generated.query)  # "rate(cpu_usage{service="payment"}[5m])"

Future Implementation Steps:
---------------------------
1. Update strategy constructors to accept QueryGenerator:
   ```python
   def __init__(self, prometheus_client, query_generator=None):
       self.prometheus = prometheus_client
       self.query_generator = query_generator
   ```

2. Enhance query construction in attempt_disproof():
   ```python
   if self.query_generator:
       # Use AI to generate sophisticated query
       request = QueryRequest(...)
       result = self.query_generator.generate_query(request)
       query = result.query
   else:
       # Fallback to simple query
       query = f"{metric_name}"
   ```

3. Track costs per strategy:
   ```python
   stats = self.query_generator.get_cost_stats()
   logger.info("strategy_query_costs", total_cost=stats["total_cost"])
   ```

Example: Temporal Contradiction Strategy Enhanced
-------------------------------------------------
"""
from decimal import Decimal
from compass.core.query_generator import QueryGenerator, QueryRequest, QueryType
from compass.core.disproof import TemporalContradictionStrategy
from compass.core.scientific_framework import Hypothesis


def example_enhanced_temporal_strategy():
    """
    Example showing how TemporalContradictionStrategy would use QueryGenerator.

    Scenario: Check if errors existed BEFORE deployment
    - Simple approach: {service="payment"} |= "error"
    - Enhanced approach: {service="payment"} |= "error" | json | level="error" | rate([5m])
    """
    print("=" * 80)
    print("EXAMPLE: Enhanced Temporal Contradiction Strategy")
    print("=" * 80)

    # Mock LLM client for demonstration
    class MockLLMClient:
        def generate(self, query_type, intent, context):
            # Simulate LLM generating sophisticated LogQL query
            service = context.get("service", "unknown")
            log_level = context.get("log_level", "error")

            # LLM would generate this based on intent and context
            sophisticated_query = (
                f'{{service="{service}"}} |= "{log_level}" '
                f'| json | level="{log_level}" '
                f'| line_format "{{{{.timestamp}}}} {{{{.message}}}}"'
            )

            return {
                "query": sophisticated_query,
                "explanation": f"Structured log query for {service} {log_level} logs with timestamp",
                "tokens_used": 180,
                "cost": Decimal("0.0018"),
            }

    # Create QueryGenerator
    query_generator = QueryGenerator(
        llm_client=MockLLMClient(),
        budget_limit=Decimal("10.00"),
    )

    # Create hypothesis
    hypothesis = Hypothesis(
        agent_id="application_agent",
        statement="Deployment at 10:30 caused errors",
        initial_confidence=0.7,
        metadata={
            "suspected_time": "2024-01-20T10:30:00Z",
            "service": "payment-service",
            "log_level": "error",
            "metric": "error_rate",
        },
    )

    # Generate query using QueryGenerator
    request = QueryRequest(
        query_type=QueryType.LOGQL,
        intent="Find error logs before deployment to check temporal contradiction",
        context={
            "service": hypothesis.metadata["service"],
            "log_level": hypothesis.metadata["log_level"],
            "time_range_start": "2024-01-20T08:00:00Z",
            "time_range_end": hypothesis.metadata["suspected_time"],
        },
    )

    print(f"\nHypothesis: {hypothesis.statement}")
    print(f"Service: {hypothesis.metadata['service']}")
    print(f"Suspected Time: {hypothesis.metadata['suspected_time']}")
    print()

    result = query_generator.generate_query(request)

    print("Generated LogQL Query:")
    print(f"  {result.query}")
    print()
    print(f"Explanation: {result.explanation}")
    print(f"Tokens Used: {result.tokens_used}")
    print(f"Cost: ${result.cost}")
    print()

    # Show cost tracking
    stats = query_generator.get_cost_stats()
    print("Cost Stats:")
    print(f"  Total Queries: {stats['total_queries']}")
    print(f"  Total Cost: ${stats['total_cost']}")
    print(f"  Remaining Budget: ${Decimal('10.00') - stats['total_cost']}")
    print()


def example_metric_strategy_with_rate():
    """
    Example showing how MetricThresholdValidationStrategy would use QueryGenerator for rate() queries.
    """
    print("=" * 80)
    print("EXAMPLE: Metric Strategy with Rate-Over-Time Analysis")
    print("=" * 80)

    class MockLLMClient:
        def generate(self, query_type, intent, context):
            metric = context.get("metric", "unknown")
            service = context.get("service", "unknown")
            time_window = context.get("time_window", "5m")

            # LLM generates rate query
            query = f'rate({metric}{{service="{service}"}}[{time_window}])'

            return {
                "query": query,
                "explanation": f"Calculate rate of {metric} over {time_window} for {service}",
                "tokens_used": 120,
                "cost": Decimal("0.0012"),
            }

    query_generator = QueryGenerator(llm_client=MockLLMClient())

    hypothesis = Hypothesis(
        agent_id="application_agent",
        statement="Request rate spiked above 1000 req/s",
        initial_confidence=0.7,
        metadata={
            "metric_claims": {
                "http_requests_total": {
                    "threshold": 1000,
                    "operator": ">=",
                    "analysis_type": "rate",
                    "time_window": "5m",
                }
            },
            "service": "payment-service",
        },
    )

    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Calculate request rate over 5 minutes to validate threshold claim",
        context={
            "metric": "http_requests_total",
            "service": hypothesis.metadata["service"],
            "time_window": "5m",
            "analysis_type": "rate",
        },
    )

    print(f"\nHypothesis: {hypothesis.statement}")
    print(f"Threshold: >= 1000 req/s")
    print()

    result = query_generator.generate_query(request)

    print("Generated PromQL Query:")
    print(f"  {result.query}")
    print()
    print(f"Explanation: {result.explanation}")
    print()
    print("Comparison:")
    print("  Simple approach: http_requests_total")
    print(f"  Enhanced approach: {result.query}")
    print()


def example_scope_strategy_with_aggregation():
    """
    Example showing how ScopeVerificationStrategy would use QueryGenerator for aggregations.
    """
    print("=" * 80)
    print("EXAMPLE: Scope Strategy with Service Aggregation")
    print("=" * 80)

    class MockLLMClient:
        def generate(self, query_type, intent, context):
            service_pattern = context.get("service_pattern", ".*")

            # LLM generates TraceQL with aggregation
            query = f'{{span.service.name=~"{service_pattern}" && status=error}} | count() by(span.service.name)'

            return {
                "query": query,
                "explanation": f"Count error traces by service matching pattern '{service_pattern}'",
                "tokens_used": 160,
                "cost": Decimal("0.0016"),
            }

    query_generator = QueryGenerator(llm_client=MockLLMClient())

    hypothesis = Hypothesis(
        agent_id="application_agent",
        statement="Errors isolated to payment-service only",
        initial_confidence=0.7,
        metadata={
            "claimed_scope": "specific_services",
            "affected_services": ["payment-service"],
            "service_pattern": "payment.*",
        },
    )

    request = QueryRequest(
        query_type=QueryType.TRACEQL,
        intent="Count errors across services to verify if errors are truly isolated",
        context={
            "service_pattern": hypothesis.metadata["service_pattern"],
            "status": "error",
        },
    )

    print(f"\nHypothesis: {hypothesis.statement}")
    print(f"Service Pattern: {hypothesis.metadata['service_pattern']}")
    print()

    result = query_generator.generate_query(request)

    print("Generated TraceQL Query:")
    print(f"  {result.query}")
    print()
    print(f"Explanation: {result.explanation}")
    print()


def show_cost_benefits():
    """
    Demonstrate cost benefits of QueryGenerator caching.
    """
    print("=" * 80)
    print("COST BENEFITS: Query Caching")
    print("=" * 80)

    class MockLLMClient:
        def __init__(self):
            self.call_count = 0

        def generate(self, query_type, intent, context):
            self.call_count += 1
            return {
                "query": "test_query",
                "explanation": "test",
                "tokens_used": 100,
                "cost": Decimal("0.0010"),
            }

    llm_client = MockLLMClient()
    query_generator = QueryGenerator(llm_client=llm_client, enable_cache=True)

    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Check CPU usage",
        context={"metric": "cpu_usage"},
    )

    print("\nGenerating 5 identical queries:")
    print()

    for i in range(1, 6):
        result = query_generator.generate_query(request)
        status = "CACHE HIT" if result.from_cache else "LLM CALL"
        print(f"  Query {i}: {status} - Cost: ${result.cost}, Tokens: {result.tokens_used}")

    print()
    print(f"LLM called: {llm_client.call_count} time(s)")
    print(f"Cache hits: {5 - llm_client.call_count}")
    print(f"Cache hit rate: {((5 - llm_client.call_count) / 5) * 100:.1f}%")
    print()

    stats = query_generator.get_cost_stats()
    print("Cost Comparison:")
    print(f"  Without caching: ${Decimal('0.0010') * 5} (5 LLM calls)")
    print(f"  With caching: ${stats['total_cost']} (1 LLM call + 4 cache hits)")
    print(f"  Savings: ${(Decimal('0.0010') * 5) - stats['total_cost']}")
    print()


if __name__ == "__main__":
    example_enhanced_temporal_strategy()
    print("\n")
    example_metric_strategy_with_rate()
    print("\n")
    example_scope_strategy_with_aggregation()
    print("\n")
    show_cost_benefits()

    print("=" * 80)
    print("SUMMARY: QueryGenerator Integration Benefits")
    print("=" * 80)
    print()
    print("1. SOPHISTICATED QUERIES")
    print("   - Rate calculations: rate(metric[5m])")
    print("   - Aggregations: avg(metric) by (instance)")
    print("   - Structured parsing: | json | level='error'")
    print()
    print("2. CONTEXT-AWARE GENERATION")
    print("   - LLM understands hypothesis intent")
    print("   - Generates appropriate query syntax")
    print("   - Adapts to service, time range, thresholds")
    print()
    print("3. COST OPTIMIZATION")
    print("   - Query caching (75%+ hit rate)")
    print("   - Budget enforcement ($10/investigation)")
    print("   - Cost tracking per query")
    print()
    print("4. BACKWARD COMPATIBLE")
    print("   - Strategies work without QueryGenerator")
    print("   - Graceful degradation to simple queries")
    print("   - Optional enhancement, not required")
    print()
