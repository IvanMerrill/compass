# COMPASS Product Reference Document
## Comprehensive Observability Multi-Agent Platform for Adaptive System Solutions

**Version:** 1.1  
**Date:** November 16, 2025  
**Status:** Product Definition - Ready for Implementation  
**Audience:** Engineering Teams, Architects, Product Owners  

---

## Executive Summary

COMPASS is an AI-powered incident investigation platform that transforms how engineers diagnose and learn from production incidents. By orchestrating specialized AI agents following proven Incident Command System (ICS) principles and scientific methodology, COMPASS reduces Mean Time to Resolution (MTTR) by 67-90% while building a culture of continuous learning.

Unlike traditional observability tools that overwhelm engineers with raw data, COMPASS acts as an intelligent investigation assistant that systematically generates and tests hypotheses, gathering evidence from across the entire observability stack. Every investigation follows scientific rigor with complete audit trails, making the system suitable for SOC2, ISO27001, and other regulatory compliance requirements.

**Core Innovation:** COMPASS democratizes incident investigation expertise through parallel OODA loop execution. Multiple agents simultaneously test different hypotheses, compressing investigation time while maintaining scientific rigor. A junior engineer can conduct investigations with the thoroughness of a senior SRE, while experienced engineers save hours on routine investigations.

---

## 1. Problem Statement

### 1.1 The Current Reality

**For Engineers:**
- **15-20 minutes** just gathering initial data across multiple tools
- **Domain-specific query languages** (PromQL, LogQL, TraceQL) create barriers
- **Context switching** between Grafana, Loki, Tempo, Mimir exhausts cognitive capacity
- **Tribal knowledge** locked in senior engineers' heads
- **Post-mortems take 30-60 minutes** of documentation work after resolution

**For Organizations:**
- **67% of incidents** require multiple engineers to resolve
- **$1M+ annual cost** from extended MTTR (for 100-engineer organizations)
- **Knowledge loss** when engineers leave
- **Blame culture** from root cause analysis focus
- **Repeat incidents** from lack of systematic learning

### 1.2 Why Existing Solutions Fall Short

| Solution Type | Limitation |
|--------------|------------|
| **APM Tools** | Present data but don't analyze or hypothesize |
| **Runbook Automation** | Only works for known patterns |
| **ChatOps** | Still requires expertise to ask right questions |
| **Traditional RCA** | Creates blame culture, misses systemic issues |
| **ML Anomaly Detection** | High false positives, no investigation capability |

### 1.3 The Opportunity

By combining proven emergency management frameworks (ICS) with modern AI capabilities and scientific methodology, we can create a system that:
- **Compresses investigation time** through parallel hypothesis testing
- **Captures and applies organizational knowledge** automatically
- **Enables learning culture** through blameless retrospectives
- **Democratizes expertise** across all skill levels

---

## 2. Core Design Principles

### 2.1 Human-in-the-Loop (Level 1 Autonomy)

**Principle:** AI accelerates data gathering and hypothesis generation; humans make all critical decisions.

**Implementation:**
- Agents can query any observability tool
- Agents generate and rank hypotheses
- Humans select which hypothesis to pursue
- Humans approve all remediation actions
- Emergency stop always available

**Rationale:** Maintains safety, accountability, and regulatory compliance while maximizing speed.

### 2.2 Scientific Methodology with Parallel OODA Loops

**Principle:** Multiple agents execute OODA loops (Observe-Orient-Decide-Act) in parallel, each testing different hypotheses simultaneously.

**Implementation:**
- 5+ specialist agents work in parallel
- Each agent completes full OODA cycles
- Hypotheses tested through falsification
- Evidence tracked for and against each theory
- Results synthesized by orchestrator

**Unique Advantage:** While traditional investigation tests one hypothesis at a time, COMPASS tests 5+ simultaneously - like having a team of senior engineers investigating in parallel.

### 2.3 Contributing Causes Over Root Cause

**Principle:** Incidents have multiple contributing factors across system levels, not single root causes.

**Implementation:**
- Analyze six system levels (regulatory, organizational, technical management, work environment, human-system interface, equipment/technology)
- Generate Contributing Causes Map
- Focus on system improvements, not individual blame
- Follow Learning Teams methodology (114% more improvement actions than RCA)

**Rationale:** Research shows this approach generates 57% more system-focused improvements.

### 2.4 LLM Provider Agnostic

**Principle:** Bring your own LLM - work with whatever AI provider the enterprise already uses.

**Implementation:**
- Auto-detect available providers (OpenAI, Azure OpenAI, Anthropic, AWS Bedrock, Copilot)
- Support for any OpenAI-compatible endpoint
- Model routing based on query complexity
- Local models via Ollama for air-gapped environments

**Rationale:** Enterprises have existing AI contracts and compliance requirements. Flexibility removes adoption barriers.

### 2.5 Progressive Complexity

**Principle:** Simple to start, powerful when needed.

**Implementation:**
- Command-line interface for developer workflow
- Natural language for beginners
- Advanced commands for power users
- Progressive disclosure of information
- Context-aware assistance

**Rationale:** Accessibility drives adoption; power features retain expert users.

---

## 3. Product Architecture Overview

### 3.1 Three-Question Framework

Every investigation systematically answers:

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  1. WHAT is happening?                  â”‚
â”‚     â†’ Observe symptoms across systems   â”‚
â”‚     â†’ Identify anomalies                â”‚
â”‚     â†’ Establish timeline                â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                   â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  2. WHERE is it happening?              â”‚
â”‚     â†’ Isolate affected components       â”‚
â”‚     â†’ Map dependencies                  â”‚
â”‚     â†’ Determine blast radius            â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                   â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  3. WHY is it happening?                â”‚
â”‚     â†’ Generate causal hypotheses        â”‚
â”‚     â†’ Test through falsification        â”‚
â”‚     â†’ Identify contributing causes      â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### 3.2 Parallel Agent Execution

```
Orchestrator (Incident Commander)
    â”‚
    â”œâ”€â”€ [Parallel OODA Loop Execution]
    â”‚   â”œâ”€â”€ Database Agent â†’ Hypothesis A
    â”‚   â”œâ”€â”€ Network Agent â†’ Hypothesis B  
    â”‚   â”œâ”€â”€ Application Agent â†’ Hypothesis C
    â”‚   â”œâ”€â”€ Infrastructure Agent â†’ Hypothesis D
    â”‚   â””â”€â”€ Tracing Agent â†’ Hypothesis E
    â”‚
    â””â”€â”€ Synthesis â†’ Ranked hypotheses for human decision
```

### 3.3 Investigation Flow

1. **Trigger:** Alert or manual start via CLI/Slack
2. **Parallel Observation:** All agents gather data simultaneously (<2 minutes)
3. **Hypothesis Generation:** Each agent proposes theories
4. **Human Decision:** Select most promising hypothesis
5. **Falsification:** Attempt to disprove selected hypothesis
6. **Iterate or Conclude:** Continue until resolution
7. **Generate Post-Mortem:** Automatic documentation

---

## 4. MVP Features (Months 1-3)

### 4.1 Core Investigation Engine

**Feature:** Multi-agent parallel investigation system

**Capabilities:**
- Spawn 5 specialist agents (Database, Network, Application, Infrastructure, Tracing)
- Query LGTM stack via MCP (Loki, Grafana, Tempo, Mimir)
- Execute investigations in <2 minutes for observation phase
- Generate 3-5 ranked hypotheses with confidence scores
- Parallel OODA loop execution across all agents

**Done When:**
- Can complete full investigation cycle for P1 incident
- All agents execute OODA loops in parallel
- Hypothesis confidence scores correlate with correctness >70%
- Complete audit log of investigation steps
- Clear differentiation of parallel vs sequential findings

### 4.2 Scientific Hypothesis Framework

**Feature:** Rigorous hypothesis generation and testing

**Capabilities:**
- Generate testable, falsifiable hypotheses
- Attempt disproof before acceptance
- Track evidence for/against each hypothesis
- Calculate confidence based on survived tests
- Document all paths including disproven ones

**Done When:**
- Every hypothesis has clear test criteria
- System actively queries for contradicting evidence
- Confidence scores update based on evidence
- Investigation chronicle shows complete journey

### 4.3 Command-Line Interface (Primary)

**Feature:** Developer-first CLI for investigation control

**Capabilities:**
```bash
# Start investigation
compass investigate payment-service --symptom "high latency"

# Interactive mode
compass> show hypotheses
compass> test hypothesis 1 
compass> why do you think this?
compass> generate post-mortem
```

**Done When:**
- Full investigation workflow via CLI
- Tab completion for commands
- Clear output formatting
- Scriptable for automation
- Works in any terminal

### 4.4 LLM Provider Flexibility

**Feature:** Bring-your-own-LLM architecture

**Capabilities:**
- Auto-detect available providers during setup
- Support OpenAI, Azure OpenAI, Anthropic, AWS Bedrock, Copilot
- Configure any OpenAI-compatible endpoint
- Local models via Ollama
- Model routing (simple queries â†’ smaller model, complex â†’ larger)
- **Clear cost transparency: Users provide and pay for their own API keys**

**Done When:**
- Setup wizard detects available LLMs
- Can switch providers without code changes
- Cost estimates shown before investigation
- Works with at least 3 major providers
- Clear documentation on API key configuration

### 4.5 Cost Management System

**Feature:** Transparent tracking and control of AI costs

**Capabilities:**
- Real-time token usage tracking
- Per-investigation budget limits ($5 default)
- Cost attribution by hypothesis/agent
- Automatic optimization for expensive operations
- **Users pay for their own LLM tokens via their API keys**

**Done When:**
- Never exceeds budget without permission
- Cost displayed for every investigation
- Can predict investigation cost before starting
- Optimization reduces costs by >30% over naive approach
- Clear messaging that token costs are user's responsibility

### 4.6 Post-Mortem Generation

**Feature:** Automated post-mortem document creation

**Capabilities:**
- Generate comprehensive post-mortem in <10 minutes
- Include investigation timeline
- Document all hypotheses (including disproven)
- Contributing causes map (not root cause)
- System improvement recommendations
- Markdown/Confluence format export

**Done When:**
- Post-mortem includes all required sections
- Human review time <5 minutes
- Follows Learning Teams methodology
- Exportable to Confluence/GitHub
- Shows complete investigation journey

### 4.7 Failure Handling & Learning

**Feature:** Graceful failure with learning capture

**Capabilities:**
- Clear communication when COMPASS can't form hypotheses
- Fallback to data presentation when AI unavailable
- Capture corrections when COMPASS is wrong
- Log unsolved patterns for analysis
- Identify observability gaps

**Done When:**
- Every failure mode has defined behavior
- Users can correct wrong conclusions
- Failed investigations still provide value
- Learning system captures failure patterns
- No silent failures or unclear states

### 4.8 Deployment Options

**Feature:** Flexible deployment from laptop to cluster

**Capabilities:**
- Kubernetes deployment with Helm charts
- Local development with Tilt (`tilt up` and running)
- Docker container packaging
- 30-minute setup to first investigation
- Works with customer's existing LLM contracts

**Done When:**
- Single `tilt up` starts local environment
- Helm install works on any K8s cluster
- Clear documentation for both modes
- No external dependencies except LLM and observability stack
- Setup wizard guides configuration

---

## 5. Future Features (Post-MVP)

### 5.1 Phase 2: Team Collaboration (Months 4-6)

**Shared Knowledge Base**
- Team-specific pattern library
- Collaborative post-mortem editing
- Shared investigation views
- Team runbook encoding

**Slack Integration Enhancement**
- Start investigations from Slack
- Real-time investigation updates
- Thread-based hypothesis discussion
- Team notification on resolution

**Advanced MCP Servers**
- GitHub code analysis
- Confluence documentation search
- Kubernetes configuration inspection
- CI/CD pipeline analysis

### 5.2 Phase 3: Enterprise Features (Months 7-12)

**Organizational Learning**
- Cross-team pattern recognition
- Tribal knowledge aggregation
- Dependency impact analysis
- Organizational metrics dashboard

**Enterprise Requirements**
- RBAC with SSO/SAML (paid feature)
- Advanced audit logging (paid feature)
- SLA support contracts (paid feature)
- Multi-tenant isolation

**Extensibility Framework**
- Plugin architecture for new agents
- Custom MCP server SDK
- Webhook integrations
- REST API for third-party tools

### 5.3 Phase 4: Resilience Engineering (Year 2)

**Build Adaptive Capacity (Not Prediction)**
- Chaos engineering integration
- Normal work analysis (work-as-done)
- Resilience metrics tracking
- Capacity and boundary identification
- Recovery pattern library

**Advanced Learning**
- Cross-incident pattern clustering
- Automated observability gap detection
- Team capability assessment
- Cultural change metrics

---

## 6. User Experience

### 6.1 Primary Personas

**Junior Engineer (0-2 years)**
- Needs: Guidance through investigation process
- Interface: Natural language via CLI
- Value: Conducts senior-level investigations

**Senior Engineer (5+ years)**
- Needs: Speed and efficiency
- Interface: CLI with advanced commands
- Value: 70% time savings on routine investigations

**On-Call Engineer**
- Needs: Fast resolution at 3 AM
- Interface: CLI + Slack integration
- Value: Reduce stress, faster resolution

**Engineering Manager**
- Needs: Team learning and metrics
- Interface: Post-mortem reports + dashboards
- Value: Improved team capability, reduced MTTR

### 6.2 Primary User Journey (CLI-First)

```bash
# Alert fires, engineer responds
$ compass investigate payment-service --urgent
COMPASS: Initiating parallel investigation across 5 agents...

[Live output as agents work]
Database Agent: Checking connection pools... ANOMALY FOUND
Network Agent: Analyzing latency patterns... normal
Application Agent: Reviewing error logs... elevated 5xx rate
Infrastructure Agent: Checking resource usage... memory pressure detected
Tracing Agent: Analyzing service dependencies... normal

COMPASS: I found 3 likely causes (parallel analysis complete):
1. [85% confidence] Database connection pool exhaustion 
2. [72% confidence] Memory pressure causing GC pauses
3. [45% confidence] Cascading failure from upstream service

$ compass test 1
COMPASS: Testing hypothesis: Database connection pool exhaustion
- Checking connection pool metrics... âœ“ maxed at 100
- Looking for contradicting evidence... âœ— none found
- Analyzing timing correlation... âœ“ matches symptom onset
- Recent changes... âœ“ connection timeout modified 2 hours ago

Hypothesis CONFIRMED with 92% confidence.
Recommended action: Increase pool size or revert timeout change

$ compass generate post-mortem
COMPASS: Generating comprehensive post-mortem...
Post-mortem ready: incident-2025-11-16-payment-service.md
```

### 6.3 Interface Principles

- **CLI-First:** Natural developer workflow
- **No Training Required:** Intuitive commands with help
- **Progressive Disclosure:** Show simple first, details on demand  
- **Blameless Language:** "What happened" not "who did it"
- **Visual Investigation Map:** See all paths explored (even dead ends)
- **Complete Transparency:** Every decision explained

---

## 7. Technical Implementation

### 7.1 Technology Stack

**Core Platform:**
- Python 3.11+ (readable, maintainable, extensive libraries)
- FastAPI for REST endpoints
- Redis for investigation state
- PostgreSQL with pgvector for knowledge/embeddings
- Docker/Kubernetes deployment

**AI/ML Components:**
- LangChain for agent orchestration
- Provider-agnostic LLM interface
- Sentence-transformers for similarity
- pgvector for vector storage (no vendor lock-in)

**Integrations:**
- MCP for tool connections (LGTM stack initially)
- Prometheus client for metrics
- Slack SDK for chat interface
- Confluence API for documentation

**Development Tools:**
- Tilt for local Kubernetes development
- Helm for production deployment
- pytest for comprehensive testing
- Black/ruff for code formatting

### 7.2 Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Agent Framework** | Custom Python | Need fine control over scientific method |
| **LLM Strategy** | Bring-your-own-LLM | Enterprises have existing AI contracts |
| **State Management** | Event streaming (Redis) | Enable real-time updates and audit |
| **Knowledge Storage** | PostgreSQL + pgvector | Single database, no vendor lock-in |
| **Vector Database** | pgvector | Already using Postgres, trusted by enterprises |
| **Language** | Python only | Readable, maintainable, wide support |
| **Deployment** | Kubernetes + Tilt | Enterprise standard + great DX |
| **Initial Stack** | LGTM (Loki, Grafana, Tempo, Mimir) | Author's environment, then expand |

### 7.3 Performance Requirements

- **Investigation Start:** <5 seconds from trigger
- **Observation Phase:** <2 minutes for parallel scan
- **Hypothesis Generation:** <30 seconds
- **Post-Mortem Generation:** <10 minutes
- **Concurrent Investigations:** 10+ per instance
- **Data Retention:** Customer-configurable (investigations ephemeral, learnings persistent)

---

## 8. Implementation Roadmap

### 8.1 Month 1: Foundation

**Week 1-2: Core Architecture**
- [ ] ScientificAgent base class
- [ ] Parallel OODA loop controller
- [ ] Investigation state machine
- [ ] Cost tracking system
- [ ] LLM provider abstraction layer

**Week 3-4: Agent Implementation**
- [ ] Database Agent with Mimir integration
- [ ] Application Agent with Loki integration
- [ ] Network Agent with Mimir integration
- [ ] Infrastructure Agent
- [ ] Basic Orchestrator with parallel execution

### 8.2 Month 2: Intelligence Layer

**Week 5-6: Hypothesis System**
- [ ] Hypothesis generation from parallel agents
- [ ] Confidence scoring algorithm
- [ ] Falsification framework
- [ ] Evidence tracking
- [ ] Synthesis of parallel findings

**Week 7-8: Learning System**
- [ ] Pattern recognition
- [ ] Knowledge persistence in pgvector
- [ ] Similar incident matching
- [ ] Feedback loop for corrections
- [ ] Failure pattern capture

### 8.3 Month 3: User Experience

**Week 9-10: Interface**
- [ ] CLI with rich output
- [ ] Interactive investigation mode
- [ ] Slack integration (basic)
- [ ] Post-mortem generator
- [ ] Setup wizard for LLM configuration

**Week 11-12: Production Readiness**
- [ ] Kubernetes manifests + Helm charts
- [ ] Tilt configuration for local dev
- [ ] Docker packaging
- [ ] Comprehensive documentation
- [ ] Quick-start guide
- [ ] Beta user onboarding

---

## 9. Success Metrics

### 9.1 Quantitative Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **MTTR Reduction** | 67-90% | Time from alert to resolution |
| **Investigation Time** | <5 minutes | Start to first hypothesis |
| **Parallel Speedup** | 5-10x | vs sequential investigation |
| **Post-Mortem Time** | <10 minutes | Auto-generation time |
| **Hypothesis Accuracy** | >70% | Confirmed/selected ratio |
| **Cost per Investigation** | <$5 | LLM token usage |
| **Adoption Rate** | >90% | Incidents using COMPASS |

### 9.2 Qualitative Metrics

- **Learning Velocity:** 7.5 improvements per incident (Learning Teams benchmark)
- **System Focus:** 57% system vs person-focused actions
- **User Satisfaction:** >4.5/5.0 rating
- **Knowledge Retention:** Patterns reused in >30% investigations
- **Culture Change:** 200% increase in near-miss reporting

### 9.3 MVP Success Criteria

**Technical Success:**
- Complete investigation cycle in production
- 10 different incident types resolved
- Parallel OODA execution working
- Zero critical bugs in first month
- 99% uptime

**User Success:**
- 10 named beta users actively using
- 50% use it for every incident
- <30 minutes to first investigation
- Positive feedback on ease of use
- Clear value demonstrated

**Business Success:**
- 3 customer testimonials
- 1 published case study
- Clear path to 100 users
- Open source repo with >100 stars

---

## 10. Business Model & Monetization

### 10.1 Open Core Strategy

**Open Source (Free Forever):**
- Core investigation engine
- All specialist agents
- CLI interface
- Basic integrations
- Community support

**Enterprise Edition (Paid):**
- RBAC and SSO/SAML
- Advanced audit logging
- SLA support contracts
- Multi-team coordination
- Compliance reporting
- Priority support

### 10.2 Revenue Streams

**Phase 1: Open Source Adoption**
- Build community
- Gather feedback
- Prove value
- No revenue focus

**Phase 2: Enterprise License**
- $50-100K annual contracts
- Based on engineering team size
- Including support and updates

**Phase 3: Professional Services**
- $50-100K implementation projects
- Custom MCP server development
- Learning Teams training
- Cultural transformation consulting

### 10.3 Why This Works

- **Grafana/Cilium Model:** Proven open core success
- **Enterprise Features:** Clear differentiation for paid
- **Services Opportunity:** Complex enough to need help
- **No Lock-in:** Increases trust and adoption

---

## 11. Competitive Differentiation

### 11.1 Unique Advantages

**Parallel OODA Loop Execution**
- 5+ agents testing hypotheses simultaneously
- 5-10x faster than sequential investigation
- More thorough coverage of possibility space
- Novel approach not seen in other tools

**Scientific Rigor**
- Only solution using falsification methodology
- Complete investigation transparency
- Audit-ready documentation
- Disproven hypotheses as learning artifacts

**Cultural Transformation**  
- Learning Teams methodology built-in
- Contributing causes over root cause
- Blameless by design
- Focus on building adaptive capacity

**LLM Flexibility**
- Bring-your-own-LLM model
- No vendor lock-in
- Works with existing enterprise contracts
- Local model support

**True Open Source**
- Not "open core" with crippled free version
- Fully functional for individuals and small teams
- Community-driven development
- No artificial limitations

### 11.2 Competitive Moat

1. **Network Effects:** More investigations â†’ better patterns â†’ faster resolution
2. **Organizational Learning:** Accumulated knowledge unique to each company
3. **Cultural Lock-in:** Teams adopt Learning Teams methodology
4. **Parallel Architecture:** Hard to replicate without full rebuild

### 11.3 Partnership Strategy

**Integrate With, Not Against:**
- APM vendors are data sources, not competitors
- Observability tools provide the data we analyze
- We make their tools more valuable
- Potential for vendor partnerships/integrations

---

## 12. Risk Mitigation

### 12.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **LLM Costs Explode** | High | Medium | Hard budget limits, optimization, user pays |
| **Hallucination** | High | Low | Scientific method, falsification, audit trails |
| **Integration Complexity** | Medium | High | Start with LGTM only, add incrementally |
| **Performance Issues** | Medium | Medium | Async operations, caching, load testing |
| **Parallel Execution Bugs** | High | Medium | Extensive testing, gradual rollout |

### 12.2 Adoption Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Learning Curve** | High | Low | Natural language, CLI-first, good docs |
| **Trust in AI** | High | Medium | Transparency, audit trails, human control |
| **Cultural Resistance** | Medium | Medium | Blameless focus, emphasize learning |
| **Tool Fatigue** | Medium | High | Replace investigation work, not add to it |

### 12.3 Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Slow Adoption** | High | Medium | Open source, no barrier to try |
| **Competition** | Medium | High | Fast execution, parallel OODA moat |
| **No Revenue** | Low | Low | Services fallback, low overhead |
| **Support Burden** | Medium | Medium | Good docs, community support |

---

## 13. Key Decisions Made

Based on collaborative review, the following decisions are finalized:

### Product Decisions
- **Free Tier:** Defer limits until usage patterns emerge
- **Team Definition:** Let usage patterns define boundaries  
- **Data Retention:** Use customer's storage, their retention policies
- **Compliance:** Start with self-hosted to avoid compliance burden

### Technical Decisions
- **LLM Provider:** User chooses during setup, bring-your-own-API-key
- **Vector Database:** PostgreSQL with pgvector
- **Deployment:** Kubernetes required, Tilt for local development
- **Language:** Python only for readability and maintainability
- **Initial Observability Stack:** LGTM (Loki, Grafana, Tempo, Mimir)

### Business Decisions
- **Pricing Model:** Defer, track all metrics for future decision
- **Open Source:** Everything in core product open
- **APM Strategy:** Partner and integrate, not compete
- **Support Model:** Community initially, paid enterprise later

---

## 14. Success Philosophy

### What Success Looks Like

**Year 1:**
- 100+ organizations using COMPASS
- Measurable MTTR reduction across users
- Active open source community
- 10+ contributed MCP servers

**Year 3:**
- Standard tool in SRE toolkit
- Learning Teams methodology adoption
- Enterprise revenue supporting development
- Industry recognition for cultural impact

### What We're Really Building

We're not just building an investigation tool. We're building:
- **A movement** toward scientific incident investigation
- **A culture** of learning over blame
- **A community** of reliability engineers helping each other
- **A platform** that makes every engineer more capable

---

## Conclusion

COMPASS represents a fundamental shift in incident investigation through parallel OODA loop execution and scientific methodology. By allowing engineers to bring their own LLM and focusing on CLI-first interaction, we remove adoption barriers while delivering immediate value.

The open source strategy ensures widespread adoption while the enterprise features provide a clear monetization path. Most importantly, we're not trying to predict failures - we're building adaptive capacity and learning culture.

Every technical decision supports the mission: make great incident investigation accessible to everyone. The parallel execution model is our technical moat, the Learning Teams methodology is our cultural differentiator, and the open source approach is our growth strategy.

**The path forward is clear:**
1. Build the MVP with parallel OODA loops
2. Prove value with 10 beta users
3. Open source for community adoption
4. Enterprise features for revenue
5. Change the industry's approach to incidents

---

*"The best investigation is one where 5 agents explore different theories simultaneously, the human makes informed decisions, and the organization learns from every path explored - even the dead ends."*

---

**Document Version History:**
- v1.0 (2025-11-16): Initial product reference document
- v1.1 (2025-11-16): Updated with LLM flexibility, parallel OODA emphasis, CLI-first design, business model clarification

**Related Documents:**
- `compass_architecture.txt` - Technical architecture details
- `investigation_learning_human_collaboration_architecture.md` - Learning system design
- `COMPASS_Architecture_Evaluation.docx` - Extensibility assessment
- `COMPASS_Product_Strategy.md` - Go-to-market strategy
