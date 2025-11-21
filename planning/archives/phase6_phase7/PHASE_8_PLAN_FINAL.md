# Phase 8 Plan: "Post-mortem Generation" (FINAL)

**Version:** 2.0 (Reviewed & Revised)
**Date:** 2025-11-18
**Status:** APPROVED - Ready for Implementation
**Reviewed by:** Agent Alpha (Senior) & Agent Beta

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
- Post-mortem saved to file (e.g., `postmortems/payment-db-a3b2c1d4-2025-11-18-140532.md`)
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
- Template engines like Jinja2 (f-strings sufficient for MVP)
- Post-mortem customization without code changes (hardcoded for MVP)

---

## Review Agent Findings Incorporated

**Critical fixes from Agent Alpha (Senior Review Agent):**
- ✅ Fixed Investigation data structure access (use `investigation.context.*`)
- ✅ Fixed investigation ID attribute (use `investigation.id` not `investigation_id`)
- ✅ Fixed duration calculation (use `updated_at` not `completed_at`)
- ✅ Fixed agent count calculation (count unique agents, not observations)

**Critical fixes from Agent Beta:**
- ✅ Removed emoji from CLI output (user preference)
- ✅ Added INCONCLUSIVE case handling in template
- ✅ Added investigation ID to filename for uniqueness
- ✅ Added Path handling for mypy --strict compliance
- ✅ Added file I/O edge case tests
- ✅ Specified error handling behavior

---

## Phase Breakdown

### Phase 8.1: Post-mortem Data Model & Template

**TDD Steps:**
1. RED: Write tests for PostMortem dataclass
2. GREEN: Implement PostMortem model with all fields
3. RED: Write tests for markdown template rendering (RESOLVED case)
4. GREEN: Implement markdown template with RESOLVED rendering
5. RED: Write tests for INCONCLUSIVE case rendering
6. GREEN: Add INCONCLUSIVE case handling to template
7. REFACTOR: Ensure type safety with mypy --strict
8. COMMIT: "feat(postmortem): Add post-mortem data model and markdown template"

**Files Changed:**
- `src/compass/core/postmortem.py` (new)
- `tests/unit/core/test_postmortem.py` (new)

**Why:** Need data model and template before generation logic

**YAGNI Check:** ✅ Minimal model with only essential fields, simple markdown template using f-strings

---

### Phase 8.2: Post-mortem Generator

**TDD Steps:**
1. RED: Write tests for PostMortemGenerator.generate() with RESOLVED investigation
2. GREEN: Implement generator that creates PostMortem from OODAResult
3. RED: Write tests for INCONCLUSIVE investigation
4. GREEN: Handle None validation_result case
5. RED: Write tests for file writing (happy path + directory creation)
6. GREEN: Implement save_postmortem() with Path handling
7. RED: Write tests for file I/O edge cases (permissions, disk full, invalid chars)
8. GREEN: Add error handling and filename sanitization
9. REFACTOR: Handle all edge cases gracefully
10. COMMIT: "feat(postmortem): Add post-mortem generator with robust error handling"

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
6. RED: Write test for error handling (post-mortem write fails)
7. GREEN: Add try/except for graceful error handling
8. REFACTOR: Ensure investigation continues even if post-mortem fails
9. COMMIT: "feat(cli): Generate post-mortems after investigations"

**Files Changed:**
- `src/compass/cli/main.py` (extend existing investigate command)
- `tests/integration/test_cli_integration.py` (extend existing file)

**Why:** Make post-mortem generation automatic in CLI flow

**YAGNI Check:** ✅ Simple flags, sensible defaults, optional skip

---

### Phase 8.4: Update Demo Documentation

**NO TDD** (documentation only)

1. Update DEMO.md with post-mortem examples
2. Document post-mortem file location and format
3. Show example post-mortem content inline (defer example.md file creation)
4. COMMIT: "docs: Update demo with post-mortem examples"

**Files Changed:**
- `DEMO.md`
- `README.md` (mention post-mortems)

**Why:** Users need to know about post-mortem output

**YAGNI Check:** ✅ Minimal docs update, inline examples only (no separate example.md file yet)

---

## Detailed Implementation Plan

### 8.1: Post-mortem Data Model & Template

**What to Build:**

```python
# src/compass/core/postmortem.py

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
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

        Handles both RESOLVED (with hypothesis) and INCONCLUSIVE (no hypothesis) cases.

        Returns:
            Markdown-formatted post-mortem document
        """
        # Format timestamp
        timestamp = self.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Header
        md = f"# Post-Mortem: {self.service} - {self.symptom}\n\n"
        md += f"**Generated:** {timestamp}\n"
        md += f"**Investigation ID:** {self.investigation_id}\n"
        md += f"**Severity:** {self.severity}\n"
        md += f"**Status:** {self.status}\n\n"
        md += "---\n\n"

        # Summary
        md += "## Summary\n\n"
        md += f"**Service:** {self.service}\n"
        md += f"**Symptom:** {self.symptom}\n"
        md += f"**Duration:** {self.duration_seconds:.1f} seconds\n"
        md += f"**Cost:** ${self.total_cost:.4f}\n"
        md += f"**Agents:** {self.agent_count} specialist agent(s)\n\n"
        md += "---\n\n"

        # Root Cause (conditional on status)
        md += "## Root Cause\n\n"
        if self.selected_hypothesis and self.validation_result:
            md += f"**Hypothesis:** {self.selected_hypothesis.statement}\n"
            md += f"**Confidence:** {self.validation_result.final_confidence:.0%} "
            md += f"(initial: {self.selected_hypothesis.initial_confidence:.0%})\n"
            md += f"**Source:** {self.selected_hypothesis.source_agent_id}\n\n"
            md += "**Reasoning:**\n"
            md += f"{self.selected_hypothesis.reasoning}\n\n"
        else:
            md += "**Status:** INCONCLUSIVE - No hypotheses could be validated\n\n"
            md += "The investigation did not identify a root cause with sufficient confidence. "
            md += "This may indicate:\n"
            md += "- Insufficient observability data available\n"
            md += "- Symptoms resolved before investigation completed\n"
            md += "- Root cause requires additional specialist agents\n\n"

        md += "---\n\n"

        # Validation (only if hypothesis was validated)
        if self.validation_result:
            md += "## Validation\n\n"
            md += "**Disproof Strategies Applied:**\n"
            for strategy in self.validation_result.strategies_applied:
                md += f"- ✓ {strategy}: Not disproven\n"
            md += f"\n**Final Confidence:** {self.validation_result.final_confidence:.0%}\n\n"
            md += "---\n\n"

        # Recommendations (only if we have a hypothesis)
        if self.selected_hypothesis:
            md += "## Recommendations\n\n"
            md += "Based on validated hypothesis and affected systems:\n"
            for system in self.selected_hypothesis.affected_systems:
                md += f"- Review and remediate {system}\n"
            md += "\n---\n\n"

        # Footer
        md += "*Generated by COMPASS on " + timestamp + "*\n"

        return md

    @classmethod
    def from_ooda_result(cls, result: OODAResult) -> "PostMortem":
        """Create post-mortem from OODA investigation result.

        Args:
            result: Completed OODA investigation result

        Returns:
            PostMortem instance
        """
        investigation = result.investigation

        # Extract selected hypothesis (if any)
        selected_hypothesis = None
        if result.validation_result:
            selected_hypothesis = result.validation_result.hypothesis

        # Calculate duration using updated_at (not completed_at which doesn't exist)
        if investigation.updated_at and investigation.created_at:
            duration = (investigation.updated_at - investigation.created_at).total_seconds()
        else:
            duration = 0.0

        # Calculate unique agent count from observations
        # Each observation dict has 'agent_id' key
        unique_agents = set(
            obs.get('agent_id')
            for obs in investigation.observations
            if isinstance(obs, dict) and 'agent_id' in obs
        )
        agent_count = len(unique_agents) if unique_agents else 0

        return cls(
            # Use investigation.id not investigation.investigation_id
            investigation_id=str(investigation.id),
            generated_at=datetime.now(timezone.utc),
            # Access service/symptom/severity via context, not direct attributes
            service=investigation.context.service,
            symptom=investigation.context.symptom,
            severity=investigation.context.severity,
            status=investigation.status.value,
            selected_hypothesis=selected_hypothesis,
            validation_result=result.validation_result,
            total_cost=investigation.total_cost,
            duration_seconds=duration,
            agent_count=agent_count,
        )


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

    Uses pathlib.Path for type-safe file operations (mypy --strict compliant).
    Includes investigation ID in filename to prevent collisions.

    Args:
        postmortem: Post-mortem document to save
        output_dir: Directory to save post-mortem (default: "postmortems")

    Returns:
        Absolute path to saved post-mortem file (as string)

    Raises:
        IOError: If file cannot be written (permissions, disk full, etc.)
    """
    # Convert to Path for type safety
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Sanitize service name for filename (replace invalid characters)
    safe_service = "".join(
        c if c.isalnum() or c in ('-', '_') else '_'
        for c in postmortem.service
    )

    # Generate filename with investigation ID for uniqueness
    timestamp = postmortem.generated_at.strftime("%Y-%m-%d-%H%M%S")
    short_id = postmortem.investigation_id[:8]  # First 8 chars of UUID
    filename = f"{safe_service}-{short_id}-{timestamp}.md"
    filepath = output_path / filename

    # Write file with explicit encoding
    try:
        filepath.write_text(postmortem.to_markdown(), encoding="utf-8")
    except OSError as e:
        raise IOError(
            f"Failed to write post-mortem to {filepath}: {e}"
        ) from e

    return str(filepath.absolute())
```

**Tests to Write:**
- `test_postmortem_from_ooda_result_with_resolved_investigation()`
- `test_postmortem_from_ooda_result_with_inconclusive_investigation()`
- `test_postmortem_to_markdown_renders_all_fields_resolved()`
- `test_postmortem_to_markdown_renders_inconclusive_case()`
- `test_postmortem_to_markdown_handles_missing_hypothesis()`
- `test_save_postmortem_creates_file()`
- `test_save_postmortem_creates_directory_if_missing()`
- `test_save_postmortem_handles_write_permission_error()`
- `test_save_postmortem_handles_disk_full_error()` (mock OSError)
- `test_save_postmortem_sanitizes_service_name_for_filename()`
- `test_save_postmortem_includes_investigation_id_in_filename()`
- `test_postmortem_calculates_unique_agent_count()`
- `test_postmortem_uses_investigation_context_fields()`

**Why This Approach:**
- Simple dataclass (YAGNI)
- Markdown format (human-readable, version-control friendly)
- F-string template (no dependencies, simple to maintain)
- No database required (just files)
- Explicit INCONCLUSIVE handling (user feedback shows this is common)
- Path-based I/O for type safety

---

### 8.2: Post-mortem Generator

**What to Build:**

Implementation already included in 8.1 above (`from_ooda_result` and `save_postmortem` functions).

**Key Implementation Details:**
1. **Duration calculation:** Use `investigation.updated_at` not `completed_at` (doesn't exist)
2. **Investigation ID:** Use `investigation.id` not `investigation.investigation_id`
3. **Context fields:** Access `investigation.context.service/symptom/severity`
4. **Agent count:** Calculate unique agents from observations, don't just count observations
5. **Filename:** Include investigation ID (first 8 chars) for uniqueness
6. **Sanitization:** Replace invalid filename characters in service name
7. **Type safety:** Use `Path` from pathlib for mypy --strict compliance

**Tests to Write:**
All tests listed in 8.1 above (combined into single phase)

**Why This Approach:**
- Extract directly from existing data structures
- No complex logic needed
- Simple transformations only
- Robust error handling for file I/O

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
    """Trigger a new incident investigation.

    This command starts a new OODA loop investigation for the specified service
    and symptom. The investigation will collect observations, generate hypotheses,
    prompt for human decision, and validate the selected hypothesis.

    After completion, a post-mortem document is automatically generated
    (unless --skip-postmortem is specified).

    Example:
        compass investigate --service api-backend \\
                          --symptom "500 errors spiking" \\
                          --severity high
    """
    # Create investigation context
    context = InvestigationContext(
        service=service,
        symptom=symptom,
        severity=severity,
    )

    # Try to create LLM provider and DatabaseAgent
    agents = []
    llm_provider = None

    try:
        # Attempt to create LLM provider from settings
        llm_provider = create_llm_provider_from_settings()

        # Select budget based on severity
        if severity.lower() == "critical":
            budget_limit = settings.critical_cost_budget_usd
        else:
            budget_limit = settings.default_cost_budget_usd

        # Create DatabaseAgent with LLM provider
        db_agent = create_database_agent(
            llm_provider=llm_provider,
            budget_limit=budget_limit,
        )
        agents.append(db_agent)

        logger.info(
            "cli.agent.created",
            agent_id=db_agent.agent_id,
            budget_limit=budget_limit,
            severity=severity,
        )

    except ValidationError as e:
        # LLM provider configuration error (missing/invalid API key)
        click.echo(f"⚠️  {e}", err=True)
        click.echo(
            "   Continuing without LLM provider (investigation will be INCONCLUSIVE)\n",
            err=True,
        )
        logger.warning("cli.no_llm_provider", reason=str(e))

    except ValueError as e:
        # Unsupported provider configuration
        click.echo(f"⚠️  {e}", err=True)
        click.echo(
            "   Continuing without LLM provider (investigation will be INCONCLUSIVE)\n",
            err=True,
        )
        logger.warning("cli.invalid_provider", reason=str(e))

    # Create disproof strategies for validation
    strategies = [
        "temporal_contradiction",
        "scope_verification",
        "correlation_vs_causation",
    ]

    # Create runner with agents and strategies
    runner = create_investigation_runner(
        agents=agents,
        strategies=strategies,
    )
    formatter = DisplayFormatter()

    # Run investigation asynchronously with error handling
    try:
        result = asyncio.run(runner.run(context))
        formatter.show_complete_investigation(result)

        # Generate post-mortem if not skipped
        # NOTE: Always generate post-mortem, even for INCONCLUSIVE investigations
        # Template handles missing hypothesis gracefully
        if not skip_postmortem:
            try:
                from compass.core.postmortem import generate_postmortem, save_postmortem

                postmortem = generate_postmortem(result)
                filepath = save_postmortem(postmortem, output_dir)

                # Plain text output (no emoji per user preference)
                click.echo(f"\nPost-mortem saved to: {filepath}")
            except IOError as e:
                # Don't fail investigation over post-mortem save failure
                click.echo(
                    f"\nWarning: Could not save post-mortem: {e}",
                    err=True,
                )
                click.echo(
                    "Investigation completed successfully but post-mortem not saved.",
                    err=True,
                )
                logger.warning("cli.postmortem.save_failed", error=str(e))

    except KeyboardInterrupt:
        click.echo("\n\nInvestigation cancelled by user.", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\n\nInvestigation failed: {e}", err=True)
        logger.exception("investigation.failed", error=str(e))
        sys.exit(1)
```

**Tests to Write:**
- `test_cli_generates_postmortem_by_default()` (extend test_cli_integration.py)
- `test_cli_generates_postmortem_for_inconclusive_investigation()`
- `test_cli_skips_postmortem_when_flag_set()`
- `test_cli_uses_custom_output_dir()`
- `test_cli_handles_postmortem_write_failure_gracefully()`
- `test_cli_continues_investigation_if_postmortem_fails()`

**Why This Approach:**
- Automatic by default (users want post-mortems)
- Handles both RESOLVED and INCONCLUSIVE investigations
- Optional skip for testing
- Configurable output location
- Graceful error handling (don't fail investigation if post-mortem write fails)
- No emoji in output (per user preference)
- Clear error messages following existing patterns

---

### 8.4: Demo Documentation

**What to Build:**

Add to DEMO.md:

```markdown
## Post-Mortem Documents

After each investigation, COMPASS automatically generates a post-mortem document in markdown format.

### Example

```bash
poetry run compass investigate \
  --service payment-service \
  --symptom "high latency" \
  --severity critical

# Output includes:
# Post-mortem saved to: postmortems/payment-service-a3b2c1d4-2025-11-18-140532.md
```

### Post-Mortem Contents

Post-mortems include:
- Investigation summary (service, symptom, severity, duration, cost)
- Root cause hypothesis with confidence score (for RESOLVED investigations)
- Explanation of INCONCLUSIVE status (when no hypothesis validated)
- Validation results from disproof strategies
- Agent observations and reasoning
- Recommendations based on affected systems

### Configuration

```bash
# Save to custom directory
compass investigate ... --output-dir ./reports

# Skip post-mortem generation (for testing)
compass investigate ... --skip-postmortem
```

### Example Post-Mortem (RESOLVED)

```markdown
# Post-Mortem: payment-service - high latency

**Generated:** 2025-11-18 14:05:32 UTC
**Investigation ID:** a3b2c1d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d
**Severity:** critical
**Status:** RESOLVED

---

## Summary

**Service:** payment-service
**Symptom:** high latency
**Duration:** 8.2 seconds
**Cost:** $0.2547
**Agents:** 1 specialist agent(s)

---

## Root Cause

**Hypothesis:** Database connection pool exhausted
**Confidence:** 85% (initial: 75%)
**Source:** database_specialist

**Reasoning:**
Metrics show connection pool utilization at 100% during incident window.
Query latency correlates with pool exhaustion events.

---

## Validation

**Disproof Strategies Applied:**
- ✓ temporal_contradiction: Not disproven
- ✓ scope_verification: Not disproven
- ✓ correlation_vs_causation: Not disproven

**Final Confidence:** 85%

---

## Recommendations

Based on validated hypothesis and affected systems:
- Review and remediate payment-db

---

*Generated by COMPASS on 2025-11-18 14:05:32 UTC*
```
```

Update README.md to mention post-mortems:

```markdown
## Features

- **OODA Loop Investigation:** Observe, Orient, Decide, Act methodology
- **Scientific Hypothesis Testing:** Generate and validate hypotheses via disproof
- **LLM-Powered Analysis:** OpenAI and Anthropic provider support
- **Automatic Post-Mortems:** Generate markdown documentation for every investigation
- **Cost-Aware:** Budget limits per investigation severity level
- **Type-Safe:** Full mypy --strict compliance
```

**Why This Approach:**
- Clear examples for both RESOLVED and INCONCLUSIVE cases
- Show actual output format
- Document configuration options
- Inline examples (defer creating separate example.md file - YAGNI)

---

## Test Coverage Goals

| Component | Target | Rationale |
|-----------|--------|-----------|
| PostMortem model | 100% | Simple dataclass, full coverage achievable |
| Template rendering | 95% | Edge cases (INCONCLUSIVE, missing data) critical |
| File I/O | 85% | Error handling important (permissions, disk full) |
| CLI integration | 75% | Integration tests prove it works |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Markdown format not ideal | Users want different format | Easy to add other renderers later |
| File I/O errors | Post-mortem not saved | Graceful error handling, don't fail investigation |
| Filename collisions | Overwrite existing post-mortems | Include investigation ID (first 8 chars) in filename |
| Large post-mortems | Files become unwieldy | Keep template simple, essential info only |
| Invalid chars in service name | Filename creation fails | Sanitize service name (replace invalid chars with _) |

---

## Success Criteria

Phase 8 is complete when:
1. ✅ Post-mortem generated automatically after investigation (RESOLVED and INCONCLUSIVE)
2. ✅ Post-mortem saved to markdown file with unique filename
3. ✅ Post-mortem includes all key information (hypothesis, validation, cost)
4. ✅ User can skip post-mortem generation with --skip-postmortem flag
5. ✅ User can specify output directory with --output-dir
6. ✅ All tests pass (unit + integration, 85%+ coverage)
7. ✅ Type safety verified (mypy --strict passes)
8. ✅ Demo documentation updated with RESOLVED and INCONCLUSIVE examples
9. ✅ File I/O errors handled gracefully (investigation doesn't fail)
10. ✅ No emoji in CLI output (per user preference)

---

## Out of Scope (Deferred)

**NOT in Phase 8:**
- Investigation history/search (Phase 9 or later)
- Multiple post-mortem templates/formats (just one format for now)
- Template customization without code changes (f-strings hardcoded for MVP)
- Post-mortem editing in CLI (users can edit markdown files directly)
- Attaching artifacts (logs, traces) to post-mortem
- Sharing/collaboration features
- Post-mortem analytics/trends
- Template engines (Jinja2, etc.) - f-strings sufficient for MVP
- Separate example.md file - inline examples in DEMO.md sufficient

---

## Timeline Estimate

| Sub-Phase | Estimated Time | Notes |
|-----------|----------------|-------|
| 8.1: Data model & template | 2.5 hours | Includes INCONCLUSIVE handling, edge cases |
| 8.2: Generator | 1.5 hours | Robust error handling, Path type safety |
| 8.3: CLI integration | 2.5 hours | Integration tests, error scenarios |
| 8.4: Demo docs | 1.0 hour | Inline examples only |
| **Total** | **7.5 hours** | Buffer for review findings |

---

## Questions for Plan Review - ANSWERED

1. **Is markdown the right format?** → YES. Human-readable, version-control friendly, no dependencies
2. **Should post-mortems be saved automatically?** → YES, with --skip-postmortem opt-out
3. **Is "postmortems/" the right default directory?** → YES, matches "logs/", "reports/" pattern
4. **Should we include raw observation data?** → NO, too verbose. Use investigation ID to correlate if needed.
5. **Are we missing any critical fields?** → NO (after fixes). Using investigation.context.*, investigation.id, investigation.updated_at
6. **Should filename include investigation ID?** → YES, first 8 chars for uniqueness and traceability

---

## Appendix: File Changes Summary

```
Created:
- src/compass/core/postmortem.py (PostMortem model, generator, save function)
- tests/unit/core/test_postmortem.py (comprehensive unit tests)
- PHASE_8_PLAN_FINAL.md (this document)

Modified:
- src/compass/cli/main.py (add post-mortem generation after investigation)
- tests/integration/test_cli_integration.py (add post-mortem integration tests)
- DEMO.md (add post-mortem documentation with examples)
- README.md (mention post-mortem feature)

Total: 3 created, 4 modified
```

---

## YAGNI Validation

**What we're building:**
- Simple dataclass for post-mortem
- Single markdown template using f-strings
- Basic file I/O with pathlib.Path
- CLI flags for configuration
- INCONCLUSIVE case handling (proven necessary by Phase 7)
- Investigation ID in filename (prevents collisions)
- Filename sanitization (handles real-world service names)

**What we're NOT building:**
- Multiple format support (YAGNI - markdown works for MVP)
- Database storage (YAGNI - files are sufficient)
- Post-mortem search/history (YAGNI - defer to Phase 9+)
- Collaborative editing (YAGNI - users can share files via git)
- Advanced templates (YAGNI - f-strings sufficient)
- Template engines (YAGNI - no need for Jinja2 yet)
- Analytics/trends (YAGNI - defer until we have data)
- Version field (YAGNI - git commit shows COMPASS version if needed)
- Separate example.md file (YAGNI - inline examples sufficient)

**Justification:** Every feature in this phase directly supports the core value: capturing investigation results for learning and communication. Edge cases like INCONCLUSIVE, file I/O errors, and filename collisions are addressed because they're proven risks, not speculative. Nothing extra.

---

## Review Agent Acknowledgments

**Agent Alpha (Senior Review Agent):** Promoted for finding critical architectural issues
- Found Investigation.context.* access requirement
- Found investigation.id vs investigation_id mismatch
- Found completed_at vs updated_at issue
- Found agent_count calculation bug

**Agent Beta:** Excellent work on user experience and edge cases
- Found emoji usage violation
- Found INCONCLUSIVE case gap
- Found file I/O edge case gaps
- Found Path type safety requirement

Both agents contributed to a significantly improved plan. Thank you! 🏆
