# COMPASS Product Reference Document
## Comprehensive Observability Multi-Agent Platform for Adaptive System Solutions

**Version:** 1.0  
**Date:** November 16, 2025  
**Status:** Product Definition - Ready for Implementation  
**Audience:** Engineering Teams, Architects, Product Owners  

---

## Executive Summary

COMPASS is an AI-powered incident investigation platform that transforms how engineers diagnose and learn from production incidents. By orchestrating specialized AI agents following proven Incident Command System (ICS) principles and scientific methodology, COMPASS reduces Mean Time to Resolution (MTTR) by 67-90% while building a culture of continuous learning.

Unlike traditional observability tools that overwhelm engineers with raw data, COMPASS acts as an intelligent investigation assistant that systematically generates and tests hypotheses, gathering evidence from across the entire observability stack. Every investigation follows scientific rigor with complete audit trails, making the system suitable for SOC2, ISO27001, and other regulatory compliance requirements.

**Core Innovation:** COMPASS democratizes incident investigation expertise. A junior engineer can conduct investigations with the thoroughness of a senior SRE, while experienced engineers save hours on routine investigations, focusing instead on system improvements.

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
- **Compresses investigation time** from hours to minutes
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

### 2.2 Scientific Methodology

**Principle:** Every hypothesis must be testable and falsifiable. Agents attempt to disprove before accepting.

**Implementation:**
- Generate 3-5 competing hypotheses
- Actively seek contradicting evidence
- Track confidence scores based on evidence
- Document all tested paths (including dead ends)
- Complete audit trail from observation to conclusion

**Rationale:** Prevents confirmation bias, ensures rigorous investigation, enables learning from failures.

### 2.3 Contributing Causes Over Root Cause

**Principle:** Incidents have multiple contributing factors across system levels, not single root causes.

**Implementation:**
- Analyze six system levels (regulatory, organizational, technical management, work environment, human-system interface, equipment/technology)
- Generate Contributing Causes Map
- Focus on system improvements, not individual blame
- Follow Learning Teams methodology (114% more improvement actions than RCA)

**Rationale:** Research shows this approach generates 57% more system-focused improvements.

### 2.4 Progressive Complexity

**Principle:** Simple to start, powerful when needed.

**Implementation:**
- Natural language interface for beginners
- Command-line options for power users
- Progressive disclosure of information
- Adaptive response formatting
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

### 3.2 Agent Hierarchy (ICS-Based)

```
Orchestrator (Incident Commander)
â”œâ”€â”€ Safety Officer (monitors for dangerous actions)
â”œâ”€â”€ Liaison Officer (coordinates external resources)
â””â”€â”€ Investigation Team
    â”œâ”€â”€ Database Agent
    â”œâ”€â”€ Network Agent  
    â”œâ”€â”€ Application Agent
    â”œâ”€â”€ Infrastructure Agent
    â””â”€â”€ Tracing Agent
```

### 3.3 OODA Loop Execution

Each investigation phase follows Observe â†’ Orient â†’ Decide â†’ Act:

- **Observe:** Parallel data gathering (<2 minutes vs 15-20 manual)
- **Orient:** Synthesize observations into hypotheses
- **Decide:** Human selects hypothesis to pursue
- **Act:** Gather evidence to test/disprove hypothesis

---

## 4. MVP Features (Months 1-3)

### 4.1 Core Investigation Engine

**Feature:** Multi-agent parallel investigation system

**Capabilities:**
- Spawn 5 specialist agents (Database, Network, Application, Infrastructure, Tracing)
- Query LGTM stack via MCP (Loki, Grafana, Tempo, Mimir)
- Execute investigations in <2 minutes for observation phase
- Generate 3-5 ranked hypotheses with confidence scores

**Done When:**
- Can complete full OODA cycle for P1 incident
- Hypothesis confidence scores correlate with correctness >70%
- All agent queries execute in parallel
- Complete audit log of investigation steps

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

### 4.3 Natural Language Interface

**Feature:** Conversational interaction for all skill levels

**Capabilities:**
- Start investigation with "Help! Payment service is down!"
- Ask follow-up questions naturally
- Progressive information disclosure
- Context-aware responses
- No need to know PromQL/LogQL

**Done When:**
- Non-technical user can start investigation
- System interprets panic/urgent language correctly
- Graceful handling of ambiguous requests
- Clear next-step guidance always available

### 4.4 Cost Management System

**Feature:** Transparent tracking and control of AI costs

**Capabilities:**
- Real-time token usage tracking
- Per-investigation budget limits ($5 default)
- Cost attribution by hypothesis/agent
- Automatic optimization for expensive operations
- Clear cost visibility in UI

**Done When:**
- Never exceeds budget without permission
- Cost displayed for every investigation
- Can predict investigation cost before starting
- Optimization reduces costs by >30% over naive approach

### 4.5 Post-Mortem Generation

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

### 4.6 Local Deployment

**Feature:** Run on laptop or personal cloud

**Capabilities:**
- Docker container packaging
- Ollama integration for local LLM
- SQLite for local knowledge storage
- 30-minute setup to first investigation
- No external dependencies required

**Done When:**
- Single docker-compose up starts system
- Works with 8GB RAM laptop
- Complete data isolation
- No network calls except to observability stack

---

## 5. Future Features (Post-MVP)

### 5.1 Phase 2: Team Collaboration (Months 4-6)

**Shared Knowledge Base**
- Team-specific pattern library
- Collaborative post-mortem editing
- Shared investigation views
- Team runbook encoding

**Slack Integration**
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

**Extensibility Framework**
- Plugin architecture for new agents
- Custom MCP server SDK
- Webhook integrations
- REST API for third-party tools

**Compliance & Security**
- RBAC with SSO/SAML
- Audit log shipping
- Data residency controls
- Encrypted knowledge storage

### 5.3 Phase 4: Advanced Capabilities (Year 2)

**Predictive Investigation**
- Pre-incident pattern detection
- Proactive hypothesis generation
- Risk scoring for changes
- Capacity planning insights

**Learning Optimization**
- Embedding-based similarity matching
- Cross-incident clustering
- Automated improvement tracking
- Cultural change metrics

---

## 6. User Experience

### 6.1 Primary Personas

**Junior Engineer (0-2 years)**
- Needs: Guidance through investigation process
- Interface: Natural language chat
- Value: Conducts senior-level investigations

**Senior Engineer (5+ years)**
- Needs: Speed and efficiency
- Interface: Command-line + shortcuts
- Value: 70% time savings on routine investigations

**On-Call Engineer**
- Needs: Fast resolution at 3 AM
- Interface: Slack + mobile-friendly web
- Value: Reduce stress, faster resolution

**Engineering Manager**
- Needs: Team learning and metrics
- Interface: Dashboard + reports
- Value: Improved team capability, reduced MTTR

### 6.2 User Journey

```
Alert Fires â†’ Slack Notification â†’ Start Investigation
     â†“
"@compass investigate payment-service high latency"
     â†“
COMPASS: "I see payment-service latency increased 300% at 
2:14 AM. I'm investigating across all systems..."
     â†“
[2 minutes later]
     â†“
COMPASS: "I found 3 likely causes:
1. (85% confidence) Database connection pool exhaustion
2. (60% confidence) Upstream API throttling  
3. (45% confidence) Memory pressure on pods

Which should I investigate first?"
     â†“
Engineer: "Check the database theory"
     â†“
COMPASS: [Attempts to disprove, finds supporting evidence]
"Confirmed: Connection pool maxed at 100, queries queuing.
Recent deploy changed connection timeout. 
Recommended action: Increase pool size or revert deployment."
```

### 6.3 Interface Principles

- **No Training Required:** Anyone can type "help"
- **Progressive Disclosure:** Show simple first, details on demand  
- **Blameless Language:** "What happened" not "who did it"
- **Visual Investigation Map:** See all paths explored
- **Complete Transparency:** Every decision explained

---

## 7. Technical Implementation

### 7.1 Technology Stack

**Core Platform:**
- Python 3.11+ (async/await for parallel execution)
- FastAPI for REST endpoints
- Redis for investigation state
- PostgreSQL for knowledge base (team+)
- Docker/Kubernetes deployment

**AI/ML Components:**
- LangChain for agent orchestration
- OpenAI/Anthropic/Ollama for LLM
- Sentence-transformers for similarity
- Chroma/Pinecone for vector storage

**Integrations:**
- MCP for tool connections
- Prometheus client for metrics
- Slack SDK for chat interface
- Confluence API for documentation

### 7.2 Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Agent Framework** | Custom Python | Need fine control over scientific method |
| **LLM Strategy** | Provider-agnostic | Enterprises have existing AI contracts |
| **State Management** | Event streaming | Enable real-time updates and audit |
| **Knowledge Storage** | Hierarchical SQLiteâ†’PostgreSQL | Scale from personal to team |
| **Deployment** | Container-first | Simplify adoption across environments |

### 7.3 Performance Requirements

- **Investigation Start:** <5 seconds from trigger
- **Observation Phase:** <2 minutes for full scan
- **Hypothesis Generation:** <30 seconds
- **Post-Mortem Generation:** <10 minutes
- **Concurrent Investigations:** 10+ per instance
- **Data Retention:** 90 days investigation history

---

## 8. Implementation Roadmap

### 8.1 Month 1: Foundation

**Week 1-2: Core Architecture**
- [ ] ScientificAgent base class
- [ ] Investigation state machine
- [ ] OODA loop controller
- [ ] Cost tracking system

**Week 3-4: Agent Implementation**
- [ ] Database Agent with Mimir integration
- [ ] Application Agent with Loki integration
- [ ] Network Agent with Mimir integration
- [ ] Basic Orchestrator

### 8.2 Month 2: Intelligence Layer

**Week 5-6: Hypothesis System**
- [ ] Hypothesis generation
- [ ] Confidence scoring
- [ ] Falsification framework
- [ ] Evidence tracking

**Week 7-8: Learning System**
- [ ] Pattern recognition
- [ ] Knowledge persistence
- [ ] Similar incident matching
- [ ] Feedback loop

### 8.3 Month 3: User Experience

**Week 9-10: Interface**
- [ ] Natural language processor
- [ ] Slack integration
- [ ] Web UI (basic)
- [ ] Command-line interface

**Week 11-12: Post-Mortem & Polish**
- [ ] Post-mortem generator
- [ ] Docker packaging
- [ ] Documentation
- [ ] Quick-start guide

---

## 9. Success Metrics

### 9.1 Quantitative Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **MTTR Reduction** | 67-90% | Time from alert to resolution |
| **Investigation Time** | <5 minutes | Start to first hypothesis |
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
- Zero critical bugs in first month
- 99% uptime

**User Success:**
- 10 active beta users
- 50% use it for every incident
- <30 minutes to first investigation
- Positive feedback on ease of use

**Business Success:**
- 3 customer testimonials
- 1 published case study
- Clear path to 100 users
- Defined pricing model

---

## 10. Risks and Mitigations

### 10.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **LLM Costs Explode** | High | Medium | Hard budget limits, optimization, caching |
| **Hallucination** | High | Low | Scientific method, falsification, audit trails |
| **Integration Complexity** | Medium | High | Start with LGTM only, add incrementally |
| **Performance Issues** | Medium | Medium | Async operations, caching, load testing |

### 10.2 Adoption Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Learning Curve** | High | Low | Natural language, progressive disclosure |
| **Trust in AI** | High | Medium | Transparency, audit trails, human control |
| **Cultural Resistance** | Medium | Medium | Blameless focus, emphasize learning |
| **Tool Fatigue** | Medium | High | Replace investigation work, not add to it |

### 10.3 Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Compliance Concerns** | High | Low | SOC2 design, audit trails, human decisions |
| **Competitive Response** | Medium | High | Fast execution, enterprise features |
| **Pricing Pressure** | Medium | Medium | Clear ROI, usage-based model |
| **Support Burden** | Low | Medium | Self-service, good docs, community |

---

## 11. Competitive Differentiation

### 11.1 Unique Advantages

**Scientific Rigor**
- Only solution using falsification methodology
- Complete investigation transparency
- Audit-ready documentation

**Cultural Transformation**  
- Learning Teams methodology built-in
- Contributing causes over root cause
- Blameless by design

**Extensibility**
- MCP servers for any data source
- Plugin architecture for agents
- Enterprise knowledge injection

**Deployment Flexibility**
- Personal â†’ Team â†’ Enterprise growth path
- Local-first privacy option
- LLM-agnostic architecture

### 11.2 Competitive Moat

1. **Network Effects:** More investigations â†’ better patterns â†’ faster resolution
2. **Switching Costs:** Accumulated knowledge and patterns
3. **Enterprise Integration:** Deep embedding in incident process
4. **Cultural Lock-in:** Teams adopt Learning Teams methodology

---

## 12. Go-to-Market Strategy

### 12.1 Landing Motion

**Target:** Individual frustrated engineers
**Channel:** GitHub, Reddit, Hacker News
**Message:** "Investigate incidents in 2 minutes, not 2 hours"
**CTA:** "30-minute setup, free forever for individuals"

### 12.2 Expansion Motion  

**Target:** Teams with on-call rotation
**Channel:** Internal champion referral
**Message:** "Your whole team investigates like your best engineer"
**CTA:** "Free trial for teams under 10"

### 12.3 Enterprise Motion

**Target:** VP Engineering/CTO
**Channel:** Case studies, analyst reports
**Message:** "67-90% MTTR reduction, build learning culture"
**CTA:** "See ROI calculator"

---

## 13. Open Questions for Resolution

### 13.1 Product Decisions Needed

1. **Free Tier Limits:** How many investigations/month for free?
2. **Team Size Definition:** When does team become enterprise?
3. **Data Retention:** How long to keep investigation history?
4. **Compliance Scope:** Which certifications to pursue first?

### 13.2 Technical Decisions Needed  

1. **LLM Selection:** Default to which provider?
2. **Vector Database:** Chroma vs Pinecone vs pgvector?
3. **Deployment Target:** Kubernetes required or optional?
4. **Language Support:** Python only or add Go/Rust?

### 13.3 Business Decisions Needed

1. **Pricing Model:** Per-seat vs per-investigation vs hybrid?
2. **Open Source Strategy:** What to open, what to keep proprietary?
3. **Partnership Strategy:** Integrate with or compete with APM vendors?
4. **Support Model:** Community vs paid support tiers?

---

## Conclusion

COMPASS represents a fundamental shift in how organizations approach incident investigation. By combining proven emergency management frameworks with modern AI capabilities and scientific methodology, we're not just reducing MTTR â€“ we're transforming engineering culture.

The MVP scope is deliberately constrained to prove core value: fast, scientific, transparent investigation that anyone can use. Every feature directly supports the goal of democratizing incident investigation expertise while building organizational learning capabilities.

Success means engineers spend less time fighting tools and more time improving systems. It means every incident becomes a learning opportunity, not a blame exercise. It means junior engineers can investigate with senior-level thoroughness, while senior engineers can focus on system improvements rather than routine investigations.

This is not another monitoring tool. This is the investigation platform that makes every engineer a detective, every incident a lesson, and every organization a learning machine.

**Next Steps:**
1. Review and approve MVP scope
2. Begin Month 1 implementation
3. Recruit 10 beta users
4. Start building in public for feedback

---

*"The best investigation is one that teaches us something new about our systems, not one that finds someone to blame."*

---

**Document Version History:**
- v1.0 (2025-11-16): Initial product reference document

**Related Documents:**
- `compass_architecture.txt` - Technical architecture details
- `investigation_learning_human_collaboration_architecture.md` - Learning system design
- `COMPASS_Architecture_Evaluation.docx` - Extensibility assessment
- `COMPASS_Product_Strategy.md` - Go-to-market strategy
