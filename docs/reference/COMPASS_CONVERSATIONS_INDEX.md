# COMPASS Project - Conversation Index & Reference Guide

**Purpose**: Quick reference to locate information from all planning conversations
**Last Updated**: 2025-11-16
**Total Conversations**: 12

---

## How to Use This Index

1. **Search by topic** using Cmd+F / Ctrl+F
2. **Each topic** lists which conversation files contain relevant information
3. **File paths** point to `chats_split/` directory for easy access
4. **Key quotes** help you verify you've found the right information

---

## Table of Contents

- [Core Architecture & Concepts](#core-architecture--concepts)
- [Multi-Agent System Design](#multi-agent-system-design)
- [OODA Loop Implementation](#ooda-loop-implementation)
- [Scientific Methodology](#scientific-methodology)
- [Human-AI Collaboration](#human-ai-collaboration)
- [CLI & Interface Design](#cli--interface-design)
- [Enterprise Features](#enterprise-features)
- [Knowledge Integration](#knowledge-integration)
- [Learning Culture & Post-Mortems](#learning-culture--post-mortems)
- [Production & Deployment](#production--deployment)
- [Cost Management](#cost-management)
- [MCP Integration](#mcp-integration)
- [Product Strategy](#product-strategy)

---

## Core Architecture & Concepts

### COMPASS Overview
**What it is**: AI-powered incident investigation platform reducing MTTR by 67-90% using parallel OODA loops and ICS principles

**Key Files**:
- `Building COMPASS_ project foundation and architecture - Claude/` (parts 1-4)
- `Building the ultimate SRE investigation tool - Claude/` (parts 1-3)
- `COMPASS_Product_Reference_Document_v1_1.md`

**Key Concepts**:
- Parallel OODA loops as core differentiator
- ICS (Incident Command System) organizational principles
- Scientific methodology with hypothesis falsification
- Learning Teams vs Root Cause Analysis

---

### Technology Stack Decisions

**Backend**: Python only (readability over polyglot complexity)
**Database**: PostgreSQL + pgvector (no vendor lock-in)
**Observability**: LGTM stack initially (Loki, Grafana, Tempo, Mimir)
**Deployment**: Kubernetes required, Tilt for local dev
**LLM**: Provider agnostic (OpenAI, Anthropic, Copilot, Ollama)

**Key Files**:
- `Enterprise tool feasibility and architect review - Claude/` (parts 1-7)
- `COMPASS_MVP_Technical_Design.md`

**Key Quote**:
> "Python only. Engineers can read it. If you need Go performance later, rewrite the hot path. Don't start with microservices in 3 languages."

---

## Multi-Agent System Design

### Agent Hierarchy & Coordination

**Structure**:
- Orchestrator → Manager Agents → Worker Agents
- Span of control: 3-7 subordinates maximum
- Circuit breakers prevent cascade failures

**Key Files**:
- `Multi-agent coordination and knowledge integration - Claude/` (parts 1-5)
- `Agent behavior refinement and performance tracking - Claude/` (parts 1-5)
- `Designing_ICSBased_MultiAgent_AI_Systems_for_Incident_Investigation.pdf`

**Coordination Patterns**:
1. Hierarchical (ICS command chain)
2. Blackboard (shared workspace)
3. Market-based (task bidding)

**Key Implementation**:
- Agent types: Database, Network, Application, Infrastructure, Kubernetes
- Communication via message bus with request-response patterns
- Failure detection with circuit breakers and alternative agent selection

---

### Agent Types & Specialization

**Database Agent**: Query patterns, connection pools, deadlocks, slow queries
**Network Agent**: Routing, latency, packet loss, DNS
**Application Agent**: Code behavior, deployments, feature flags
**Infrastructure Agent**: CPU, memory, disk, node health
**Kubernetes Agent**: Pods, nodes, resources, configurations

**Key Files**:
- `compass_database_agent.py`
- `compass_agent_template.py`
- `Multi-agent coordination and knowledge integration - Claude/` (part 2-3)

---

## OODA Loop Implementation

### Four Phases

**1. Observe**: Parallel data gathering from multiple sources
**2. Orient**: Hypothesis generation and ranking
**3. Decide**: Human decision points with captured reasoning
**4. Act**: Evidence gathering and hypothesis testing

**Key Files**:
- `Handling disproven hypotheses in OODA loops - Claude/` (parts 1-8)
- `MVP to enterprise architecture roadmap - Claude/` (parts 1-6)

**Key Design Decision**:
> "Optimize for iteration speed over perfect analysis. Parallelize observation phase with concurrent agent execution."

---

### Hypothesis Management

**States**: GENERATED → TESTING → SUPPORTED → PROVEN / DISPROVEN / INCONCLUSIVE

**Confidence Scoring**:
- Evidence quality weighting (HIGH=1.0, MEDIUM=0.7, LOW=0.4, SUGGESTIVE=0.2, WEAK=0.1)
- Surviving disproof attempts increases confidence
- Multiple supporting evidence sources strengthen hypotheses

**Key Files**:
- `Agent hypothesis validation through falsification - Claude/` (parts 1-3)
- `compass_scientific_framework.py`
- `Handling disproven hypotheses in OODA loops - Claude/` (parts 3-5)

**Disproof Strategies**:
1. Temporal contradiction (timeline doesn't match)
2. Scope contradiction (wrong scale)
3. Correlation testing (metrics don't correlate)
4. Similar incident comparison
5. Metric threshold validation
6. Dependency analysis
7. Alternative explanation testing
8. Baseline comparison

---

## Scientific Methodology

### Core Principles

1. Every action must have stated purpose and expected outcome
2. Every hypothesis must be testable and falsifiable
3. Every conclusion must be traceable to evidence
4. Every investigation step must be auditable
5. Uncertainty must be quantified, not hidden

**Key Files**:
- `Agent hypothesis validation through falsification - Claude/` (all parts)
- `COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md`
- `compass_scientific_framework.py`

**Key Innovation**:
> "Don't just generate hypotheses—systematically try to DISPROVE them before presenting to humans. This is Popper's scientific method at scale."

---

### Evidence Quality Ratings

**HIGH**: Primary source, directly observed (weight: 1.0)
**MEDIUM**: Confirmed by multiple sources (weight: 0.7)
**LOW**: Inferred from related data (weight: 0.4)
**SUGGESTIVE**: Suggestive but not conclusive (weight: 0.2)
**WEAK**: Single source, uncorroborated (weight: 0.1)

**Key Files**:
- `compass_scientific_framework.py` (lines 40-48)
- `test_scientific_framework.py`

---

## Human-AI Collaboration

### Human Decisions as First-Class Citizens

**Philosophy**: Humans decide, AI advises and accelerates. Every human decision is captured with full context and reasoning.

**Decision Types**:
- HYPOTHESIS_SELECTION: Which hypothesis to pursue
- HYPOTHESIS_REJECTION: Reject AI suggestion
- DATA_REQUEST: Request external data
- INVESTIGATION_DIRECTION: Change investigation strategy
- AI_DISAGREEMENT: Explicitly disagree with AI
- ESCALATION: Escalate to senior engineer

**Key Files**:
- `Handling disproven hypotheses in OODA loops - Claude/` (parts 2-4)
- `Designing CLI interactions for agent-human collaboration - Claude/` (all parts)

**Key Principle**:
> "NEVER call human decisions 'wrong' - call them 'different paths' or 'unexpected outcomes'. Focus on SYSTEM factors, not individual failure."

---

### Blameless Post-Mortems

**Approach**: When human's hypothesis is disproven, analyze SYSTEM factors:
- Incomplete observability
- Misleading metrics
- Time pressure / incident severity
- Ambiguous symptoms
- Multiple root causes
- Documentation gaps
- Pattern matching to similar incidents

**Key Files**:
- `Handling disproven hypotheses in OODA loops - Claude/` (part 3, lines 44-204)
- `Agent-driven post mortem documentation design - Claude/` (parts 1-2)

**Outcome Types** (neutral language):
- HYPOTHESIS_SUPPORTED
- HYPOTHESIS_DISPROVEN
- PARTIALLY_CORRECT
- INCONCLUSIVE
- NOT: "WRONG", "INCORRECT", "FAILED", "MISTAKE"

---

## CLI & Interface Design

### Three Interface Approaches Evaluated

**Option 1: Natural Language First with Progressive Enhancement** ⭐ SELECTED
- Zero learning curve - anyone can start immediately
- Conversational format promotes psychological safety
- Power users can use structured commands when needed

**Option 2: Visual Investigation Canvas with CLI Companion**
- Web-based visual investigation map
- Multiple interaction methods

**Option 3: Adaptive Conversational Agent**
- Dynamically adjusts to user expertise and incident urgency

**Key Files**:
- `Designing CLI interactions for agent-human collaboration - Claude/` (parts 1-5)
- `COMPASS_Interface_Architecture.md`

**Key Decision**:
> "Start with Natural Language First (Option 1), evolve to Adaptive Agent (Option 3) as enhancement. Immediate accessibility + scientific rigor + learning culture."

---

### User Interaction Modes

**MINIMAL**: Critical incident, experienced user - terse, action-focused
**STANDARD**: Regular investigation - balanced detail
**LEARNING**: New user or training mode - educational, verbose
**DETAILED**: Power user wants full information

**Example Interactions**:

```bash
# Minimal mode (expert during P1)
$ compass investigate payment-service --urgent
→ 3 hypotheses. Top: Feature flag 'new-checkout' (78%). Fix: rollback? [y/n/details]

# Learning mode (new user)
$ compass investigate payment-service
→ I'll help you investigate. Here's what I'm doing:
   1. Observing: Gathering metrics, logs, recent changes
   2. Hypothesizing: Forming theories...
   Would you like me to:
   a) Explain what I'm seeing in detail
   b) Just show me the most likely cause
   c) Teach me how to investigate this myself
```

**Key Files**:
- `COMPASS_Interface_Architecture.md` (section 4.2)
- `Designing CLI interactions for agent-human collaboration - Claude/` (part 3)

---

## Enterprise Features

### Enterprise Knowledge Integration

**Purpose**: Allow domain experts to inject operational knowledge through declarative YAML configs

**Key Files**:
- `Agent behavior refinement and performance tracking - Claude/` (parts 1-5)
- `COMPASS_Enterprise_Knowledge_Architecture.md`
- `compass_enterprise_knowledge_guide.md`

**Configuration Hierarchy**:
```
Global (company-wide)
  ↓
Team (shared within tribe)
  ↓
Service (service-specific)
  ↓
Instance (testing overrides)
```

**Example Configuration**:
```yaml
service: payment-service
team: payments-platform
noise_patterns:
  - pattern: "Connection timeout on redis.*during deployment"
    reason: "Normal during rolling restarts"
    confidence: 0.95

known_issues:
  - name: "Monday morning load spike"
    symptoms:
      - "CPU > 80%"
      - "Response time > 500ms"
    time_pattern: "Mon 08:00-09:00 UTC"
    root_cause: "Batch job overlap"
```

**Key Innovation**:
> "Engineers encode their tribal knowledge in simple YAML files. No ML expertise required. Git-based version control with PR review workflow."

---

### Multi-Tenancy & Tribal Boundaries

**Knowledge Isolation**:
- Platform Tribe knowledge != Product Tribe knowledge
- Tribal boundaries are sacred
- Knowledge flows UP for learning, DOWN for context

**Security**:
- Row-level security for multi-tenant isolation
- RBAC with tribal boundaries
- Complete audit logging
- BYOK (Bring Your Own Keys) for enterprise security

**Key Files**:
- `Enterprise tool feasibility and architect review - Claude/` (parts 3-7)
- `COMPASS_Enterprise_Knowledge_Architecture.md` (section 4)

---

## Knowledge Integration

### External Knowledge Sources

**Supported Integrations**:
- **GitHub**: Code, issues, PRs, workflows
- **Confluence**: Documentation, runbooks
- **Slack**: Team communications, incident history
- **PagerDuty**: Alert history, escalation patterns
- **Grafana**: Dashboard definitions, annotations
- **Splunk**: Log patterns, saved searches
- **Datadog**: Monitor definitions, SLO configs
- **Web**: External documentation

**Key Files**:
- `Multi-agent coordination and knowledge integration - Claude/` (parts 1-5)
- `investigation_learning_human_collaboration_architecture.md`

**Caching Strategy**:
- L1: In-memory cache (hot configs, <1ms)
- L2: Redis cache (warm data, <10ms)
- L3: PostgreSQL (cold storage, <100ms)
- Vector embeddings for semantic search

---

### Pattern Learning System

**Pattern Recognition**:
- Extracts patterns from completed incidents
- Matches existing patterns vs creates new ones
- Confidence scoring based on validation
- Active learning queue for human validation

**Pattern Structure**:
```python
{
  "pattern_type": "database_connection_pool_exhaustion",
  "symptoms": ["timeout errors", "connection refused"],
  "metric_patterns": {"db_connections": "> 95%"},
  "log_patterns": ["pool exhausted", "max connections reached"],
  "historical_causes": ["missing connection.close()", "leaked connections"],
  "successful_remediations": ["restart service", "increase pool size"],
  "confidence_score": 0.87,
  "occurrence_count": 23,
  "false_positive_rate": 0.04
}
```

**Key Files**:
- `Multi-agent coordination and knowledge integration - Claude/` (part 2-3)
- `Agent behavior refinement and performance tracking - Claude/` (all parts)

---

## Learning Culture & Post-Mortems

### Learning Teams vs Root Cause Analysis

**Research Findings**:
- Learning Teams generate **114% more improvement actions** (7.5 vs 3.5)
- **57% system-focused actions** vs 30% for RCA
- Involves ALL relevant staff, not just those in the incident
- Asks "What made sense at the time?" not "Why did you err?"

**Key Files**:
- `Agent-driven post mortem documentation design - Claude/` (parts 1-2)
- `Evaluation_of_Learning_Teams_Versus_Root_Cause.pdf`
- `Oct23LVI008TheProblemwithRootCauseAnalysis.pdf`

**Problems with RCA**:
- Promotes flawed reductionist view (single root cause)
- Only 45-70% of RCA recommendations ever implemented
- Creates blame culture
- Organizational forgetting - recurring incidents
- Poor feedback loops

---

### Post-Mortem Structure

**New Structure** (Learning Culture Focus):
1. **Timeline of Events**: What happened chronologically
2. **Normal Work Description**: How work actually happens vs procedures
3. **Contributing Causes Map**: Factors across all system levels
4. **Investigation Journey**: ALL paths explored (including disproved)
5. **System Vulnerabilities**: How factors combined to breach safety
6. **Pattern Recognition**: Links to similar incidents
7. **Improvement Actions**: Hierarchy of effectiveness
8. **Questions for Reflection**: Promoting continued team learning

**Key Files**:
- `AI_PostMortem_Learning_Culture_COMPASS.pdf`
- `Agent-driven post mortem documentation design - Claude/` (parts 1-2)

**Systems Levels for Analysis**:
- Government/Regulatory
- Organization/Management
- Physical Environment
- Human-System Interface
- Equipment & Technology

Each level contains contributing factors that interact to create incident conditions.

---

### Automated Post-Mortem Generation

**AI Capabilities**:
- Reduce post-mortem creation time by 67-90%
- Automatically collect events, metrics, metadata throughout incident
- Reconstruct timeline from multiple sources
- Highlight key decisions and actions
- Identify patterns across incidents

**Key Features**:
- Shows ALL hypotheses (proved AND disproved)
- Distinguishes human vs AI investigations
- Captures reasoning for all decisions
- Creates complete audit trail
- Links to similar past incidents

**Key Files**:
- `AI_PostMortem_Generation_COMPASS.pdf`
- `AI_PostMortem_Learning_Culture_COMPASS.pdf`

---

## Production & Deployment

### Deployment Strategy

**Phase 1: Local Development** (Months 1-6)
- Engineer runs locally with Ollama or personal API keys
- Tilt for local Kubernetes development
- 30-minute setup to value

**Phase 2: Team Deployment** (Months 6-12)
- Team's Kubernetes namespace
- Shared team knowledge base
- Team license model

**Phase 3: Shadow Mode** (Year 2)
- Parallel non-impacting runs
- Validation before full production
- Compare with production results

**Phase 4: Enterprise Platform** (Year 2+)
- Centralized with federation
- Hub and spoke architecture
- Global patterns + tribal boundaries

**Key Files**:
- `Building production systems with Claude code - Claude/` (parts 1-4)
- `Enterprise tool feasibility and architect review - Claude/` (parts 3-7)
- `MVP to enterprise architecture roadmap - Claude/` (all parts)

---

### Infrastructure

**Kubernetes Components**:
- Orchestrator deployment (m6i.xlarge nodes)
- Worker pool (m6i.large nodes)
- Redis for state management (ElastiCache with multi-AZ)
- S3 for artifact storage (encrypted)
- DynamoDB for pattern storage

**Monitoring**:
- OpenTelemetry tracing for all agent interactions
- Prometheus metrics collection
- Grafana dashboards
- Custom metrics: hypothesis accuracy, cost per investigation, MTTR reduction

**Key Files**:
- `Multi-agent coordination and knowledge integration - Claude/` (part 5)
- `COMPASS_MVP_Technical_Design.md`

**Performance Targets**:
- Observation phase: <2 minutes (parallel execution)
- Hypothesis generation: <30 seconds per hypothesis
- Configuration loads: <100ms
- Pattern matching: <10ms
- Total investigation time: 67% reduction from baseline

---

## Cost Management

### Token Budget Management

**Default Limits**:
- $10 per routine investigation
- $20 for critical incidents
- Users pay for their own LLM tokens (~$5-10 per investigation)

**Cost Optimization Strategies**:
1. Use GPT-4/Claude Opus ONLY for orchestrator and synthesis
2. Deploy cheaper models (GPT-4o-mini/Claude Sonnet) for data retrieval
3. Cache prompts aggressively (target 75%+ cache hit rate)
4. Track cost-per-incident-type metrics from day one

**Key Files**:
- `Enterprise tool feasibility and architect review - Claude/` (parts 1-3)
- `COMPASS_MVP_Technical_Design.md` (section on cost controls)

**Cost Tracking**:
```python
{
  "investigation_id": "INC-2024-1234",
  "total_cost": 8.45,
  "breakdown": {
    "orchestrator": 3.20,
    "database_agent": 2.15,
    "network_agent": 1.80,
    "caching_savings": 1.30
  },
  "tokens_used": 42250,
  "time_saved_minutes": 34,
  "cost_per_minute_saved": 0.25
}
```

**Key Quote**:
> "Engineers LOVE metrics. Show them 'Investigation cost: $8.45 (0.3% of engineer hourly rate). Time saved: 34 minutes.' That's the efficiency proof."

---

### Model Selection Strategy

**Model Routing**:
- **Orchestrator** (complex reasoning): GPT-4, Claude Opus
- **Data retrieval** (simple queries): GPT-4o-mini, Claude Sonnet
- **Pattern matching** (local): Ollama, self-hosted
- **Synthesis**: High-capability models

**Flexibility**:
- LLM provider agnostic
- BYOK (Bring Your Own Keys)
- Self-hosted options (Ollama)
- SaaS options (OpenAI, Anthropic)

**Key Files**:
- `Enterprise tool feasibility and architect review - Claude/` (parts 2-3)
- `COMPASS_Future_Proofing_Architecture.md`

---

## MCP Integration

### MCP as Integration Layer

**Key Benefit**: Community-maintained integrations solve the "integration hell" problem

**Approach**:
- COMPASS orchestrates MCP servers, doesn't write integrations
- When customer uses Datadog instead of Prometheus: "cool, use the Datadog MCP server"
- New data source = new MCP server, not COMPASS's problem

**Key Files**:
- `Enterprise tool feasibility and architect review - Claude/` (parts 2-3)
- `Building COMPASS_ project foundation and architecture - Claude/` (parts 1-4)

**Key Quote**:
> "MCP solves integration complexity - it's the AI that adapts to different APIs, not us having to write perfect integrations for everything."

---

### LGTM Stack Integration

**L**oki: Log aggregation
**G**rafana: Visualization and dashboards
**T**empo: Distributed tracing
**M**imir: Metrics storage

**Why LGTM First**:
- Complete observability stack coverage
- Open source = no vendor lock-in
- Common in engineering orgs
- Proven integration patterns
- MCP servers available or buildable

**Key Files**:
- `Building the ultimate SRE investigation tool - Claude/` (parts 1-3)
- `COMPASS_MVP_Architecture_Reference.md`

**Graceful Degradation**:
```
User: "I don't have Tempo installed"
COMPASS: "OK, using Prometheus metrics instead.
          (Install Tempo MCP server for trace correlation)"
```

---

## Product Strategy

### Bottom-Up Adoption Model

**The Path**:
1. One engineer installs locally
2. Solves incident faster
3. Team adopts it informally
4. Manager notices improved MTTR
5. Team wants official deployment
6. Spreads to other teams

**Key Files**:
- `Enterprise tool feasibility and architect review - Claude/` (all parts)
- `MVP to enterprise architecture roadmap - Claude/` (all parts)
- `COMPASS_Product_Strategy.md`

**Success Criteria (First Engineer)**:
- Reflexively uses COMPASS during incidents (muscle memory)
- AI right more often than wrong
- Misses it when it's down
- Tells teammates without prompting
- Sends you patterns to encode

**Key Quote**:
> "You're not building enterprise software. You're building a developer tool that enterprises will end up buying. That's a much better strategy."

---

### Pricing Model

**Free Tier (Individual Developers)**:
- Local deployment
- Community MCP servers
- Personal knowledge base
- **Monetization**: Adoption and evangelism

**Team Tier ($100/engineer/month)**:
- Shared team deployment
- Team knowledge base
- Post-mortem automation
- **Value Prop**: "10x faster incident resolution for your team"

**Enterprise Tier ($500+/engineer/month)**:
- Centralized hub-and-spoke deployment
- Global + tribal knowledge management
- Compliance audit trails (SOC2, GDPR, HIPAA)
- RBAC with tribal boundaries
- Learning analytics dashboard
- **Value Prop**: "Organizational learning from every incident"

**Enterprise Premium (Custom Pricing)**:
- Custom MCP server development
- Dedicated success manager
- On-premise deployment
- Custom compliance requirements
- **Value Prop**: "Transform your incident response culture"

**Key Files**:
- `Enterprise tool feasibility and architect review - Claude/` (part 3)
- `COMPASS_Product_Strategy.md`

---

### Revenue Models

**Consultancy-Funded Development**:
- Get paid to embed COMPASS at companies (first 2-3 customers)
- Learn real patterns from real incidents
- Refine through actual usage
- Success stories become case studies

**Open Source + Enterprise Features** (Grafana model):
- Core framework: Open source
- Community: Build MCP servers
- Monetize: Support, hosted version, enterprise features

**Key Files**:
- `Enterprise tool feasibility and architect review - Claude/` (part 3)
- `COMPASS_Product_Strategy.md`

---

## Implementation Priorities

### MVP Build Order

**Week 1-2: Minimum Lovable Product**
1. Basic LGTM integration
2. Single hypothesis generation (database issues)
3. CLI interface - just get SOMETHING working
4. Slack integration (where engineers actually are)
5. Cost tracking (silent but comprehensive)

**Week 3-4: Make It Trustworthy**
1. Hypothesis confidence scoring
2. Evidence linking to actual data
3. Jump to source (Grafana panels)
4. Show failures gracefully

**Week 5-6: Make It Indispensable**
1. Pattern learning ("I've seen this 3 times, it's usually X")
2. Personal runbook encoding
3. Metrics ("COMPASS saved you 34 minutes this week")

**Key Files**:
- `COMPASS_MVP_Build_Guide.md`
- `compass-day1-startup.md`
- `compass-tdd-workflow.md`

**Key Principle**:
> "One user who loves it over many who tolerate it. Full integration power over simplified subset. Getting to real problems over anticipating theoretical ones."

---

### TDD Workflow

**Test-Driven Development from Day 1**:
1. Write failing test for incident investigation behavior
2. Implement minimal code to pass test
3. Refactor while keeping tests green
4. Add observability metrics for component

**Testing Requirements**:
- Unit tests for individual agent logic
- Integration tests for tool interactions
- Scenario tests for common incident patterns
- Chaos testing for production resilience
- NO mocked observability data in integration tests

**Key Files**:
- `compass-tdd-workflow.md`
- `compass-day1-reconciled.md`
- `test_scientific_framework.py`

---

## Quick Reference by Chat File

### Building COMPASS: project foundation and architecture
**Topics**: Initial vision, ICS principles, OODA loop design, agent hierarchy, production-first mindset

### Building the ultimate SRE investigation tool
**Topics**: LGTM stack integration, MCP protocol, observability principles, data gathering strategies

### MVP to enterprise architecture roadmap
**Topics**: Phased development, deployment progression, team→tribe→enterprise evolution

### Enterprise tool feasibility and architect review
**Topics**: Bottom-up adoption, cost management, MCP integration, product strategy, pricing model

### Designing CLI interactions for agent-human collaboration
**Topics**: Interface design research, natural language first approach, user interaction modes, accessibility

### Agent behavior refinement and performance tracking
**Topics**: Enterprise knowledge integration, configuration-based refinement, Thimo documentation, A/B testing

### Agent hypothesis validation through falsification
**Topics**: Scientific framework, disproof strategies, Popper's methodology, evidence quality

### Handling disproven hypotheses in OODA loops
**Topics**: Blameless culture, human decisions as first-class, learning from unexpected outcomes

### Agent-driven post mortem documentation design
**Topics**: Post-mortem automation, Learning Teams vs RCA, contributing causes, timeline reconstruction

### Multi-agent coordination and knowledge integration
**Topics**: External knowledge sources, pattern learning, caching strategies, coordination patterns

### Building production systems with Claude code
**Topics**: Production deployment, infrastructure as code, monitoring, cost optimization, security

### Downloading project files
**Topics**: Project file organization, documentation exports

---

## Search Keywords

**Architecture**: ICS, OODA, multi-agent, orchestrator, hierarchy, coordination, blackboard, circuit breaker
**Methodology**: scientific method, hypothesis, evidence, disproof, falsification, Popper, confidence scoring
**Culture**: Learning Teams, blameless, psychological safety, RCA, contributing causes, systems thinking
**Technology**: Python, Kubernetes, PostgreSQL, Redis, LGTM, MCP, Prometheus, Grafana, Tempo
**Cost**: token budget, LLM routing, caching, cost per investigation, optimization
**Human-AI**: decision capture, disagreement, collaboration, trust calibration, transparency
**Enterprise**: RBAC, multi-tenancy, tribal knowledge, compliance, audit trail, BYOK
**Product**: bottom-up adoption, pricing tiers, consultancy model, open source, developer tools
**Interface**: CLI, natural language, conversation, progressive enhancement, adaptive
**Deployment**: local, team, shadow mode, hub-and-spoke, progressive rollout

---

## Related Documentation Files

- `COMPASS_Product_Reference_Document_v1_1.md` - Complete product specification
- `COMPASS_MVP_Architecture_Reference.md` - MVP architecture details
- `COMPASS_MVP_Technical_Design.md` - Technical implementation details
- `COMPASS_MVP_Build_Guide.md` - Step-by-step build instructions
- `compass-day1-startup.md` - Day 1 startup guide
- `compass-tdd-workflow.md` - TDD process documentation
- `claude.md` - Claude Code development guidelines
- `COMPASS_Enterprise_Knowledge_Architecture.md` - Enterprise knowledge system
- `COMPASS_Interface_Architecture.md` - Interface design specification
- `COMPASS_Future_Proofing_Architecture.md` - Extensibility and future-proofing
- `compass_enterprise_knowledge_guide.md` - Enterprise user guide (for Thimo)
- `compass-quick-reference.md` - Quick reference guide

---

## Key Architectural Documents Created During Planning

### Python Implementation Files
- `compass_scientific_framework.py` - Core scientific methodology framework
- `compass_database_agent.py` - Example specialist agent
- `compass_agent_template.py` - Template for new agents
- `test_scientific_framework.py` - Comprehensive test suite

### Architecture Documents
- `investigation_learning_human_collaboration_architecture.md` - Full multi-agent architecture
- `COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md` - Scientific framework documentation
- `IMPLEMENTATION_SUMMARY.md` - Executive implementation summary
- `FRAMEWORK_FLOW_DIAGRAM.txt` - Visual investigation flow

### Research Documents (PDFs)
- `Designing_ICSBased_MultiAgent_AI_Systems_for_Incident_Investigation.pdf`
- `Evaluation_of_Learning_Teams_Versus_Root_Cause_154.pdf`
- `Oct23LVI008TheProblemwithRootCauseAnalysis.pdf`
- `AI_PostMortem_Generation_COMPASS.pdf`
- `AI_PostMortem_Learning_Culture_COMPASS.pdf`

---

**End of Index**

*Use Cmd+F / Ctrl+F to search this document for any topic, keyword, or concept. Each entry points you to the specific conversation files and line numbers where information can be found.*
