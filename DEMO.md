# COMPASS Quick Start Demo

This guide shows you how to run COMPASS end-to-end demo.

## Prerequisites

- Python 3.11+
- Poetry installed
- OpenAI or Anthropic API key

## Setup

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Set API key** (choose one):
   ```bash
   export OPENAI_API_KEY="sk-..."
   # OR
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

3. **(Optional) Configure MCP servers:**
   ```bash
   # Not required for demo - DatabaseAgent works without MCP
   export GRAFANA_URL="..."
   export GRAFANA_TOKEN="..."
   ```

## Run Demo

```bash
poetry run compass investigate \
  --service payment-service \
  --symptom "high latency and 500 errors" \
  --severity critical
```

## What Happens

1. **Observe**: DatabaseAgent queries metrics/logs/traces (or uses empty data if no MCP)
2. **Orient**: DatabaseAgent generates hypothesis using LLM
3. **Decide**: You select which hypothesis to validate
4. **Act**: System validates hypothesis with disproof strategies
5. **Result**: Investigation completes with RESOLVED status

## Expected Output

```
=== COMPASS Investigation ===
Service: payment-service
Symptom: high latency and 500 errors
Severity: critical

[OBSERVE] Querying 1 specialist agents...
  ✓ database_specialist (confidence: 0.8)

[ORIENT] Generated 1 hypotheses:
  [1] Database connection pool exhausted (85% confidence)

[DECIDE] Select hypothesis to validate:
> 1

[ACT] Validating hypothesis...
  ✓ temporal_contradiction: Not disproven
  ✓ scope_verification: Not disproven
  ✓ correlation_vs_causation: Not disproven

[RESOLVED] Investigation complete!
  Hypothesis: Database connection pool exhausted
  Confidence: 90% (initial: 85%)
  Cost: $0.25
  Duration: 8.2s
```

## Troubleshooting

### No LLM provider configured
```
⚠️  OpenAI API key not configured. Set OPENAI_API_KEY environment variable.
```
→ Set OPENAI_API_KEY or ANTHROPIC_API_KEY

### Investigation INCONCLUSIVE
→ Normal when no LLM provider configured
→ Check that API key is valid and has sufficient credits

### Permission denied or module not found
```bash
# Ensure you're in the poetry shell
poetry shell

# Or use poetry run prefix
poetry run compass investigate --help
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | None |
| `ANTHROPIC_API_KEY` | Anthropic API key | None |
| `DEFAULT_LLM_PROVIDER` | LLM provider to use | `openai` |
| `DEFAULT_MODEL_NAME` | Model for worker agents | `gpt-4o-mini` |
| `DEFAULT_COST_BUDGET_USD` | Budget for low/medium/high severity | `10.0` |
| `CRITICAL_COST_BUDGET_USD` | Budget for critical severity | `20.0` |

### Severity Levels

- **low/medium/high**: Uses `DEFAULT_COST_BUDGET_USD` ($10.00)
- **critical**: Uses `CRITICAL_COST_BUDGET_USD` ($20.00)

## Example Investigations

### Database Performance Issue
```bash
poetry run compass investigate \
  --service postgres-db \
  --symptom "slow queries and high CPU" \
  --severity high
```

### API Latency Spike
```bash
poetry run compass investigate \
  --service api-backend \
  --symptom "p99 latency increased 5x" \
  --severity critical
```

### Microservice Communication Failure
```bash
poetry run compass investigate \
  --service order-service \
  --symptom "timeout errors calling payment service" \
  --severity medium
```

## Next Steps

- See [README.md](README.md) for full documentation
- Check [Architecture](docs/architecture.md) for system design
- Review [Contributing](CONTRIBUTING.md) for development guidelines
