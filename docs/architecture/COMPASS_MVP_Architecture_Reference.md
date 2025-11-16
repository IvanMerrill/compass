# COMPASS MVP Architecture Reference Document
## Building the Foundation for Intelligent Incident Investigation

**Version:** 1.0  
**Date:** November 16, 2025  
**Status:** Implementation Blueprint  
**Audience:** Ivan (Product Owner), Claude Code, Development Team

---

## Executive Summary

COMPASS (Comprehensive Observability Multi-Agent Platform for Adaptive System Solutions) transforms incident investigation from reactive firefighting to systematic scientific inquiry. This document defines our path from MVP to enterprise platform, providing concrete guidance for implementation while maintaining flexibility for learning and adaptation.

**Core Innovation:** Parallel OODA loops where multiple specialist agents simultaneously test different hypotheses, compressing investigation time from hours to minutes while maintaining scientific rigor.

**Cultural Mission:** Shift from "Who broke it?" to "What made sense at the time?" - fundamentally changing how engineering teams learn from incidents.

**Development Reality:** 3-month MVP timeline is aggressive but achievable with focused scope, extensive AI assistance, and clear architectural decisions already made.

---

## Part 1: Understanding What We're Building

### 1.1 The Problem We're Solving

Every production incident follows a predictable pattern of chaos:
- Engineers scramble through dashboards seeking clues
- Senior engineers monopolize investigations while juniors watch
- Valuable patterns get lost in Slack threads
- Post-mortems focus on blame rather than learning
- The same incidents repeat because lessons aren't captured

**COMPASS changes this by:**
- Automating the systematic investigation process
- Democratizing investigation expertise to all engineers  
- Capturing every investigation path for organizational learning
- Generating evidence-based post-mortems automatically
- Building institutional memory that prevents repeat incidents

### 1.2 Product Vision

**Near-term (3 months):** A developer tool that any engineer can run to get senior-level investigation in minutes, not hours.

**Mid-term (12 months):** A team platform that captures and shares investigation patterns, making every incident a learning opportunity.

**Long-term (2+ years):** The organizational nervous system for engineering teams - where every incident contributes to collective intelligence.

### 1.3 Why This Approach Works

**Scientific Foundation:** Based on proven frameworks:
- **ICS (Incident Command System):** Military-tested command structure
- **OODA Loops:** Boyd's decision-making framework for rapid iteration
- **Learning Teams:** 7.5x more improvement actions than root cause analysis
- **Hypothesis Falsification:** Popper's scientific method applied to incidents

**Technical Innovation:** 
- Parallel investigation compresses time by 5-10x
- LLM flexibility works with existing enterprise AI contracts
- MCP integration leverages existing observability investments
- CLI-first design matches developer workflows

**Cultural Alignment:**
- Bottom-up adoption through individual developers
- Respects tribal knowledge boundaries
- No blame, only learning
- Transparent reasoning builds trust

---

## Part 2: MVP Scope (Months 1-3)

### 2.1 Core Capabilities

The MVP proves our fundamental hypothesis: AI-powered parallel investigation dramatically reduces MTTR while improving learning.

**What the MVP MUST do:**
1. Complete a full investigation cycle in <5 minutes
2. Generate 3-5 testable hypotheses with confidence scores
3. Attempt to disprove hypotheses before presenting them
4. Provide transparent reasoning for every conclusion
5. Generate a useful post-mortem automatically
6. Work with existing LGTM stack out of the box

**What the MVP WON'T do (yet):**
- Team knowledge sharing (Phase 2)
- Enterprise features like SSO/RBAC (Phase 3)
- Predictive capabilities (explicitly not a goal)
- Custom agent development (post-MVP)
- Web UI beyond basic config (CLI-first)

### 2.2 User Journey

```
1. TRIGGER: Alert fires or engineer notices issue
   $ compass investigate payment-service --symptom "high latency"

2. OBSERVE: 5 specialist agents query in parallel
   - Database Agent â†’ Mimir metrics, connection pools, slow queries
   - Network Agent â†’ Latency patterns, packet loss, routing
   - Application Agent â†’ Loki logs, error rates, traces
   - Infrastructure Agent â†’ CPU, memory, disk, pods
   - Tracing Agent â†’ Tempo distributed traces
   
3. HYPOTHESIZE: Agents generate theories
   [85%] Database lock contention on payments table
   [72%] Network latency to payment provider
   [45%] Memory pressure causing GC pauses
   
4. DECIDE: Human selects most promising
   > investigate hypothesis 1

5. FALSIFY: System attempts disproof
   âœ“ Lock wait times correlate with latency spike
   âœ“ No increase in payment provider latency
   âœ— Cannot find contradicting evidence
   
6. RESOLVE: Human-directed mitigation
   > Suggested action: Kill long-running transaction
   > Execute? [y/n]

7. LEARN: Automatic post-mortem generation
   - Complete timeline with evidence
   - All tested hypotheses (including disproven)  
   - Improvement actions
   - Pattern saved for future incidents
```

### 2.3 Technical Decisions Made

These are locked for MVP - no second-guessing:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Language** | Python | Readability, AI familiarity, library ecosystem |
| **Deployment** | Kubernetes + Docker | Industry standard, Tilt for local dev |
| **LLM Strategy** | Provider-agnostic | OpenAI, Anthropic, Azure, Ollama |
| **Interface** | CLI-first | Developer adoption before enterprise |
| **State Storage** | SQLite â†’ PostgreSQL | Simple start, clear upgrade path |
| **Knowledge Format** | YAML + Markdown | Human-readable, git-friendly |
| **Testing** | TDD from day 1 | Quality and confidence |

---

## Part 3: System Architecture

### 3.1 High-Level Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                     User Interface Layer                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚   CLI    â”‚  â”‚  Slack   â”‚  â”‚ Web API  â”‚  â”‚ Future: UI â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â”‚
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    Orchestration Layer                       â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚            Investigation Orchestrator                 â”‚  â”‚
â”‚  â”‚  â€¢ OODA Loop Controller (Parallel Execution)         â”‚  â”‚
â”‚  â”‚  â€¢ Hypothesis Ranking & Confidence Scoring           â”‚  â”‚
â”‚  â”‚  â€¢ Human Decision Points & Audit Trail               â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â”‚
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    Specialist Agent Layer                    â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚ Database â”‚ â”‚ Network  â”‚ â”‚   App    â”‚ â”‚Infrastructureâ”‚  â”‚
â”‚  â”‚  Agent   â”‚ â”‚  Agent   â”‚ â”‚  Agent   â”‚ â”‚    Agent     â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â”‚                                                              â”‚
â”‚  Each agent implements:                                      â”‚
â”‚  â€¢ observe() - Gather domain-specific data                  â”‚
â”‚  â€¢ hypothesize() - Generate testable theories               â”‚
â”‚  â€¢ test_hypothesis() - Attempt falsification                â”‚
â”‚  â€¢ get_evidence() - Provide supporting data                 â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â”‚
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    Integration Layer (MCP)                   â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚   Loki   â”‚ â”‚ Grafana  â”‚ â”‚  Tempo   â”‚ â”‚    Mimir     â”‚  â”‚
â”‚  â”‚  (Logs)  â”‚ â”‚(Dashbds) â”‚ â”‚ (Traces) â”‚ â”‚  (Metrics)   â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**For detailed technical architecture:** See `compass_architecture.txt`

### 3.2 Core Components

#### Investigation Orchestrator
- **Purpose:** Coordinate parallel agent execution
- **Key Responsibilities:**
  - Spawn specialist agents based on symptoms
  - Manage OODA loop progression
  - Rank hypotheses by confidence
  - Track human decisions
  - Generate audit trail

#### Specialist Agents  
- **Purpose:** Domain-specific investigation
- **Implementation:** See `compass_scientific_framework.py` for base class
- **Extensibility:** Plugin architecture for new domains

#### Knowledge System
- **MVP:** Local SQLite with patterns
- **Future:** Distributed knowledge federation
- **Details:** See `COMPASS_Enterprise_Knowledge_Architecture.md`

### 3.3 Data Flow

```
1. Incident Trigger
   â†“
2. Parallel Observation (all agents simultaneously)
   â”œâ”€â†’ Database Agent â†’ Query metrics/logs
   â”œâ”€â†’ Network Agent â†’ Query network data  
   â”œâ”€â†’ App Agent â†’ Query application logs
   â””â”€â†’ Infra Agent â†’ Query infrastructure metrics
   â†“
3. Hypothesis Generation (each agent independently)
   â†“
4. Hypothesis Ranking (orchestrator)
   â†“
5. Human Selection
   â†“
6. Falsification Attempt (selected hypothesis)
   â†“
7. Result Presentation
   â†“
8. Human Decision & Action
   â†“
9. Post-Mortem Generation
```

---

## Part 4: Implementation Roadmap

### 4.1 Month 1: Foundation (Weeks 1-4)

**Goal:** Core engine running with basic agents

**Week 1-2: Core Framework**
- [ ] Set up project structure with Tilt
- [ ] Implement `ScientificAgent` base class
- [ ] Create `InvestigationOrchestrator` 
- [ ] Build OODA loop controller
- [ ] Add comprehensive logging/audit trail

**Week 3-4: First Agents**
- [ ] Database Agent with Mimir integration
- [ ] Application Agent with Loki integration
- [ ] Basic hypothesis generation
- [ ] Confidence scoring algorithm
- [ ] Cost tracking ($5/investigation target)

**Validation Checkpoint:** Can complete investigation for database issue

### 4.2 Month 2: Intelligence (Weeks 5-8)

**Goal:** Scientific reasoning and learning

**Week 5-6: Hypothesis Framework**
- [ ] Falsification engine
- [ ] Evidence chain tracking
- [ ] Hypothesis ranking algorithm
- [ ] Parallel vs sequential comparison
- [ ] Multi-hypothesis testing

**Week 7-8: Learning System**
- [ ] Pattern recognition from investigations
- [ ] Local knowledge persistence
- [ ] Similar incident detection
- [ ] Feedback incorporation
- [ ] Pattern reuse in new investigations

**Validation Checkpoint:** 70% hypothesis accuracy on test incidents

### 4.3 Month 3: Production Ready (Weeks 9-12)

**Goal:** Usable product for beta users

**Week 9-10: User Experience**
- [ ] CLI with rich terminal output
- [ ] Interactive investigation mode
- [ ] Slack integration
- [ ] Post-mortem generator
- [ ] Configuration management

**Week 11-12: Deployment & Polish**
- [ ] Docker packaging
- [ ] Kubernetes manifests + Helm
- [ ] Tilt configuration perfected
- [ ] Documentation & quick-start guide
- [ ] Beta user onboarding flow

**Validation Checkpoint:** 10 beta users successfully investigating

---

## Part 5: Critical Success Factors

### 5.1 What Success Looks Like

**Technical Success:**
- Investigations complete in <5 minutes
- Parallel execution shows 5-10x speedup
- 70% of hypotheses prove correct
- Zero critical bugs in production
- Cost under $5 per investigation

**User Success:**
- 10 named beta users (you already have them)
- 50% use it for every incident
- Setup to first investigation <30 minutes
- Clear value vs manual investigation
- Positive feedback on ease of use

**Business Success:**
- 3 customer testimonials
- 1 detailed case study
- Clear path to 100 users
- Open source repo with community interest

### 5.2 Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **LLM costs explode** | Medium | High | Strict token limits, caching, local Ollama option |
| **Agents hallucinate** | High | Medium | Falsification framework, evidence requirements |
| **Too complex for users** | Low | High | CLI-first, sane defaults, progressive disclosure |
| **Can't access data** | Medium | High | MCP flexibility, manual input option |
| **Performance issues** | Low | Medium | Parallel execution, async everything |

### 5.3 Explicit Trade-offs

**We're optimizing for:**
- Speed of investigation over perfect accuracy
- Developer experience over enterprise features
- Learning capture over prediction
- Transparency over sophistication
- Proven value over feature completeness

**We're explicitly NOT doing:**
- Web UI (CLI is enough for MVP)
- Predictive analytics (resilience over prediction)
- Custom ML models (use existing LLMs)
- Complex deployment (Docker + Tilt only)
- Enterprise features (no SSO, RBAC for MVP)

---

## Part 6: Beyond MVP

### 6.1 Phase 2: Team Platform (Months 4-6)

**Knowledge Sharing**
- Team knowledge base
- Shared investigation views
- Collaborative post-mortems
- Pattern library with versioning

**Enhanced Integration** 
- GitHub for code correlation
- Confluence for runbook search
- PagerDuty for alert context
- Kubernetes for config analysis

**Details:** See `COMPASS_Product_Strategy.md` Section 5.2

### 6.2 Phase 3: Tribal Federation (Months 7-12)

**Organizational Learning**
- Hub-and-spoke architecture
- Tribal knowledge boundaries
- Cross-team pattern detection
- Dependency impact analysis

**Enterprise Features**
- RBAC with team/tribal boundaries
- SSO/SAML integration
- Compliance reporting
- SLA support contracts

**Architecture:** See `COMPASS_Product_Strategy.md` Section 5.3

### 6.3 Future Vision (Year 2+)

**Platform Capabilities**
- Organizational memory system
- Automated runbook generation
- Incident prevention recommendations
- Cultural transformation metrics

**Market Position**
- Open core with enterprise features
- $50-100K annual contracts
- Professional services arm
- Industry thought leadership

---

## Part 7: Getting Started

### 7.1 Immediate Next Steps

**This Week:**
1. Review and approve this document
2. Set up development environment with Tilt
3. Create project repository structure
4. Implement first agent (Database)
5. Begin daily progress tracking

**Success Criteria for Week 1:**
- [ ] Tilt environment running locally
- [ ] Basic agent querying real data
- [ ] First hypothesis generated
- [ ] Clear understanding of next steps

### 7.2 How to Use This Document

**For Development:**
- Part 2 defines what to build
- Part 3 shows how components connect
- Part 4 provides the schedule
- Referenced docs have implementation details

**For Decisions:**
- Part 5 defines success metrics
- Trade-offs are explicit
- Risks are acknowledged
- Future phases are mapped

**For Communication:**
- Executive summary for stakeholders
- User journey for beta testers
- Technical sections for developers
- Roadmap for project tracking

### 7.3 Living Document Process

This document will evolve as we learn:
- Weekly reviews of progress vs plan
- Monthly updates to reflect reality
- Quarterly strategic reassessment
- All changes tracked in version history

---

## Appendices

### A. Reference Documents

| Document | Purpose | When to Consult |
|----------|---------|-----------------|
| `compass_scientific_framework.py` | Agent implementation | Building new agents |
| `COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md` | Scientific methodology | Understanding reasoning |
| `compass_architecture.txt` | Technical details | System design decisions |
| `COMPASS_Product_Strategy.md` | Business strategy | Pricing, go-to-market |
| `COMPASS_Enterprise_Knowledge_Architecture.md` | Knowledge system | Phase 2 planning |
| Research PDFs | Learning Teams methodology | Cultural aspects |

### B. Key Design Principles

1. **Parallel Over Sequential:** Always prefer parallel execution
2. **Evidence Over Opinion:** Every conclusion needs data
3. **Learning Over Blame:** Capture all paths, not just successful ones
4. **Simple Over Complex:** Start simple, complexify based on need
5. **Open Over Closed:** Default to transparency and open source

### C. Definition of Done

**For MVP Launch:**
- [ ] 10 different incident types successfully investigated
- [ ] 10 beta users actively using the system
- [ ] Complete documentation and quick-start guide
- [ ] Open source repository with CI/CD
- [ ] First case study published
- [ ] Clear metrics showing value

---

## Final Thoughts

Ivan, this is our blueprint. It's ambitious but achievable. The key is maintaining focus on the core value proposition: faster, scientific, transparent investigation that anyone can use.

Every feature in the MVP directly supports this goal. Everything else waits.

The technical decisions are made. The architecture is sound. The path is clear.

Let's build something that changes how our industry thinks about incidents - from problems to solve to opportunities to learn.

**Remember:** We're not building another monitoring tool. We're building the investigation platform that makes every engineer a detective, every incident a lesson, and every organization a learning machine.

---

**Document Version:** 1.0  
**Last Updated:** November 16, 2025  
**Next Review:** Week 1 Progress Check  
**Owner:** Ivan (Product Owner)

*"The best way to predict the future is to build it." - Let's build COMPASS together.*
