"""LLM prompts for DatabaseAgent hypothesis generation.

This module contains prompts for generating database-related hypotheses
using LLM providers (OpenAI and Anthropic).

Design Principles:
- Clear, specific instructions for LLM
- Request structured JSON output for reliable parsing
- Include domain expertise about database systems
- Guide LLM to generate testable, falsifiable hypotheses
"""

# System prompt providing database domain context
SYSTEM_PROMPT = """You are an expert database reliability engineer investigating database-related incidents.

Your role is to generate testable, falsifiable hypotheses about database issues based on observational data from metrics (Prometheus/Mimir), logs (Loki), and distributed traces (Tempo).

When generating hypotheses:
1. Base them on evidence from observations (metrics, logs, traces)
2. Make them specific and testable (not vague)
3. Include affected systems/components
4. Estimate initial confidence (0.0-1.0) based on evidence strength
5. Focus on root causes, not symptoms

Common database issue patterns:
- Connection pool exhaustion
- Slow query performance (missing indexes, inefficient queries)
- Lock contention and deadlocks
- Replication lag
- Resource exhaustion (CPU, memory, disk I/O)
- Network issues between app and database
- Configuration issues (timeouts, connection limits)
"""

# User prompt template for hypothesis generation
HYPOTHESIS_GENERATION_PROMPT_TEMPLATE = """Based on the following database observations, generate a hypothesis about what might be causing the incident.

## Observations

### Metrics (Prometheus/Mimir)
{metrics}

### Logs (Loki)
{logs}

### Traces (Tempo)
{traces}

### Observation Timestamp
{timestamp}

### Observation Confidence
{confidence} (0.0-1.0, where 1.0 means all data sources available)

{context}

## Task

Generate ONE testable hypothesis about the root cause of this database incident.

Respond with ONLY a JSON object in this exact format (no markdown, no additional text):

{{
  "statement": "Clear, specific hypothesis statement about the root cause",
  "initial_confidence": 0.7,
  "affected_systems": ["list", "of", "affected", "database", "components"],
  "reasoning": "Brief explanation of why this hypothesis is plausible based on the observations"
}}

Requirements:
- statement: Must be specific and testable (e.g., "PostgreSQL connection pool exhausted due to leaked connections")
- initial_confidence: Float between 0.0-1.0 based on evidence strength
- affected_systems: List of specific components (e.g., ["postgres-primary", "connection-pool", "api-backend"])
- reasoning: 1-2 sentences explaining the hypothesis

Generate the JSON now:"""


def format_hypothesis_prompt(
    metrics: str,
    logs: str,
    traces: str,
    timestamp: str,
    confidence: float,
    context: str = "",
) -> str:
    """Format the hypothesis generation prompt with observation data.

    Args:
        metrics: Formatted metrics data from observations
        logs: Formatted logs data from observations
        traces: Formatted traces data from observations
        timestamp: ISO 8601 timestamp of observations
        confidence: Confidence score (0.0-1.0) of observations
        context: Optional additional context about the incident

    Returns:
        Formatted prompt string ready for LLM
    """
    # Add context section if provided
    context_section = ""
    if context:
        context_section = f"\n### Additional Context\n{context}\n"

    return HYPOTHESIS_GENERATION_PROMPT_TEMPLATE.format(
        metrics=metrics or "No metrics data available",
        logs=logs or "No logs data available",
        traces=traces or "No traces data available",
        timestamp=timestamp,
        confidence=confidence,
        context=context_section,
    )
