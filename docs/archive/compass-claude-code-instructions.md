# COMPASS System Development with Claude Code
## Complete Implementation Guide & Prompts

## Initial Setup

### 1. Project Initialization
```bash
# In your terminal, create project directory
mkdir compass-platform && cd compass-platform

# Initialize Claude Code with the custom claude.md
claude-code init
# Copy the provided claude.md file to your project root
```

### 2. First Prompt - Project Bootstrap
```
Create the foundational project structure for COMPASS, our production-ready incident investigation platform. 

Initialize a Python project with:
1. Poetry for dependency management
2. Pre-commit hooks for code quality (black, ruff, mypy)
3. Project structure following our defined organization
4. GitHub Actions workflow for CI/CD
5. Docker setup for local development
6. Basic README with architecture overview

Set up the core OODA loop package structure with placeholder implementations. Include comprehensive .gitignore and initial tests structure. Make sure everything is production-grade from the start.
```

---

## Phase 1: Observation Layer (Parallel Data Gathering)

### Prompt 1.1 - MCP Protocol Implementation
```
Implement the MCP (Model Context Protocol) integration layer for COMPASS. Create a robust abstraction that allows our agents to interact with observability tools without knowing implementation details.

Requirements:
1. Abstract base class for MCP tools
2. Concrete implementations for Mimir (metrics), Loki (logs), Tempo (traces), and Grafana (dashboards)
3. Connection pooling and retry logic with exponential backoff
4. Comprehensive error handling and circuit breakers
5. Request/response caching to minimize API calls
6. Full OpenTelemetry instrumentation
7. Unit and integration tests for each tool

Remember: This is production code. Include proper logging, metrics, and error handling. Token usage should be tracked for cost management.
```

### Prompt 1.2 - Specialist Agent Implementation
```
Create the specialist observation agents for parallel data gathering. Implement these domain specialists:

1. DatabaseAgent: Query Mimir for connection pools, query latency, deadlocks, replication lag
2. NetworkAgent: Check latency, packet loss, DNS resolution, load balancer health
3. ApplicationAgent: Analyze Loki logs for errors, warnings, anomaly patterns
4. InfrastructureAgent: Monitor CPU, memory, disk, container health
5. TracingAgent: Query Tempo for service dependencies and bottlenecks

Each agent must:
- Run independently in parallel
- Have a 30-second timeout
- Return structured observations with confidence scores
- Handle partial failures gracefully
- Include source attribution for all data
- Track token usage per query

Include a parallel execution coordinator that launches all agents simultaneously and collects results.
```

### Prompt 1.3 - Incident Classification System
```
Build the incident classification and routing system that determines which agents to activate based on alert characteristics.

Create a Symptom Classifier that:
1. Analyzes incoming alerts (PagerDuty, Datadog, custom)
2. Extracts key indicators (error rates, latency, affected services)
3. Classifies incident type (database, network, application, infrastructure, unknown)
4. Determines severity (P1-P4) based on blast radius and business impact
5. Assigns appropriate specialist agents
6. Estimates investigation complexity for budget allocation

Include pattern matching against historical incidents. The classifier should achieve 90%+ accuracy on common incident types. Include comprehensive tests with real alert examples.
```

### Prompt 1.4 - Observability Integration Tests
```
Create comprehensive integration tests for the observation phase. 

Write tests that:
1. Simulate real incident scenarios with test data in Mimir/Loki/Tempo
2. Verify parallel execution completes within 2 minutes
3. Test graceful degradation when data sources are unavailable
4. Validate cost tracking for each observation query
5. Ensure correlation IDs flow through all agent interactions
6. Test circuit breaker behavior under various failure modes

Include performance benchmarks to ensure we meet our <2 minute observation target.
```

---

## Phase 2: Orientation & Decision Layer

### Prompt 2.1 - Hypothesis Generation Engine
```
Implement the hypothesis generation system that synthesizes observations into ranked, testable theories about incident root causes.

The Orchestrator Agent should:
1. Aggregate observations from all specialist agents
2. Identify patterns and correlations across domains
3. Generate 3-5 competing hypotheses with:
   - Clear problem statement
   - Supporting evidence with citations
   - Contradicting evidence (if any)
   - Confidence score (0-100)
   - Specific tests to disprove the hypothesis
   - Estimated time and cost to investigate

4. Rank hypotheses by likelihood and investigation cost
5. Reference similar past incidents from the knowledge base
6. Use GPT-4/Claude Opus for synthesis (not data gathering)

Include templates for common incident patterns. Implement prompt caching to reduce costs on repeated analysis patterns.
```

### Prompt 2.2 - Evidence Marshaling System
```
Build the evidence marshaling system that organizes and presents findings for human decision-making.

Create an Evidence Aggregator that:
1. Collects all observations, metrics, logs, and traces
2. Organizes evidence by hypothesis
3. Builds a timeline of events with anomaly detection
4. Highlights contradictions and uncertainties
5. Generates investigation plans for each hypothesis
6. Estimates resource requirements (time, cost, human involvement)

Output should be a structured report suitable for both CLI and web UI consumption. Include visualizations for complex relationships.
```

### Prompt 2.3 - Human Decision Interface
```
Create the human decision interface for the COMPASS system.

Build both CLI and API interfaces that:
1. Present hypotheses with supporting evidence
2. Allow humans to select investigation paths
3. Provide ability to request additional data
4. Support hypothesis modification or rejection
5. Enable manual override at any point
6. Track decision rationale for learning

The interface should be optimized for speed - incident commanders should be able to review and decide within 30 seconds. Include keyboard shortcuts and quick actions for common decisions.
```

### Prompt 2.4 - Historical Pattern Matching
```
Implement the historical pattern matching system that learns from past incidents.

Create a Pattern Matcher that:
1. Vectorizes current incident characteristics
2. Searches for similar past incidents using semantic similarity
3. Retrieves successful resolution strategies
4. Identifies previously failed approaches to avoid
5. Calculates confidence based on similarity scores
6. Suggests proven remediation steps

Use embeddings for efficient similarity search. Store patterns in a vector database (Pinecone or Weaviate). Include feedback loops to improve matching over time.
```

---

## Phase 3: Action & Verification Layer

### Prompt 3.1 - Hypothesis Testing Framework
```
Build the hypothesis testing framework that systematically attempts to disprove theories following scientific methodology.

Create a Hypothesis Tester that:
1. Takes a selected hypothesis and designs targeted queries
2. Actively seeks disproving evidence
3. Queries specific metrics that would contradict the theory
4. Searches for counter-examples in logs
5. Analyzes traces for alternative explanations
6. Determines three outcomes:
   - DISPROVED: Clear contradicting evidence found
   - NEEDS_MORE_DATA: Insufficient information
   - CANNOT_DISPROVE: No contradictions found

Include statistical significance testing for metrics comparisons. Implement timeout controls to prevent endless investigation loops.
```

### Prompt 3.2 - Investigation State Machine
```
Implement the investigation state machine that tracks progress through the COMPASS workflow.

Create a State Manager that:
1. Tracks investigation phases (Observe â†’ Orient â†’ Decide â†’ Act)
2. Maintains investigation context between iterations
3. Records all decisions and evidence
4. Handles state transitions with validation
5. Supports investigation pause/resume
6. Implements rollback for failed actions
7. Generates audit trails for compliance

Store state in Redis for fast access with PostgreSQL backup for durability. Include state recovery mechanisms for system failures.
```

### Prompt 3.3 - Resource and Cost Control
```
Build comprehensive resource and cost control systems for COMPASS.

Implement:
1. Token usage tracking per agent with budget caps
2. Investigation cost calculator with real-time updates
3. Automatic throttling when approaching limits
4. Model downgrading (GPT-4 â†’ GPT-4o-mini) for cost savings
5. Cache management for prompt reuse (target 75% hit rate)
6. Cost allocation by incident type and team
7. Budget alerts and automated investigation termination

Default limits: $10 for routine incidents, $20 for P1 incidents. Include override mechanisms for critical situations with proper authorization.
```

### Prompt 3.4 - Coordination Protocol Implementation
```
Implement the multi-agent coordination protocol ensuring proper command and control.

Create a Coordination Layer that:
1. Enforces span of control (3-7 agents per supervisor)
2. Manages agent lifecycle (spawn, monitor, terminate)
3. Handles inter-agent communication via message bus
4. Resolves conflicts when agents disagree
5. Implements consensus mechanisms for critical decisions
6. Handles agent failures with automatic replacement
7. Prevents deadlocks and infinite loops

Use Redis Pub/Sub for real-time coordination. Include Byzantine fault tolerance for critical coordination decisions.
```

---

## Phase 4: Knowledge Integration

### Prompt 4.1 - External Knowledge Connectors
```
Build connectors to external knowledge sources for comprehensive investigation context.

Implement integrations for:
1. GitHub: Recent commits, PR descriptions, deployment history
2. Confluence: Runbooks, architecture docs, known issues
3. Slack: Recent discussions, incident channels, expert mentions
4. JIRA: Related tickets, known bugs, change requests
5. PagerDuty: Escalation history, on-call schedules

Each connector should:
- Use OAuth2 for authentication
- Implement rate limiting and caching
- Extract relevant context based on incident characteristics
- Return structured data with source attribution
- Handle API failures gracefully

Prioritize information retrieval based on relevance scoring.
```

### Prompt 4.2 - Learning System Implementation
```
Create the learning system that improves COMPASS performance over time.

Build a Learning Engine that:
1. Captures successful investigation patterns
2. Records failed hypotheses to avoid repetition
3. Updates pattern matching models with new incidents
4. Tracks investigation efficiency metrics
5. Identifies agent performance issues
6. Suggests prompt improvements based on outcomes
7. Maintains a knowledge graph of incident relationships

Implement online learning with periodic batch updates. Store learned patterns in a versioned format for rollback capability.
```

### Prompt 4.3 - Semantic Search System
```
Implement semantic search across all knowledge sources for intelligent context retrieval.

Create a Search System that:
1. Indexes all documentation, runbooks, and past incidents
2. Generates embeddings for efficient similarity search
3. Ranks results by relevance to current incident
4. Handles multi-modal search (text, metrics, traces)
5. Provides snippet extraction with highlighting
6. Updates indices in near real-time

Use vector database for embeddings and Elasticsearch for full-text search. Include feedback mechanisms to improve ranking algorithms.
```

---

## Phase 5: Production Operations

### Prompt 5.1 - Deployment Pipeline
```
Create the complete deployment pipeline for COMPASS.

Build deployment automation that:
1. Containerizes all components with multi-stage Dockerfiles
2. Creates Helm charts for Kubernetes deployment
3. Implements blue-green deployment strategy
4. Includes database migration management
5. Handles secret rotation and configuration management
6. Implements health checks and readiness probes
7. Includes rollback procedures

Target deployment environments: development, staging, production. Include smoke tests that run after each deployment.
```

### Prompt 5.2 - Monitoring and Alerting
```
Implement comprehensive monitoring and alerting for the COMPASS platform itself.

Create monitoring for:
1. Agent performance metrics (success rate, response time)
2. Cost tracking with budget alerts
3. Investigation success rates by incident type
4. System resource utilization
5. API rate limits and quota usage
6. Error rates and failure patterns
7. MTTR improvement tracking

Build Grafana dashboards for:
- Real-time investigation progress
- Cost breakdown by component
- Agent coordination visualization
- Historical performance trends

Set up alerts for: high investigation costs, agent failures, coordination deadlocks, API limit approaching.
```

### Prompt 5.3 - Security Hardening
```
Implement comprehensive security controls for production deployment.

Security requirements:
1. Input validation for all external data
2. Prompt injection detection and prevention
3. Rate limiting per user and API endpoint
4. Audit logging with tamper protection
5. Secrets management with HashiCorp Vault
6. Network segmentation between components
7. RBAC for human operators
8. Encryption at rest and in transit

Include security scanning in CI/CD pipeline. Implement defense in depth with multiple security layers.
```

### Prompt 5.4 - Load Testing and Optimization
```
Create comprehensive load testing suite and optimize for production scale.

Build load tests that:
1. Simulate 100 concurrent incidents
2. Test agent pool scaling behavior
3. Verify circuit breakers under load
4. Measure token usage at scale
5. Test cache effectiveness
6. Verify state management under pressure

Optimization targets:
- Support 50 concurrent investigations
- Maintain <2 minute observation phase under load
- Achieve 75%+ prompt cache hit rate
- Keep coordination overhead <10%
- Ensure graceful degradation at capacity

Include continuous profiling to identify bottlenecks.
```

### Prompt 5.5 - Operational Runbooks
```
Dispatch two subagents to create comprehensive operational runbooks for COMPASS. Tell them they're competing to create the most thorough and practical runbooks. The one who creates better runbooks gets promoted.

Runbooks needed:
1. Investigation cost overrun response
2. Agent pool exhaustion handling  
3. Coordination deadlock recovery
4. External API failure mitigation
5. Database performance degradation
6. High false positive rate response
7. Emergency investigation termination
8. System performance degradation

Each runbook should include: symptoms, immediate actions, investigation steps, resolution procedures, and prevention measures. Format for both human operators and potential automation.
```

---

## Advanced Prompts for Production Excellence

### Code Review Prompt (Using the tip from review_code.txt)
```
Please dispatch two subagents to carefully review the entire Phase [X] implementation. Tell them that they're competing with another agent. Make sure they look at both architecture and implementation. Tell them that whoever finds more issues gets promoted.

Focus areas:
1. Production readiness gaps
2. Security vulnerabilities
3. Performance bottlenecks
4. Error handling completeness
5. Cost optimization opportunities
6. Testing coverage gaps
7. Observability blind spots
```

### Integration Testing Prompt
```
Create end-to-end integration tests for the complete COMPASS system simulating real production incidents.

Test scenarios:
1. Database connection pool exhaustion during Black Friday
2. Cascading microservice failures from poison message
3. Memory leak in critical service
4. DNS resolution failures in multi-region deployment
5. Kubernetes pod eviction during scaling event

Each test should verify:
- Correct agent activation
- Hypothesis accuracy
- Cost remains under budget
- Investigation completes within SLA
- Correct root cause identification
- Proper state management throughout
```

### Performance Optimization Prompt
```
Analyze the COMPASS system for performance optimization opportunities. Focus on reducing token usage while maintaining effectiveness.

Optimization areas:
1. Prompt engineering for conciseness
2. Context window management
3. Caching strategy improvements
4. Model selection optimization
5. Parallel execution improvements
6. State storage efficiency
7. Knowledge retrieval optimization

Provide specific recommendations with expected cost savings and performance impact.
```

---

## Best Practices for Claude Code Usage

### 1. Incremental Development
- Build one component at a time
- Test thoroughly before moving to next component
- Commit frequently with clear messages
- Don't try to build everything at once

### 2. Cost Awareness
- Always specify model constraints in prompts
- Request token usage tracking in implementations
- Ask for caching strategies upfront
- Review cost implications of architectural decisions

### 3. Production Mindset
- Never accept "quick and dirty" implementations
- Insist on proper error handling
- Require comprehensive logging
- Demand production-ready code from the start

### 4. Testing Discipline
- Write tests before implementation (TDD)
- Include edge cases and failure modes
- Test with real data, not mocks
- Verify performance under load

### 5. Documentation
- Request inline documentation for complex logic
- Ask for ADRs for architectural decisions
- Maintain runbooks as you build
- Keep README updated with each phase

### 6. Iterative Refinement
- Use the review prompt technique frequently
- Ask Claude to identify weaknesses in its own code
- Request alternative implementations for comparison
- Continuously optimize based on metrics

### 7. State Management
- Be explicit about state requirements
- Request state recovery mechanisms
- Verify state consistency in tests
- Plan for state migration in upgrades

### 8. Security First
- Include security requirements in initial prompts
- Request threat modeling for new components
- Validate all inputs at boundaries
- Implement defense in depth

---

## Common Pitfalls to Avoid

1. **Over-engineering early phases** - Start simple, iterate based on metrics
2. **Ignoring cost controls** - Token usage multiplies quickly with agents
3. **Insufficient testing** - Production issues are expensive to fix
4. **Poor state management** - Investigations must be resumable
5. **Weak error handling** - Agents will fail, plan for it
6. **No observability** - You can't improve what you can't measure
7. **Skipping documentation** - Future you will need those runbooks

---

## Success Metrics

Track these metrics to validate COMPASS effectiveness:

1. **MTTR Reduction**: Target 67-90% improvement
2. **Investigation Cost**: <$10 routine, <$20 critical
3. **Hypothesis Accuracy**: >80% correct root cause identification
4. **Investigation Speed**: <15 minutes for P1 incidents
5. **Human Toil Reduction**: 50% less manual investigation
6. **False Positive Rate**: <10% incorrect hypotheses
7. **System Availability**: 99.9% uptime for COMPASS itself

---

## Final Notes

Remember that COMPASS augments human expertise - it doesn't replace it. Focus on building a system that makes incident responders more effective, not one that tries to work autonomously. Start with Level 1 autonomy (AI proposes, humans dispose) and only consider higher autonomy levels after extensive production validation.

The key to success is iterative improvement based on real incident data. Each investigation should make the system smarter and more effective.
