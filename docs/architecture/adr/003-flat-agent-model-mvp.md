# ADR 003: Flat Agent Model for MVP

**Status**: Accepted
**Date**: 2025-11-19
**Deciders**: Ivan (Product Owner), Development Team
**Related**: P0-1 from Comprehensive Code Review

## Context and Problem Statement

The original COMPASS architecture specified a 3-level ICS (Incident Command System) hierarchy for agent coordination:

```
Orchestrator (GPT-4/Opus - expensive, smart)
    ├── Database Manager (GPT-4o-mini/Sonnet - cheaper)
    │   ├── PostgreSQL Worker
    │   ├── MySQL Worker
    │   └── MongoDB Worker
    ├── Network Manager
    │   ├── Routing Worker
    │   ├── DNS Worker
    │   └── Load Balancer Worker
    └── ...
```

However, MVP scope includes only a single domain (database) with one specialist agent. This raises the question:

**Should we implement the full 3-level hierarchy now for architectural consistency, or use a simpler flat model for MVP and add hierarchy later when multiple domains exist?**

## Decision Drivers

- **YAGNI Principle**: Don't build what we don't need yet - single agent doesn't require manager layer
- **Cost**: Manager layer adds LLM API calls without providing value for single domain
- **Simplicity**: Easier to test, debug, and understand flat model during MVP validation
- **Time to Market**: MVP needs to ship quickly to validate core hypothesis
- **Reversibility**: Can add hierarchy later without breaking changes to investigation flow
- **ICS Span of Control**: Principle states 3-7 subordinates per supervisor - with 1 agent, hierarchy is premature
- **User Feedback**: "I hate complexity" and "don't build things we don't need"

## Considered Options

### Option A: Flat Model for MVP, Hierarchy Later (CHOSEN)

**Implementation**:
```
OODAOrchestrator (coordination logic in core/)
    └── DatabaseAgent (direct observation and hypothesis generation)
```

**Pros**:
- Simpler implementation (~200 LOC savings)
- Lower costs (no manager-level LLM calls)
- Faster development velocity (1-2 weeks savings)
- Still validates core COMPASS value propositions:
  - Parallel OODA loops work
  - Scientific method with disproof strategies
  - Quality-weighted evidence scoring
  - Learning Teams culture
  - Cost controls ($10/investigation target)
- Easier to debug and test
- Meets all MVP success criteria

**Cons**:
- Doesn't match documented architecture (requires doc updates)
- Refactoring needed when adding 2nd domain
- ICS hierarchy principles not fully validated in MVP
- Risk of "temporary becomes permanent"

### Option B: Implement Full ICS Hierarchy Now

**Implementation**:
```
OrchestratorAgent (new agent class)
    └── DatabaseManager (new manager agent)
        └── DatabaseAgent (current worker)
```

**Pros**:
- Matches documented architecture
- Ready for multi-domain expansion
- Demonstrates ICS principles fully
- No refactoring needed later
- Clear separation of concerns

**Cons**:
- Adds significant complexity for single agent
- Extra LLM costs (manager layer) with no MVP benefit
- More code to test and maintain (~200-300 extra LOC)
- Delays MVP delivery (1-2 weeks)
- Violates YAGNI and user preference for simplicity
- ICS span of control (3-7 subordinates) violated with 1 worker

### Option C: Hybrid - Code for Hierarchy, Don't Activate

**Implementation**:
```python
# Create interfaces but use passthrough for MVP
class DatabaseManager:
    def coordinate(self, workers):
        if len(workers) == 1:
            return workers[0].observe()  # Passthrough
        else:
            # Real coordination logic
```

**Pros**:
- Architecture in place for future
- Easy to activate when needed
- Documents intended direction

**Cons**:
- Dead code in MVP (complexity without benefit)
- Still requires implementation time
- Creates maintenance burden
- Violates "simplest thing that works"

## Decision Outcome

**Chosen Option**: Option A - Flat agent model for MVP

We will use a flat architecture for MVP with direct orchestrator-to-agent communication. The manager layer will be added when **any** of these conditions are met:

1. **2nd domain added** (Network, Application, Infrastructure, or External)
2. **Specialist count exceeds 7** (ICS span of control limit)
3. **Coordination complexity justifies overhead** (cross-domain dependencies)

## Consequences

### Positive

- **Simpler codebase**: ~1200 LOC core implementation (vs ~1500 with hierarchy)
- **Lower costs during MVP**: Single LLM call per observation instead of orchestrator → manager → worker chain
- **Faster development**: 1-2 weeks saved on manager layer implementation and testing
- **Still validates core hypothesis**: All COMPASS differentiators work without hierarchy
- **Easier debugging**: Flat call stack makes issues easier to trace
- **Better MVP focus**: Team focuses on scientific framework and OODA cycle, not coordination complexity

### Negative

- **Documentation mismatch**: Need to update architecture docs to reflect flat reality
- **Refactoring required**: Adding 2nd domain requires introducing manager layer
- **ICS not fully validated**: Can't prove hierarchy works until Phase 2
- **Risk of premature optimization**: Might add hierarchy too early if not careful

### Neutral

- **Clear migration path**: When to add managers is well-defined (conditions above)
- **Reversible decision**: Can implement hierarchy later without breaking investigation flow
- **Pragmatic compromise**: Balances architectural vision with MVP realities

## Validation

MVP success criteria do **NOT** require manager layer:

| Criterion | Requires Hierarchy? | Status |
|-----------|-------------------|--------|
| Complete investigation cycle in <5 minutes | ❌ No | ✅ Achievable with flat model |
| Generate 3-5 testable hypotheses | ❌ No | ✅ Agent generates directly |
| Attempt to disprove hypotheses | ❌ No | ✅ Validation phase handles this |
| Cost <$10 routine, <$20 critical | ❌ No | ✅ Investigation-level budget enforced |
| Work with LGTM stack | ❌ No | ✅ MCP integration works |
| Learning Teams post-mortems | ❌ No | ✅ Post-mortem generation implemented |

If MVP fails, it won't be because we lacked a manager layer. Core value proposition is in:
- **Scientific method**: Quality-weighted evidence, systematic disproof
- **Human collaboration**: First-class human decisions, Learning Teams culture
- **Cost control**: $10/investigation budget enforcement
- **OODA speed**: Parallel observation, fast hypothesis generation

## Implementation Notes

### Current Architecture (MVP)

```python
# src/compass/core/ooda_orchestrator.py
class OODAOrchestrator:
    def execute(self, investigation, agents, ...):
        # Observe: Coordinate agents directly
        for agent in agents:
            observation = await agent.observe(...)

        # Orient: Generate hypotheses from observations
        hypotheses = [
            await agent.generate_hypotheses(...)
            for agent in agents
        ]

        # Decide: Human selects hypothesis
        selected = decision_interface.decide(...)

        # Act: Validate hypothesis
        result = validator.validate(...)
```

### Future Architecture (Phase 2+)

```python
# When 2nd domain added, introduce managers:
class DatabaseManager(ManagerAgent):
    """Coordinates 3-7 database specialist workers."""
    def coordinate_observation(self, workers: List[DatabaseAgent]):
        # Manager-level coordination logic
        # - Load balancing across workers
        # - Deduplication of queries
        # - Domain-specific optimization

# OODAOrchestrator then coordinates managers:
orchestrator.execute(
    managers=[database_manager, network_manager]  # Not workers!
)
```

### Migration Checklist (When Adding 2nd Domain)

- [ ] Create `ManagerAgent` base class
- [ ] Implement `DatabaseManager` for existing DatabaseAgent
- [ ] Implement `NetworkManager` for new network specialists
- [ ] Update OODAOrchestrator to coordinate managers, not workers
- [ ] Add manager-level cost tracking (cheaper models for managers)
- [ ] Update tests to validate manager coordination
- [ ] Update architecture docs to show hierarchy
- [ ] Validate ICS span of control (3-7 workers per manager)

## References

- **Code Review Findings**:
  - Agent Alpha: review_agent_alpha_findings.md (P1-1, lines 165-210)
  - Agent Beta: review_agent_beta_findings.md (P0-1, lines 40-121)
  - Consolidated Plan: CONSOLIDATED_REVIEW_AND_FIX_PLAN.md

- **Architecture Documents**:
  - COMPASS MVP Architecture Reference: docs/architecture/COMPASS_MVP_Architecture_Reference.md
  - ICS Principles: docs/research/Designing_ICSBased_MultiAgent_AI_Systems...pdf

- **User Guidance**:
  - CLAUDE.md: "I hate complexity" and "don't build things we don't need"
  - Product strategy: Focus on Learning Teams and scientific method differentiation

- **Related ADRs**:
  - ADR 001: Evidence Quality Naming Convention
  - ADR 002: Foundation First Approach (Quality over velocity)

## Revision History

- **2025-11-19**: Initial version - flat model for MVP decision
