"""
Dynamic Query Generator for Observability Tools.

Generates PromQL, LogQL, and TraceQL queries dynamically using LLM,
allowing agents to ask whatever questions they need to validate hypotheses.

Key Features:
- Dynamic query generation via LLM
- Query validation before execution
- Cost tracking and budget enforcement ($10/investigation default)
- Query templates for common patterns (reduces LLM costs)
- Query caching for 75%+ cache hit rate
- Support for rate(), aggregation, and time-series queries

Usage:
    generator = QueryGenerator(llm_client=llm, budget_limit=Decimal("10.00"))

    request = QueryRequest(
        query_type=QueryType.PROMQL,
        intent="Check CPU usage over last 5 minutes",
        context={"service": "payment-service", "metric": "cpu_usage"},
    )

    result = generator.generate_query(request)
    print(result.query)  # "rate(cpu_usage{service="payment-service"}[5m])"
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
import hashlib
import re
import structlog


logger = structlog.get_logger()


class QueryType(Enum):
    """Types of observability queries supported."""

    PROMQL = "promql"  # Prometheus Query Language
    LOGQL = "logql"  # Loki/Grafana Log Query Language
    TRACEQL = "traceql"  # Tempo Trace Query Language


@dataclass
class QueryRequest:
    """Request for query generation."""

    query_type: QueryType
    intent: str  # What the query should accomplish
    context: Dict[str, Any]  # Context for query generation
    use_template: Optional[str] = None  # Optional template name


@dataclass
class GeneratedQuery:
    """Result of query generation."""

    query_type: QueryType
    query: str
    explanation: str
    is_valid: bool
    validation_errors: Optional[List[str]] = None
    tokens_used: int = 0
    cost: Decimal = Decimal("0.0000")
    used_template: bool = False
    from_cache: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class QueryGenerationError(Exception):
    """Raised when query generation fails."""

    pass


class QueryGenerator:
    """
    Generates observability queries dynamically using LLM.

    Replaces hardcoded queries in disproof strategies, allowing agents
    to ask whatever questions they need for hypothesis validation.
    """

    # Default estimated cost per query (used when no cost history available)
    DEFAULT_ESTIMATED_COST_PER_QUERY = Decimal("0.0020")  # $0.002

    # Target cache hit rate for cost optimization
    TARGET_CACHE_HIT_RATE = 0.75  # 75%+

    def __init__(
        self,
        llm_client: Any,
        budget_limit: Optional[Decimal] = None,
        enable_cache: bool = True,
    ):
        """
        Initialize QueryGenerator.

        Args:
            llm_client: LLM client for query generation
            budget_limit: Maximum cost for query generation (default: no limit)
            enable_cache: Enable query caching for cost optimization
        """
        self.llm_client = llm_client
        self.budget_limit = budget_limit
        self.enable_cache = enable_cache

        # Cost tracking
        self._total_queries = 0
        self._total_tokens = 0
        self._total_cost = Decimal("0.0000")
        self._non_cached_queries = 0  # Track queries that required LLM generation

        # Query cache for cost optimization
        self._query_cache: Dict[str, GeneratedQuery] = {}

        # Query templates for common patterns
        self._templates: Dict[str, Dict[str, Any]] = {}

        logger.info(
            "query_generator_initialized",
            budget_limit=str(budget_limit) if budget_limit else "unlimited",
            enable_cache=enable_cache,
        )

    def generate_query(self, request: QueryRequest) -> GeneratedQuery:
        """
        Generate observability query based on request.

        Args:
            request: Query generation request

        Returns:
            GeneratedQuery with query string and metadata

        Raises:
            QueryGenerationError: If generation fails or budget exceeded
        """
        logger.info(
            "generating_query",
            query_type=request.query_type.value,
            intent=request.intent,
            use_template=request.use_template,
        )

        # Check budget before generating (including estimated cost for next query)
        if self.budget_limit:
            # Calculate average cost per non-cached query
            avg_cost = (
                self._total_cost / self._non_cached_queries
                if self._non_cached_queries > 0
                else self.DEFAULT_ESTIMATED_COST_PER_QUERY
            )

            # Check if current cost + estimated next query cost would exceed budget
            estimated_total = self._total_cost + avg_cost
            if estimated_total > self.budget_limit:
                raise QueryGenerationError(
                    f"Budget exceeded: ${estimated_total} > ${self.budget_limit}"
                )

        # Try template first if specified
        if request.use_template:
            return self._generate_from_template(request)

        # Try cache if enabled
        if self.enable_cache:
            cached = self._get_from_cache(request)
            if cached:
                # Still count cached queries in totals (for tracking purposes)
                self._total_queries += 1
                self._total_tokens += cached.tokens_used  # Track tokens even for cached
                self._total_cost += cached.cost  # Track cost even for cached
                logger.info("query_cache_hit", query_type=request.query_type.value)
                return cached

        # Generate using LLM
        try:
            result = self._generate_with_llm(request)

            # Cache the result
            if self.enable_cache:
                self._cache_query(request, result)

            # Update cost tracking (including this query)
            self._total_queries += 1
            self._non_cached_queries += 1  # Track non-cached queries for budget estimation
            self._total_tokens += result.tokens_used
            self._total_cost += result.cost

            logger.info(
                "query_generated",
                query_type=request.query_type.value,
                tokens_used=result.tokens_used,
                cost=str(result.cost),
                is_valid=result.is_valid,
            )

            return result

        except Exception as e:
            logger.error(
                "query_generation_failed",
                query_type=request.query_type.value,
                error=str(e),
            )
            raise QueryGenerationError(f"Failed to generate query: {e}") from e

    def _generate_with_llm(self, request: QueryRequest) -> GeneratedQuery:
        """Generate query using LLM."""
        # Call LLM to generate query
        llm_response = self.llm_client.generate(
            query_type=request.query_type.value,
            intent=request.intent,
            context=request.context,
        )

        query = llm_response["query"]
        explanation = llm_response["explanation"]
        tokens_used = llm_response["tokens_used"]
        cost = llm_response["cost"]

        # Validate generated query
        is_valid, validation_errors = self._validate_query(request.query_type, query)

        return GeneratedQuery(
            query_type=request.query_type,
            query=query,
            explanation=explanation,
            is_valid=is_valid,
            validation_errors=validation_errors if not is_valid else None,
            tokens_used=tokens_used,
            cost=cost,
            used_template=False,
            from_cache=False,
        )

    def _generate_from_template(self, request: QueryRequest) -> GeneratedQuery:
        """Generate query from template (no LLM call)."""
        template_name = request.use_template
        if template_name not in self._templates:
            raise QueryGenerationError(f"Unknown template: {template_name}")

        template = self._templates[template_name]

        # Fill template with context
        query = template["template"].format(**request.context)

        # Validate template result
        is_valid, validation_errors = self._validate_query(request.query_type, query)

        logger.info(
            "query_from_template",
            template=template_name,
            is_valid=is_valid,
        )

        return GeneratedQuery(
            query_type=request.query_type,
            query=query,
            explanation=f"Generated from template: {template_name}",
            is_valid=is_valid,
            validation_errors=validation_errors if not is_valid else None,
            tokens_used=0,  # No LLM call
            cost=Decimal("0.0000"),
            used_template=True,
            from_cache=False,
        )

    def _validate_query(
        self, query_type: QueryType, query: str
    ) -> tuple[bool, Optional[List[str]]]:
        """
        Validate generated query syntax.

        Args:
            query_type: Type of query
            query: Query string to validate

        Returns:
            (is_valid, validation_errors)
        """
        errors = []

        if query_type == QueryType.PROMQL:
            # Basic PromQL validation
            # Must have metric name or function before any label selector
            # Invalid: {service="test"}
            # Valid: metric_name{service="test"} or rate(metric[5m])
            stripped = query.strip()
            if stripped.startswith("{"):
                errors.append("PromQL query missing metric name (cannot start with '{')")
            elif not re.search(r"[a-zA-Z_:][a-zA-Z0-9_:]*", query):
                errors.append("PromQL query missing metric name or function")

            # Check for unbalanced brackets
            if query.count("{") != query.count("}"):
                errors.append("Unbalanced curly braces in PromQL query")

            if query.count("[") != query.count("]"):
                errors.append("Unbalanced square brackets in PromQL query")

            if query.count("(") != query.count(")"):
                errors.append("Unbalanced parentheses in PromQL query")

        elif query_type == QueryType.LOGQL:
            # Basic LogQL validation
            # Must have log stream selector
            if not re.search(r"\{[^}]+\}", query):
                errors.append("LogQL query missing log stream selector")

        elif query_type == QueryType.TRACEQL:
            # Basic TraceQL validation
            # Must have span selector
            if not re.search(r"\{[^}]+\}", query):
                errors.append("TraceQL query missing span selector")

        is_valid = len(errors) == 0
        return is_valid, errors if not is_valid else None

    def _get_cache_key(self, request: QueryRequest) -> str:
        """Generate cache key for query request."""
        # Create hash of request parameters
        cache_data = f"{request.query_type.value}:{request.intent}:{str(request.context)}"
        return hashlib.md5(cache_data.encode()).hexdigest()

    def _get_from_cache(self, request: QueryRequest) -> Optional[GeneratedQuery]:
        """Get query from cache if available."""
        cache_key = self._get_cache_key(request)
        cached = self._query_cache.get(cache_key)

        if cached:
            # Return copy with updated from_cache flag
            # Note: Keep original tokens_used and cost for tracking purposes
            return GeneratedQuery(
                query_type=cached.query_type,
                query=cached.query,
                explanation=cached.explanation,
                is_valid=cached.is_valid,
                validation_errors=cached.validation_errors,
                tokens_used=cached.tokens_used,  # Keep original for tracking
                cost=cached.cost,  # Keep original for tracking
                used_template=cached.used_template,
                from_cache=True,
                timestamp=datetime.now(timezone.utc),
            )

        return None

    def _cache_query(self, request: QueryRequest, result: GeneratedQuery) -> None:
        """Cache generated query for future use."""
        cache_key = self._get_cache_key(request)
        self._query_cache[cache_key] = result

    def register_template(
        self, name: str, template: str, parameters: List[str]
    ) -> None:
        """
        Register a query template for common patterns.

        Templates reduce LLM costs for frequently used query patterns.

        Args:
            name: Template name
            template: Query template with {param} placeholders
            parameters: List of required parameter names

        Example:
            generator.register_template(
                name="metric_current_value",
                template='{metric_name}{{service="{service}"}}',
                parameters=["metric_name", "service"],
            )
        """
        self._templates[name] = {
            "template": template,
            "parameters": parameters,
        }

        logger.info(
            "template_registered",
            name=name,
            parameters=parameters,
        )

    def get_cost_stats(self) -> Dict[str, Any]:
        """
        Get cost tracking statistics.

        Returns:
            Dict with total_queries, total_tokens, total_cost, average_tokens_per_query
        """
        return {
            "total_queries": self._total_queries,
            "total_tokens": self._total_tokens,
            "total_cost": self._total_cost,
            "average_tokens_per_query": (
                self._total_tokens / self._total_queries if self._total_queries > 0 else 0.0
            ),
            "cache_size": len(self._query_cache),
            "template_count": len(self._templates),
        }
