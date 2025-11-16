# COMPASS MVP Technical Design Document
## Concrete Implementation Specifications

**Version:** 1.0  
**Date:** November 16, 2025  
**Purpose:** Detailed technical specifications for MVP implementation  
**Audience:** Development team and Claude Code

---

## Table of Contents

1. [System Components & APIs](#1-system-components--apis)
2. [Data Models & Schemas](#2-data-models--schemas)
3. [Investigation Workflow](#3-investigation-workflow)
4. [MCP Integration Specification](#4-mcp-integration-specification)
5. [CLI Command Structure](#5-cli-command-structure)
6. [Configuration Management](#6-configuration-management)
7. [State Management](#7-state-management)
8. [Deployment Configuration](#8-deployment-configuration)
9. [Implementation Checklist](#9-implementation-checklist)

---

## 1. System Components & APIs

### 1.1 Investigation Orchestrator

```python
class InvestigationOrchestrator:
    """Central coordinator for incident investigations"""
    
    def __init__(self, config: OrchestratorConfig):
        self.agents: Dict[str, ScientificAgent] = {}
        self.investigation_id = str(uuid.uuid4())
        self.state = InvestigationState()
        self.audit_trail = AuditTrail()
        self.cost_tracker = CostTracker()
        
    async def start_investigation(self, trigger: InvestigationTrigger) -> Investigation:
        """Entry point for new investigation"""
        # 1. Parse symptoms and determine relevant agents
        agents_to_spawn = self.determine_agents(trigger.symptoms)
        
        # 2. Initialize agents in parallel
        await self.spawn_agents(agents_to_spawn)
        
        # 3. Execute parallel observation phase
        observations = await self.parallel_observe(timeout=120)
        
        # 4. Generate hypotheses from all agents
        hypotheses = await self.collect_hypotheses()
        
        # 5. Rank by confidence
        ranked = self.rank_hypotheses(hypotheses)
        
        # 6. Present to human
        return Investigation(
            id=self.investigation_id,
            hypotheses=ranked,
            observations=observations,
            next_action="AWAIT_HUMAN_DECISION"
        )
    
    async def test_hypothesis(self, hypothesis_id: str) -> TestResult:
        """Attempt to disprove selected hypothesis"""
        hypothesis = self.state.get_hypothesis(hypothesis_id)
        agent = self.agents[hypothesis.agent_id]
        
        # Delegate to specialist agent for domain-specific testing
        result = await agent.attempt_falsification(hypothesis)
        
        self.audit_trail.record(
            action="HYPOTHESIS_TEST",
            hypothesis=hypothesis,
            result=result
        )
        
        return result
```

### 1.2 Agent API Contract

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class AgentInterface(ABC):
    """Contract all specialist agents must implement"""
    
    @abstractmethod
    async def observe(self, context: ObservationContext) -> List[Observation]:
        """Gather domain-specific observations"""
        pass
    
    @abstractmethod
    async def generate_hypotheses(self, observations: List[Observation]) -> List[Hypothesis]:
        """Generate testable hypotheses from observations"""
        pass
    
    @abstractmethod
    async def attempt_falsification(self, hypothesis: Hypothesis) -> FalsificationResult:
        """Try to disprove hypothesis with additional queries"""
        pass
    
    @abstractmethod
    def get_required_data_sources(self) -> List[str]:
        """Declare which MCP servers this agent needs"""
        pass
```

### 1.3 REST API Endpoints

```yaml
# FastAPI endpoints for external interfaces
endpoints:
  /api/v1/investigations:
    POST:
      description: Start new investigation
      request_body:
        schema: InvestigationTrigger
      response:
        schema: Investigation
    GET:
      description: List investigations
      parameters:
        - status: [active, completed, failed]
        - limit: integer
      response:
        schema: List[InvestigationSummary]
  
  /api/v1/investigations/{id}:
    GET:
      description: Get investigation details
      response:
        schema: Investigation
    
  /api/v1/investigations/{id}/hypotheses/{hypothesis_id}/test:
    POST:
      description: Test specific hypothesis
      response:
        schema: TestResult
  
  /api/v1/investigations/{id}/actions:
    POST:
      description: Execute mitigation action
      request_body:
        schema: MitigationAction
      response:
        schema: ActionResult
```

---

## 2. Data Models & Schemas

### 2.1 Core Investigation Models

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any

class InvestigationStatus(Enum):
    TRIGGERED = "triggered"
    OBSERVING = "observing"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    AWAITING_HUMAN = "awaiting_human"
    TESTING = "testing"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    FAILED = "failed"

@dataclass
class InvestigationTrigger:
    """How an investigation starts"""
    source: str  # "pagerduty", "manual", "slack", "api"
    service: str  # affected service name
    symptoms: List[str]  # ["high latency", "500 errors", "connection timeouts"]
    severity: str  # "P1", "P2", "P3"
    context: Dict[str, Any]  # additional context
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Observation:
    """Single observation from an agent"""
    agent_id: str
    observation_type: str  # "metric", "log", "trace", "config"
    source: str  # "prometheus:api_latency_p99"
    value: Any  # actual observed value
    interpretation: str  # human-readable interpretation
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    query_cost: float  # LLM token cost

@dataclass
class Hypothesis:
    """Testable theory about incident cause"""
    id: str
    agent_id: str
    statement: str  # "Database connection pool exhaustion"
    initial_confidence: float
    current_confidence: float
    supporting_observations: List[str]  # observation IDs
    falsification_tests: List[str]  # test names to run
    affected_systems: List[str]
    suggested_mitigation: Optional[str]
    status: HypothesisStatus

@dataclass
class FalsificationResult:
    """Result of attempting to disprove hypothesis"""
    hypothesis_id: str
    test_name: str
    expected_if_true: str
    observed: str
    disproven: bool
    confidence_adjustment: float  # how much to adjust confidence
    evidence: List[Evidence]
    reasoning: str
```

### 2.2 State Management Models

```python
@dataclass
class InvestigationState:
    """Complete state of an investigation"""
    investigation_id: str
    status: InvestigationStatus
    trigger: InvestigationTrigger
    active_agents: List[str]
    observations: List[Observation]
    hypotheses: List[Hypothesis]
    tested_hypotheses: List[str]
    human_decisions: List[HumanDecision]
    mitigation_actions: List[MitigationAction]
    audit_trail: List[AuditEntry]
    total_cost: float
    start_time: datetime
    end_time: Optional[datetime]
    
    def to_redis_dict(self) -> Dict:
        """Serialize for Redis storage"""
        return {
            'investigation_id': self.investigation_id,
            'status': self.status.value,
            'trigger': json.dumps(asdict(self.trigger)),
            'observations': json.dumps([asdict(o) for o in self.observations]),
            'hypotheses': json.dumps([asdict(h) for h in self.hypotheses]),
            # ... etc
        }
    
    @classmethod
    def from_redis_dict(cls, data: Dict) -> 'InvestigationState':
        """Deserialize from Redis"""
        return cls(
            investigation_id=data['investigation_id'],
            status=InvestigationStatus(data['status']),
            trigger=InvestigationTrigger(**json.loads(data['trigger'])),
            # ... etc
        )
```

### 2.3 Post-Mortem Schema

```python
@dataclass
class PostMortem:
    """Generated post-mortem document"""
    investigation_id: str
    incident_title: str
    executive_summary: str
    
    timeline: List[TimelineEntry]
    impact: ImpactAssessment
    
    root_cause: str  # The validated hypothesis
    contributing_factors: List[str]
    
    what_went_well: List[str]
    what_went_poorly: List[str]
    where_we_got_lucky: List[str]
    
    action_items: List[ActionItem]
    
    # All hypotheses including disproven ones
    hypotheses_tested: List[HypothesisSummary]
    
    lessons_learned: List[str]
    similar_incidents: List[str]  # IDs of similar past incidents
    
    def to_markdown(self) -> str:
        """Generate markdown document"""
        # Implementation here
        pass
```

---

## 3. Investigation Workflow

### 3.1 Complete Investigation Flow

```python
async def complete_investigation_flow(trigger: InvestigationTrigger):
    """End-to-end investigation workflow"""
    
    # 1. Initialize
    orchestrator = InvestigationOrchestrator(config)
    investigation = await orchestrator.start_investigation(trigger)
    
    # 2. Present hypotheses to human
    ui.display_hypotheses(investigation.hypotheses)
    
    # 3. Human selection loop
    while investigation.status != InvestigationStatus.RESOLVED:
        decision = await ui.await_human_decision()
        
        if decision.action == "TEST_HYPOTHESIS":
            result = await orchestrator.test_hypothesis(decision.hypothesis_id)
            
            if result.disproven:
                ui.display_message(f"Hypothesis disproven: {result.reasoning}")
                # Remove from list and show next
            else:
                ui.display_message(f"Hypothesis validated: {result.reasoning}")
                # Proceed with mitigation
                
        elif decision.action == "REQUEST_MORE_DATA":
            # Human provides additional context
            observations = await orchestrator.observe_with_context(decision.context)
            new_hypotheses = await orchestrator.regenerate_hypotheses(observations)
            
        elif decision.action == "EXECUTE_MITIGATION":
            result = await orchestrator.execute_mitigation(decision.mitigation)
            
            if result.successful:
                investigation.status = InvestigationStatus.RESOLVED
    
    # 4. Generate post-mortem
    post_mortem = await orchestrator.generate_post_mortem()
    await post_mortem.publish()
```

### 3.2 Parallel Agent Execution

```python
async def parallel_observe(agents: List[ScientificAgent], context: ObservationContext):
    """Execute all agents in parallel with timeout"""
    
    async def observe_with_timeout(agent: ScientificAgent):
        try:
            return await asyncio.wait_for(
                agent.observe(context),
                timeout=30.0  # 30 seconds per agent
            )
        except asyncio.TimeoutError:
            return ObservationError(
                agent_id=agent.agent_id,
                error="Timeout during observation"
            )
    
    # Launch all agents simultaneously
    tasks = [observe_with_timeout(agent) for agent in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    observations = []
    errors = []
    
    for result in results:
        if isinstance(result, ObservationError):
            errors.append(result)
        else:
            observations.extend(result)
    
    return observations, errors
```

---

## 4. MCP Integration Specification

### 4.1 MCP Server Configuration

```yaml
# config/mcp_servers.yaml
mcp_servers:
  prometheus:
    url: "${PROMETHEUS_URL}"
    auth:
      type: bearer
      token: "${PROMETHEUS_TOKEN}"
    capabilities:
      - query_metrics
      - query_range
      - get_labels
    
  loki:
    url: "${LOKI_URL}"
    auth:
      type: basic
      username: "${LOKI_USER}"
      password: "${LOKI_PASSWORD}"
    capabilities:
      - query_logs
      - query_range
      - get_labels
      - stream_logs
  
  tempo:
    url: "${TEMPO_URL}"
    capabilities:
      - query_traces
      - get_trace_by_id
      - search_traces
  
  grafana:
    url: "${GRAFANA_URL}"
    auth:
      type: api_key
      key: "${GRAFANA_API_KEY}"
    capabilities:
      - get_dashboards
      - get_annotations
      - execute_query
```

### 4.2 MCP Client Implementation

```python
class MCPClient:
    """Unified interface to all MCP servers"""
    
    def __init__(self, config_path: str = "config/mcp_servers.yaml"):
        self.servers = self._load_config(config_path)
        self.clients = {}
        self._initialize_clients()
    
    async def query_prometheus(self, query: str, time_range: TimeRange) -> PrometheusResult:
        """Query Prometheus for metrics"""
        client = self.clients['prometheus']
        
        params = {
            'query': query,
            'start': time_range.start.isoformat(),
            'end': time_range.end.isoformat(),
            'step': '30s'
        }
        
        response = await client.query_range(params)
        return PrometheusResult.from_response(response)
    
    async def query_loki(self, query: str, time_range: TimeRange) -> LokiResult:
        """Query Loki for logs"""
        client = self.clients['loki']
        
        params = {
            'query': query,
            'start': time_range.start_ns,
            'end': time_range.end_ns,
            'limit': 1000,
            'direction': 'backward'
        }
        
        response = await client.query_range(params)
        return LokiResult.from_response(response)
    
    async def query_tempo(self, service: str, operation: str, time_range: TimeRange) -> TempoResult:
        """Query Tempo for traces"""
        client = self.clients['tempo']
        
        params = {
            'service': service,
            'operation': operation,
            'start': time_range.start_us,
            'end': time_range.end_us,
            'limit': 20
        }
        
        response = await client.search_traces(params)
        return TempoResult.from_response(response)
```

### 4.3 Agent-Specific MCP Usage

```python
class DatabaseAgent(ScientificAgent):
    """Database specialist with MCP integration"""
    
    async def observe(self, context: ObservationContext) -> List[Observation]:
        observations = []
        
        # 1. Query connection pool metrics
        pool_query = f'''
            pg_stat_database_numbackends{{db="{context.service}"}} /
            pg_stat_database_max_connections{{db="{context.service}"}}
        '''
        pool_result = await self.mcp.query_prometheus(pool_query, context.time_range)
        
        if pool_result.value > 0.8:
            observations.append(Observation(
                agent_id=self.agent_id,
                observation_type="metric",
                source="prometheus:connection_pool",
                value=pool_result.value,
                interpretation=f"Connection pool at {pool_result.value*100:.1f}% capacity",
                confidence=0.9
            ))
        
        # 2. Check for slow queries in logs
        slow_query = f'''
            {{app="{context.service}"}} 
            |= "slow query" 
            | json 
            | duration > 1000
        '''
        slow_result = await self.mcp.query_loki(slow_query, context.time_range)
        
        if slow_result.count > 10:
            observations.append(Observation(
                agent_id=self.agent_id,
                observation_type="log",
                source="loki:slow_queries",
                value=slow_result.count,
                interpretation=f"Found {slow_result.count} slow queries",
                confidence=0.8
            ))
        
        # 3. Check for lock contention
        lock_query = f'pg_locks_count{{db="{context.service}",mode="ExclusiveLock"}}'
        lock_result = await self.mcp.query_prometheus(lock_query, context.time_range)
        
        if lock_result.value > 50:
            observations.append(Observation(
                agent_id=self.agent_id,
                observation_type="metric",
                source="prometheus:lock_contention",
                value=lock_result.value,
                interpretation=f"High lock contention: {lock_result.value} exclusive locks",
                confidence=0.85
            ))
        
        return observations
```

---

## 5. CLI Command Structure

### 5.1 Command Hierarchy

```bash
compass
â”œâ”€â”€ investigate      # Start new investigation
â”œâ”€â”€ status          # Check investigation status
â”œâ”€â”€ hypotheses      # List/test hypotheses
â”œâ”€â”€ execute         # Execute mitigation
â”œâ”€â”€ postmortem      # Generate post-mortem
â”œâ”€â”€ config          # Manage configuration
â”œâ”€â”€ learn           # Query learned patterns
â””â”€â”€ cost            # Check investigation costs
```

### 5.2 Command Specifications

```python
# cli/commands.py
import click
from rich.console import Console
from rich.table import Table
from rich.live import Live

console = Console()

@click.group()
def cli():
    """COMPASS - AI-powered incident investigation"""
    pass

@cli.command()
@click.argument('service')
@click.option('--symptom', '-s', multiple=True, help='Observed symptoms')
@click.option('--severity', '-p', default='P2', type=click.Choice(['P1', 'P2', 'P3']))
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode')
@click.option('--timeout', default=300, help='Investigation timeout in seconds')
def investigate(service, symptom, severity, interactive, timeout):
    """Start a new investigation"""
    
    # Create trigger
    trigger = InvestigationTrigger(
        source="cli",
        service=service,
        symptoms=list(symptom),
        severity=severity
    )
    
    # Start investigation
    with console.status("[bold green]Starting investigation...") as status:
        orchestrator = InvestigationOrchestrator(config)
        investigation = asyncio.run(orchestrator.start_investigation(trigger))
    
    # Display hypotheses
    table = Table(title="Generated Hypotheses")
    table.add_column("ID", style="cyan")
    table.add_column("Confidence", style="magenta")
    table.add_column("Hypothesis", style="white")
    table.add_column("Agent", style="green")
    
    for idx, hyp in enumerate(investigation.hypotheses):
        table.add_row(
            str(idx + 1),
            f"{hyp.current_confidence:.0%}",
            hyp.statement,
            hyp.agent_id
        )
    
    console.print(table)
    
    if interactive:
        # Enter interactive mode
        enter_interactive_mode(investigation)
    else:
        console.print(f"\nInvestigation ID: {investigation.id}")
        console.print("Run 'compass status <id>' to check progress")

def enter_interactive_mode(investigation):
    """Interactive investigation mode"""
    
    while investigation.status != InvestigationStatus.RESOLVED:
        # Show prompt
        console.print("\n[bold]Actions:[/bold]")
        console.print("  1. Test hypothesis")
        console.print("  2. Request more data")
        console.print("  3. Execute mitigation")
        console.print("  4. Show observations")
        console.print("  5. Exit")
        
        choice = console.input("\n[yellow]Choose action: [/yellow]")
        
        if choice == "1":
            hyp_id = console.input("Hypothesis number to test: ")
            test_hypothesis_interactive(investigation, int(hyp_id) - 1)
        elif choice == "2":
            request_more_data_interactive(investigation)
        elif choice == "3":
            execute_mitigation_interactive(investigation)
        elif choice == "4":
            show_observations(investigation)
        elif choice == "5":
            break

@cli.command()
@click.argument('investigation_id')
def status(investigation_id):
    """Check investigation status"""
    # Implementation here
    pass

@cli.command()
@click.argument('investigation_id')
@click.argument('hypothesis_id', type=int)
def test(investigation_id, hypothesis_id):
    """Test a specific hypothesis"""
    # Implementation here
    pass
```

---

## 6. Configuration Management

### 6.1 Main Configuration Structure

```yaml
# config/compass.yaml
compass:
  environment: ${COMPASS_ENV:development}
  log_level: ${LOG_LEVEL:INFO}
  
  investigation:
    max_parallel_agents: 5
    observation_timeout_seconds: 120
    hypothesis_generation_timeout: 30
    max_hypotheses_per_agent: 3
    min_confidence_threshold: 0.5
    max_investigation_cost: 10.0  # dollars
    
  agents:
    enabled:
      - database
      - network
      - application
      - infrastructure
      - tracing
    
    database:
      data_sources:
        - prometheus
        - loki
      queries:
        connection_pool: "pg_stat_database_numbackends"
        slow_queries: "duration > 1000"
        lock_contention: "pg_locks_count"
      
  llm:
    default_provider: ${LLM_PROVIDER:openai}
    
    providers:
      openai:
        api_key: ${OPENAI_API_KEY}
        model: "gpt-4-turbo-preview"
        temperature: 0.3
        max_tokens: 4000
        
      anthropic:
        api_key: ${ANTHROPIC_API_KEY}
        model: "claude-3-opus"
        temperature: 0.3
        max_tokens: 4000
        
      ollama:
        url: ${OLLAMA_URL:http://localhost:11434}
        model: "llama2:70b"
        temperature: 0.3
        
    token_limits:
      per_hypothesis: 1000
      per_observation: 500
      per_investigation: 50000
      
  storage:
    redis:
      url: ${REDIS_URL:redis://localhost:6379}
      ttl_seconds: 86400  # 24 hours
      
    postgres:
      url: ${DATABASE_URL:postgresql://compass:compass@localhost/compass}
      pool_size: 10
      
  integrations:
    slack:
      enabled: ${SLACK_ENABLED:false}
      bot_token: ${SLACK_BOT_TOKEN}
      app_token: ${SLACK_APP_TOKEN}
      default_channel: ${SLACK_CHANNEL:#incidents}
    
    pagerduty:
      enabled: ${PAGERDUTY_ENABLED:false}
      api_key: ${PAGERDUTY_API_KEY}
      integration_key: ${PAGERDUTY_INTEGRATION_KEY}
```

### 6.2 Agent Configuration

```yaml
# config/agents/database.yaml
database_agent:
  min_confidence_threshold: 0.65
  time_budget_seconds: 45
  
  observation_queries:
    connection_saturation:
      prometheus: |
        pg_stat_database_numbackends{db="$SERVICE"} / 
        pg_stat_database_max_connections{db="$SERVICE"}
      threshold: 0.8
      confidence: 0.9
      
    slow_query_detection:
      loki: |
        {app="$SERVICE"} |= "slow query" | json | duration > 1000
      threshold: 10  # more than 10 slow queries
      confidence: 0.8
      
    lock_contention:
      prometheus: |
        pg_locks_count{db="$SERVICE",mode="ExclusiveLock"}
      threshold: 50
      confidence: 0.85
      
  disproof_strategies:
    - name: "check_connection_pool_history"
      description: "Verify pool was actually saturated"
      requires: ["prometheus"]
      
    - name: "correlate_with_traffic"
      description: "Check if issue correlates with traffic spike"
      requires: ["prometheus"]
      
    - name: "check_recent_changes"
      description: "Look for recent schema or config changes"
      requires: ["github", "loki"]
```

---

## 7. State Management

### 7.1 Redis State Store

```python
class InvestigationStateStore:
    """Manage investigation state in Redis"""
    
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.ttl = 86400  # 24 hours
    
    async def save_state(self, state: InvestigationState):
        """Save investigation state"""
        key = f"investigation:{state.investigation_id}"
        data = state.to_redis_dict()
        
        # Save as hash with TTL
        await self.redis.hset(key, mapping=data)
        await self.redis.expire(key, self.ttl)
        
        # Add to active investigations set
        await self.redis.sadd("active_investigations", state.investigation_id)
    
    async def get_state(self, investigation_id: str) -> Optional[InvestigationState]:
        """Retrieve investigation state"""
        key = f"investigation:{investigation_id}"
        data = await self.redis.hgetall(key)
        
        if not data:
            return None
            
        return InvestigationState.from_redis_dict(data)
    
    async def update_status(self, investigation_id: str, status: InvestigationStatus):
        """Update investigation status"""
        key = f"investigation:{investigation_id}"
        await self.redis.hset(key, "status", status.value)
        
        # Publish status change event
        await self.redis.publish(
            f"investigation:{investigation_id}:status",
            status.value
        )
    
    async def subscribe_to_updates(self, investigation_id: str):
        """Subscribe to investigation updates"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"investigation:{investigation_id}:*")
        
        async for message in pubsub.listen():
            yield message
```

### 7.2 Event Streaming

```python
class EventStream:
    """Real-time event streaming for UI updates"""
    
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.subscribers = {}
    
    async def emit_event(self, investigation_id: str, event: Event):
        """Emit event to all subscribers"""
        channel = f"events:{investigation_id}"
        payload = json.dumps({
            'type': event.type,
            'data': event.data,
            'timestamp': event.timestamp.isoformat()
        })
        
        await self.redis.publish(channel, payload)
    
    async def subscribe(self, investigation_id: str, callback):
        """Subscribe to investigation events"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"events:{investigation_id}")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                event = json.loads(message['data'])
                await callback(event)
```

---

## 8. Deployment Configuration

### 8.1 Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY compass/ ./compass/
COPY config/ ./config/

# Set environment variables
ENV PYTHONPATH=/app
ENV COMPASS_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "compass.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.2 Kubernetes Manifests

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compass
  namespace: compass
spec:
  replicas: 3
  selector:
    matchLabels:
      app: compass
  template:
    metadata:
      labels:
        app: compass
    spec:
      containers:
      - name: compass
        image: compass:latest
        ports:
        - containerPort: 8000
        env:
        - name: COMPASS_ENV
          value: "production"
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: compass-secrets
              key: redis-url
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: compass-secrets
              key: database-url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: compass-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: compass
  namespace: compass
spec:
  selector:
    app: compass
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 8.3 Tilt Configuration

```python
# Tiltfile
load('ext://restart_process', 'docker_build_with_restart')

# Build Docker image
docker_build_with_restart(
    'compass',
    '.',
    dockerfile='Dockerfile',
    entrypoint=['python', '-m', 'compass.api'],
    only=['./compass', './config'],
    live_update=[
        sync('./compass', '/app/compass'),
        sync('./config', '/app/config'),
    ]
)

# Deploy to local k8s
k8s_yaml([
    'k8s/namespace.yaml',
    'k8s/secrets.yaml',
    'k8s/deployment.yaml',
    'k8s/service.yaml',
])

# Configure port forwarding
k8s_resource('compass', port_forwards='8000:8000')

# Add Redis for local development
docker_compose('docker-compose.dev.yaml')

# Local resource dependencies
k8s_resource('compass', resource_deps=['redis', 'postgres'])

# Open UI on start
local_resource(
    'open-ui',
    'sleep 5 && open http://localhost:8000',
    resource_deps=['compass']
)
```

---

## 9. Implementation Checklist

### Week 1-2: Foundation
- [ ] Set up project structure
- [ ] Configure Tilt environment
- [ ] Implement `ScientificAgent` base class
- [ ] Create `InvestigationOrchestrator`
- [ ] Set up Redis state management
- [ ] Create basic CLI structure
- [ ] Implement audit trail logging

### Week 3-4: First Agents
- [ ] Implement DatabaseAgent with MCP
- [ ] Implement ApplicationAgent with MCP  
- [ ] Create hypothesis generation logic
- [ ] Build confidence scoring algorithm
- [ ] Add cost tracking
- [ ] Test parallel execution

### Week 5-6: Hypothesis Framework
- [ ] Build falsification engine
- [ ] Implement evidence chain tracking
- [ ] Create hypothesis ranking algorithm
- [ ] Add multi-hypothesis testing
- [ ] Implement disproof strategies

### Week 7-8: Learning System
- [ ] Set up PostgreSQL with pgvector
- [ ] Implement pattern recognition
- [ ] Create similar incident detection
- [ ] Build feedback incorporation
- [ ] Add pattern reuse logic

### Week 9-10: User Experience
- [ ] Complete CLI commands
- [ ] Add rich terminal output
- [ ] Implement interactive mode
- [ ] Create Slack integration
- [ ] Build post-mortem generator

### Week 11-12: Production Ready
- [ ] Finalize Docker image
- [ ] Complete Kubernetes manifests
- [ ] Add comprehensive error handling
- [ ] Performance optimization
- [ ] Documentation and quick-start guide
- [ ] Beta user onboarding

---

## Appendix A: Example Investigation Session

```bash
$ compass investigate payment-service -s "high latency" -s "timeout errors" -i

ðŸ” Starting investigation for payment-service...

â³ Observing (5 agents in parallel)...
  âœ“ Database Agent: 3 observations
  âœ“ Network Agent: 2 observations  
  âœ“ Application Agent: 4 observations
  âœ“ Infrastructure Agent: 1 observation
  âœ“ Tracing Agent: 2 observations

ðŸ“Š Generated Hypotheses:
â”â”â”â”â”³â”â”â”â”â”â”â”â”â”â”â”â”³â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”³â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”“
â”ƒ # â”ƒ Confidence â”ƒ Hypothesis                             â”ƒ Agent           â”ƒ
â”¡â”â”â”â•‡â”â”â”â”â”â”â”â”â”â”â”â•‡â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â•‡â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”©
â”‚ 1 â”‚ 85%        â”‚ Database lock contention on orders     â”‚ database        â”‚
â”‚ 2 â”‚ 72%        â”‚ Payment gateway latency spike          â”‚ network         â”‚
â”‚ 3 â”‚ 61%        â”‚ Memory pressure causing GC pauses      â”‚ infrastructure  â”‚
â”‚ 4 â”‚ 45%        â”‚ Distributed trace shows retry storm    â”‚ tracing         â”‚
â””â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

Actions:
  1. Test hypothesis
  2. Request more data
  3. Execute mitigation
  4. Show observations
  5. Exit

Choose action: 1
Hypothesis number to test: 1

ðŸ§ª Testing: Database lock contention on orders table

Attempting to disprove hypothesis...
  âœ“ Checking lock wait times... HIGH (>5s average)
  âœ“ Correlating with latency spikes... STRONG (r=0.92)
  âœ— Looking for contradicting evidence... NONE FOUND

âœ… Hypothesis VALIDATED with 92% confidence

Suggested mitigation: Kill long-running transaction (PID: 45231)
Execute mitigation? (y/n): y

âš¡ Executing: Kill transaction PID 45231...
âœ“ Transaction killed successfully
âœ“ Lock contention resolved
âœ“ Latency returning to normal

ðŸ“ Generating post-mortem...
âœ“ Post-mortem saved: PM-2025-11-16-001.md

Investigation complete! Total time: 3m 42s | Cost: $0.47
```

---

**This document provides the concrete technical specifications needed to build the COMPASS MVP. Each section contains implementation-ready details that can be directly translated into code.**
