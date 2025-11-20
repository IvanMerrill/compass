# Phase 8 Plan: "Post-mortem Generation"

**Version:** 1.0
**Date:** 2025-11-18
**Status:** DRAFT - Awaiting Plan Review

---

## Executive Summary

**Goal:** Generate clear, actionable post-mortem documents from completed investigations

**Current State:**
- ✅ Investigations complete end-to-end (Phase 7)
- ✅ OODA cycle reaches RESOLVED status
- ✅ Investigation data structure captures all context
- ❌ No post-mortem documentation generated
- ❌ No way to share investigation results
- ❌ Learning from incidents not captured in standard format

**Target State:**
- User runs investigation to completion
- System automatically generates post-mortem document
- Post-mortem saved to file (e.g., `postmortems/payment-db-2025-11-18-140532.md`)
- Post-mortem includes: summary, timeline, hypothesis, validation results, recommendations
- User can review, edit, and share post-mortem with team

---

## Why This Phase?

Following YAGNI and "prove it works" philosophy:
1. Phase 7 proved the system works end-to-end
2. Phase 8 captures the value of investigations for learning
3. Post-mortems are **core to Learning Teams approach** (not a nice-to-have)
4. Minimal scope: just format existing investigation data

**Value Proposition:**
- Without post-mortems: Investigation results lost after CLI output disappears
- With post-mortems: Persistent documentation for learning, communication, compliance

**NOT included (deferred to later phases):**
- Investigation history/search (post-MVP)
- MCP server integration (works without it)
- Multiple specialist agents (DatabaseAgent sufficient for MVP)
- Web UI for post-mortems (CLI-only per MVP scope)
- Real-time collaboration (post-MVP)

---

## Phase Breakdown

### Phase 8.1: Post-mortem Data Model & Template

**TDD Steps:**
1. RED: Write tests for PostMortem dataclass
2. GREEN: Implement PostMortem model with all fields
3. RED: Write tests for markdown template rendering
4. GREEN: Implement markdown template
5. REFACTOR: Ensure type safety
6. COMMIT: "feat(postmortem): Add post-mortem data model and markdown template"

**Files Changed:**
- `src/compass/core/postmortem.py` (new)
- `tests/unit/core/test_postmortem.py` (new)

**Why:** Need data model and template before generation logic

**YAGNI Check:** ✅ Minimal model with only essential fields, simple markdown template

---

### Phase 8.2: Post-mortem Generator

**TDD Steps:**
1. RED: Write tests for PostMortemGenerator.generate()
2. GREEN: Implement generator that creates PostMortem from OODAResult
3. RED: Write tests for file writing
4. GREEN: Implement save_to_file() method
5. REFACTOR: Handle edge cases (no hypotheses, etc.)
6. COMMIT: "feat(postmortem): Add post-mortem generator"

**Files Changed:**
- `src/compass/core/postmortem.py` (extend)
- `tests/unit/core/test_postmortem.py` (extend)

**Why:** Core logic to transform investigation results into post-mortem

**YAGNI Check:** ✅ Single generator class, simple transformation, no fancy features

---

### Phase 8.3: CLI Integration

**TDD Steps:**
1. RED: Write integration test for post-mortem generation in CLI
2. GREEN: Update CLI to call generator after investigation
3. GREEN: Add --output-dir flag for post-mortem location
4. RED: Write test for --skip-postmortem flag
5. GREEN: Add --skip-postmortem flag
6. REFACTOR: Handle file I/O errors gracefully
7. COMMIT: "feat(cli): Generate post-mortems after investigations"

**Files Changed:**
- `src/compass/cli/main.py`
- `tests/integration/test_cli_integration.py`

**Why:** Make post-mortem generation automatic in CLI flow

**YAGNI Check:** ✅ Simple flags, sensible defaults, optional skip

---

### Phase 8.4: Update Demo Documentation

**NO TDD** (documentation only)

1. Update DEMO.md with post-mortem examples
2. Document post-mortem file location and format
3. Show example post-mortem content
4. COMMIT: "docs: Update demo with post-mortem examples"

**Files Changed:**
- `DEMO.md`
- `README.md` (mention post-mortems)

**Why:** Users need to know about post-mortem output

**YAGNI Check:** ✅ Minimal docs update, examples only

---

## Detailed Implementation Plan

### 8.1: Post-mortem Data Model & Template

**What to Build:**

```python
# src/compass/core/postmortem.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from compass.core.investigation import Investigation
from compass.core.ooda_orchestrator import OODAResult
from compass.core.scientific_framework import Hypothesis, ValidationResult


@dataclass
class PostMortem:
    """Post-mortem document for completed investigation.

    Captures investigation results in standardized format for
    learning, communication, and compliance.
    """

    # Core identification
    investigation_id: str
    generated_at: datetime

    # Incident details
    service: str
    symptom: str
    severity: str

    # Investigation results
    status: str  # "RESOLVED", "INCONCLUSIVE", etc.
    selected_hypothesis: Optional[Hypothesis]
    validation_result: Optional[ValidationResult]

    # Metadata
    total_cost: float
    duration_seconds: float
    agent_count: int

    def to_markdown(self) -> str:
        """Render post-mortem as markdown document.

        Returns:
            Markdown-formatted post-mortem document
        """
        pass

    @classmethod
    def from_ooda_result(cls, result: OODAResult) -> "PostMortem":
        """Create post-mortem from OODA investigation result.

        Args:
            result: Completed OODA investigation result

        Returns:
            PostMortem instance
        """
        pass


def generate_postmortem(result: OODAResult) -> PostMortem:
    """Generate post-mortem from investigation result.

    Args:
        result: Completed OODA investigation result

    Returns:
        PostMortem document
    """
    return PostMortem.from_ooda_result(result)


def save_postmortem(postmortem: PostMortem, output_dir: str = "postmortems") -> str:
    """Save post-mortem to markdown file.

    Args:
        postmortem: Post-mortem document to save
        output_dir: Directory to save post-mortem (default: "postmortems")

    Returns:
        Path to saved post-mortem file

    Raises:
        IOError: If file cannot be written
    """
    pass
```

**Markdown Template (Simple):**

```markdown
# Post-Mortem: [Service] - [Symptom]

**Generated:** [Timestamp]
**Investigation ID:** [UUID]
**Severity:** [Level]
**Status:** [RESOLVED/INCONCLUSIVE]

---

## Summary

**Service:** [service name]
**Symptom:** [description]
**Duration:** [X.X seconds]
**Cost:** $[X.XX]
**Agents:** [N specialist agents]

---

## Root Cause

**Hypothesis:** [Selected hypothesis statement]
**Confidence:** [X]% (initial: [Y]%)
**Source:** [agent_id]

**Reasoning:**
[Agent's reasoning for this hypothesis]

---

## Validation

**Disproof Strategies Applied:**
- ✓ [Strategy 1]: Not disproven
- ✓ [Strategy 2]: Not disproven
- ✓ [Strategy 3]: Not disproven

**Final Confidence:** [X]%

---

## Recommendations

[Based on hypothesis and affected systems]

---

## Investigation Details

**Observations:** [N observations collected]
**Hypotheses Generated:** [N hypotheses]
**Agent Reports:**
- [agent_id]: [confidence score]

---

*Generated by COMPASS v[version] on [timestamp]*
```

**Tests to Write:**
- `test_postmortem_from_ooda_result_with_resolved_investigation()`
- `test_postmortem_from_ooda_result_with_inconclusive_investigation()`
- `test_postmortem_to_markdown_renders_all_fields()`
- `test_postmortem_to_markdown_handles_missing_hypothesis()`
- `test_save_postmortem_creates_file()`
- `test_save_postmortem_creates_directory_if_missing()`

**Why This Approach:**
- Simple dataclass (YAGNI)
- Markdown format (human-readable, version-control friendly)
- Template-based (easy to customize later)
- No database required (just files)

---

### 8.2: Post-mortem Generator

**What to Build:**

The generator is already sketched in 8.1 (`from_ooda_result` and `save_postmortem` functions). Implementation:

```python
@classmethod
def from_ooda_result(cls, result: OODAResult) -> "PostMortem":
    """Create post-mortem from OODA investigation result."""
    investigation = result.investigation

    # Extract selected hypothesis (if any)
    selected_hypothesis = None
    if result.validation_result:
        selected_hypothesis = result.validation_result.hypothesis

    # Calculate duration
    if investigation.completed_at and investigation.created_at:
        duration = (investigation.completed_at - investigation.created_at).total_seconds()
    else:
        duration = 0.0

    return cls(
        investigation_id=str(investigation.investigation_id),
        generated_at=datetime.now(),
        service=investigation.service,
        symptom=investigation.symptom,
        severity=investigation.severity,
        status=investigation.status.value,
        selected_hypothesis=selected_hypothesis,
        validation_result=result.validation_result,
        total_cost=investigation.total_cost,
        duration_seconds=duration,
        agent_count=len(investigation.observations),
    )
```

**Tests to Write:**
- Test with complete investigation (has hypothesis, validation)
- Test with incomplete investigation (no hypothesis)
- Test cost/duration calculations
- Test file writing with various output directories
- Test filename generation (unique, sortable)

**Why This Approach:**
- Extract directly from existing data structures
- No complex logic needed
- Simple transformations only

---

### 8.3: CLI Integration

**What to Build:**

```python
# src/compass/cli/main.py updates

@cli.command()
@click.option("--service", required=True, ...)
@click.option("--symptom", required=True, ...)
@click.option("--severity", required=True, ...)
@click.option(
    "--output-dir",
    default="postmortems",
    help="Directory to save post-mortem (default: postmortems)",
)
@click.option(
    "--skip-postmortem",
    is_flag=True,
    help="Skip post-mortem generation",
)
def investigate(
    service: str,
    symptom: str,
    severity: str,
    output_dir: str,
    skip_postmortem: bool,
) -> None:
    """Trigger a new incident investigation."""

    # ... existing investigation logic ...

    try:
        result = asyncio.run(runner.run(context))
        formatter.show_complete_investigation(result)

        # Generate post-mortem if not skipped
        if not skip_postmortem:
            from compass.core.postmortem import generate_postmortem, save_postmortem

            postmortem = generate_postmortem(result)
            filepath = save_postmortem(postmortem, output_dir)

            click.echo(f"\n📄 Post-mortem saved: {filepath}")
    except KeyboardInterrupt:
        ...
```

**Tests to Write:**
- `test_cli_generates_postmortem_by_default()`
- `test_cli_skips_postmortem_when_flag_set()`
- `test_cli_uses_custom_output_dir()`
- `test_cli_handles_postmortem_write_failure_gracefully()`

**Why This Approach:**
- Automatic by default (users want post-mortems)
- Optional skip for testing
- Configurable output location
- Graceful error handling (don't fail investigation if post-mortem write fails)

---

### 8.4: Demo Documentation

**What to Build:**

Add to DEMO.md:

```markdown
## Post-Mortem Documents

After each investigation, COMPASS automatically generates a post-mortem document.

### Example

```bash
poetry run compass investigate \
  --service payment-service \
  --symptom "high latency" \
  --severity critical

# Output includes:
# 📄 Post-mortem saved: postmortems/payment-service-2025-11-18-140532.md
```

### Post-Mortem Contents

Post-mortems include:
- Investigation summary (service, symptom, severity)
- Root cause hypothesis with confidence score
- Validation results from disproof strategies
- Agent observations and reasoning
- Cost and duration metrics
- Recommendations based on findings

### Configuration

```bash
# Save to custom directory
compass investigate ... --output-dir ./reports

# Skip post-mortem generation
compass investigate ... --skip-postmortem
```

### Example Post-Mortem

See [postmortems/example.md](postmortems/example.md) for a sample post-mortem document.
```

**Why This Approach:**
- Clear examples
- Show output location
- Explain what's included
- Document configuration options

---

## Test Coverage Goals

| Component | Target | Rationale |
|-----------|--------|-----------|
| PostMortem model | 100% | Simple dataclass, full coverage easy |
| Template rendering | 90% | Edge cases (missing data) important |
| File I/O | 80% | Error handling matters |
| CLI integration | 70% | Integration test proves it works |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Markdown format not ideal | Users want different format | Easy to add other renderers later |
| File I/O errors | Post-mortem not saved | Graceful error handling, don't fail investigation |
| Filename collisions | Overwrite existing post-mortems | Use timestamp + UUID in filename |
| Large post-mortems | Files become unwieldy | Keep template simple, essential info only |

---

## Success Criteria

Phase 8 is complete when:
1. ✅ Post-mortem generated automatically after investigation
2. ✅ Post-mortem saved to markdown file
3. ✅ Post-mortem includes all key information (hypothesis, validation, cost)
4. ✅ User can skip post-mortem generation with flag
5. ✅ User can specify output directory
6. ✅ All tests pass (unit + integration)
7. ✅ Type safety verified (mypy --strict)
8. ✅ Demo documentation updated with examples

---

## Out of Scope (Deferred)

**NOT in Phase 8:**
- Investigation history/search (Phase 9 or later)
- Post-mortem templates (just one format for now)
- Post-mortem editing in CLI (users can edit markdown files)
- Attaching artifacts (logs, traces) to post-mortem
- Sharing/collaboration features
- Post-mortem analytics/trends

---

## Timeline Estimate

| Sub-Phase | Estimated Time |
|-----------|----------------|
| 8.1: Data model & template | 2 hours |
| 8.2: Generator | 1 hour |
| 8.3: CLI integration | 2 hours |
| 8.4: Demo docs | 1 hour |
| **Total** | **6 hours** |

---

## Questions for Plan Review

1. Is markdown the right format, or should we support multiple formats?
2. Should post-mortems be saved automatically, or require explicit flag?
3. Is "postmortems/" the right default directory?
4. Should we include raw observation data in post-mortem?
5. Are we missing any critical fields in the post-mortem model?
6. Should filename include investigation ID or just timestamp+service?

---

## Appendix: File Changes Summary

```
Created:
- src/compass/core/postmortem.py (PostMortem model, generator, save function)
- tests/unit/core/test_postmortem.py (unit tests)
- postmortems/example.md (example post-mortem for documentation)

Modified:
- src/compass/cli/main.py (add post-mortem generation after investigation)
- tests/integration/test_cli_integration.py (integration tests)
- DEMO.md (add post-mortem documentation)
- README.md (mention post-mortem feature)

Total: 3 created, 4 modified
```

---

## YAGNI Validation

**What we're building:**
- Simple dataclass for post-mortem
- Single markdown template
- Basic file I/O
- CLI flags for configuration

**What we're NOT building:**
- Multiple format support (YAGNI)
- Database storage (YAGNI)
- Post-mortem search/history (YAGNI)
- Collaborative editing (YAGNI)
- Advanced templates (YAGNI)
- Analytics/trends (YAGNI)

**Justification:** Every feature in this phase directly supports the core value: capturing investigation results for learning and communication. Nothing extra.
