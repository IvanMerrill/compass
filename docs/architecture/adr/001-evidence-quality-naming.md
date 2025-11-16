# ADR 001: Evidence Quality Naming Convention

## Status
Accepted

## Context
The scientific framework requires a quality rating system for evidence that:
- Is intuitive to domain experts (DBAs, network engineers, SREs)
- Has clear semantic meaning
- Maps to numeric weights for confidence calculation
- Aligns with industry incident investigation practices

Two approaches were considered:

### Option A: Simple Quality Levels
- `HIGH`, `MEDIUM`, `LOW`, `SUGGESTIVE`, `WEAK`
- Direct mapping to confidence (HIGH=1.0, MEDIUM=0.7, etc.)
- Simpler for newcomers to understand

### Option B: Semantic Evidence Types
- `DIRECT`, `CORROBORATED`, `INDIRECT`, `CIRCUMSTANTIAL`, `WEAK`
- Describes the nature of evidence gathering methodology
- Used in legal and scientific investigation contexts

## Decision
Use semantic evidence types: **DIRECT, CORROBORATED, INDIRECT, CIRCUMSTANTIAL, WEAK**

## Rationale

### 1. Professional Alignment
Matches terminology used in:
- Professional incident investigation (NTSB, Aviation Safety)
- Legal proceedings and forensic analysis
- Scientific research methodology
- Learning Teams post-mortem practices

### 2. Clearer Semantic Meaning
- **DIRECT**: "I observed the connection pool at 95%" - First-hand observation
- **HIGH**: "This is high quality" - Requires understanding the quality scale

The semantic name immediately conveys *how* the evidence was gathered, not just an arbitrary quality rating.

### 3. Encourages Methodological Thinking
Forces agents and engineers to consider:
- How was this evidence collected?
- Can it be corroborated?
- Am I making inferences (INDIRECT) or observing directly (DIRECT)?

This improves investigation rigor over time.

### 4. Better Audit Trails
Audit logs with "DIRECT observation" vs "CIRCUMSTANTIAL evidence" provide clearer context for compliance officers and incident reviewers than "HIGH quality" vs "LOW quality".

### 5. Prototype Validation
Reference implementation successfully used this approach without confusion. Team feedback was positive.

### 6. Documentation Consistency
The COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md examples use semantic naming throughout.

## Consequences

### Positive
- Domain experts find terminology familiar and professional
- Forces agents to consider evidence gathering methodology
- Better audit trails ("DIRECT observation from Prometheus" vs "HIGH quality metric")
- Aligns with Learning Teams methodology of rigorous investigation
- Clear mapping to quality weights maintains objectivity

### Negative
- Slightly longer enum names (`EvidenceQuality.CORROBORATED` vs `Quality.HIGH`)
- Requires brief explanation for newcomers (but this is valuable training time)
- May need glossary in documentation

### Neutral
- Both approaches map to numeric weights equally well
- Performance impact: negligible (enum comparison)

## Implementation

```python
class EvidenceQuality(Enum):
    """Quality rating based on evidence gathering methodology."""
    DIRECT = "direct"              # Weight: 1.0 - First-hand observation
    CORROBORATED = "corroborated"  # Weight: 0.9 - Confirmed by multiple sources
    INDIRECT = "indirect"          # Weight: 0.6 - Inferred from related data
    CIRCUMSTANTIAL = "circumstantial" # Weight: 0.3 - Suggestive but not conclusive
    WEAK = "weak"                  # Weight: 0.1 - Single source, potentially unreliable
```

### Quality Weight Mapping
The confidence calculation uses these weights:
- DIRECT: 1.0 (full weight)
- CORROBORATED: 0.9 (slightly discounted for interpretation variance)
- INDIRECT: 0.6 (inferred, not observed)
- CIRCUMSTANTIAL: 0.3 (suggestive pattern)
- WEAK: 0.1 (minimal weight, flags need for better evidence)

### Example Usage

```python
# Direct observation from monitoring system
Evidence(
    source="prometheus:connection_pool_utilization",
    data={"utilization": 0.95},
    interpretation="Pool at 95% capacity",
    quality=EvidenceQuality.DIRECT,  # We directly observed this metric
    confidence=0.9
)

# Corroborated by multiple sources
Evidence(
    source="logs:connection_errors + db_metrics:conn_refused",
    interpretation="Connection failures confirmed in logs and DB metrics",
    quality=EvidenceQuality.CORROBORATED,  # Multiple independent sources
    confidence=0.85
)

# Indirect inference
Evidence(
    source="apm:response_time_increase",
    interpretation="Response time increase suggests DB slowdown",
    quality=EvidenceQuality.INDIRECT,  # Inferred, not directly observed
    confidence=0.6
)
```

## Mitigations for Negatives

### 1. Documentation
- Comprehensive docstrings explain each quality level
- Examples in `COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md`
- Quick reference guide in ADR (this document)

### 2. Type Hints & IDE Support
- Full type hints make IDE autocomplete helpful
- Enum provides clear list of options

### 3. Training Value
The slight learning curve actually *improves* investigation quality by making engineers think about methodology.

## Alternatives Considered

### Simple Numeric Scale (1-5)
**Rejected**: No semantic meaning, arbitrary numbers

### Confidence-Based Names (CERTAIN, PROBABLE, POSSIBLE)
**Rejected**: Conflates quality with confidence (evidence can be DIRECT but low confidence)

### Source-Based Names (PRIMARY, SECONDARY, TERTIARY)
**Rejected**: Doesn't capture corroboration or inference levels

## Related Decisions
- Confidence calculation algorithm (uses these weights)
- Audit log format (includes quality level)
- Agent training and onboarding (teaches evidence methodology)

## References
- `src/compass/core/scientific_framework.py` - Implementation
- `tests/unit/core/test_scientific_framework.py` - Usage examples
- `docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md` - Framework documentation
- Learning Teams: "The five traps of evidence gathering" (source for quality levels)
- NTSB Investigation Manual (evidence classification methodology)

## Revision History
- 2025-11-16: Initial decision (Day 2 implementation)
- Status: Accepted and implemented

---

**Decision Made By**: COMPASS Team
**Date**: 2025-11-16
**Reviewed By**: [To be filled during team review]
