# COMPASS

**Comprehensive Observability Multi-Agent Platform for Adaptive System Solutions**

AI-powered incident investigation platform that reduces MTTR by 67-90% using parallel OODA loops, ICS principles, and scientific methodology.

---

## Project Status

🏗️ **Planning Complete** - Ready to build MVP

**Last Updated**: 2025-11-16

---

## Quick Start

For new team members or contributors:

1. **Start here**: [`docs/product/COMPASS_Product_Reference_Document_v1_1.md`](docs/product/COMPASS_Product_Reference_Document_v1_1.md)
2. **Understand the architecture**: [`docs/architecture/COMPASS_MVP_Architecture_Reference.md`](docs/architecture/COMPASS_MVP_Architecture_Reference.md)
3. **Build guide**: [`docs/guides/COMPASS_MVP_Build_Guide.md`](docs/guides/COMPASS_MVP_Build_Guide.md)
4. **Development workflow**: [`docs/guides/compass-tdd-workflow.md`](docs/guides/compass-tdd-workflow.md)

---

## Project Structure

```
compass/
├── docs/                      # All documentation
│   ├── architecture/          # System architecture documents
│   ├── product/               # Product strategy and requirements
│   ├── guides/                # Build guides and workflows
│   ├── reference/             # Quick references and indexes
│   └── research/              # Research papers (PDFs)
│
├── src/                       # Source code (in development)
│   ├── compass/               # Main Python package
│   │   ├── core/             # OODA loop, scientific framework
│   │   ├── agents/           # Agent implementations
│   │   ├── cli/              # CLI interface
│   │   ├── api/              # API server
│   │   └── integrations/     # MCP integrations
│   └── tests/                 # Test suite
│
├── planning/                  # Planning conversations
│   ├── conversations/         # Original HTML chats
│   └── transcripts/          # Extracted text transcripts
│
├── examples/                  # Example configurations and templates
│   ├── configurations/        # Sample YAML configs
│   └── templates/            # Agent templates
│
├── deployment/                # Deployment configurations
│   ├── k8s/                  # Kubernetes manifests
│   └── docker/               # Docker files
│
└── scripts/                   # Utility scripts
```

---

## Core Concepts

### What is COMPASS?

COMPASS uses AI agents organized according to Incident Command System (ICS) principles to investigate incidents using parallel OODA loops and scientific methodology.

**Key Differentiators**:
- **Parallel OODA Loops**: 5+ agents test hypotheses simultaneously
- **Scientific Rigor**: Systematic hypothesis disproof before human escalation
- **Learning Culture**: Learning Teams methodology vs traditional RCA
- **Human-in-the-Loop**: Level 1 autonomy - AI proposes, humans decide

### Technology Stack

- **Language**: Python only (readability over complexity)
- **Database**: PostgreSQL + pgvector
- **Observability**: LGTM stack (Loki, Grafana, Tempo, Mimir)
- **Deployment**: Kubernetes (Tilt for local dev)
- **LLM**: Provider agnostic (OpenAI, Anthropic, Copilot, Ollama)

### Architecture Highlights

**Agent Hierarchy** (ICS-based):
```
Orchestrator
    ├── Database Manager → Workers
    ├── Network Manager → Workers
    ├── Application Manager → Workers
    └── Infrastructure Manager → Workers
```

**OODA Loop Phases**:
1. **Observe**: Parallel data gathering
2. **Orient**: Hypothesis generation and ranking
3. **Decide**: Human decision points
4. **Act**: Evidence gathering and hypothesis testing

---

## Documentation Map

### Essential Reading (Start Here)

1. **Product Overview**
   - [`COMPASS_Product_Reference_Document_v1_1.md`](docs/product/COMPASS_Product_Reference_Document_v1_1.md) - Complete product specification

2. **Architecture**
   - [`COMPASS_MVP_Architecture_Reference.md`](docs/architecture/COMPASS_MVP_Architecture_Reference.md) - MVP architecture
   - [`COMPASS_MVP_Technical_Design.md`](docs/architecture/COMPASS_MVP_Technical_Design.md) - Technical design details

3. **Build Guides**
   - [`COMPASS_MVP_Build_Guide.md`](docs/guides/COMPASS_MVP_Build_Guide.md) - Step-by-step build instructions
   - [`compass-tdd-workflow.md`](docs/guides/compass-tdd-workflow.md) - TDD development process

### Quick References

- [`compass-quick-reference.md`](docs/reference/compass-quick-reference.md) - Quick reference guide
- [`COMPASS_CONVERSATIONS_INDEX.md`](docs/reference/COMPASS_CONVERSATIONS_INDEX.md) - Searchable index of all planning conversations
- [`INDEXING_SYSTEM_SUMMARY.md`](docs/reference/INDEXING_SYSTEM_SUMMARY.md) - How to use the conversation index

### Specialized Topics

**Scientific Framework**:
- [`COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md`](docs/architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md)
- [`compass_scientific_framework.py`](src/compass/core/compass_scientific_framework.py) - Core implementation

**Enterprise Features**:
- [`COMPASS_Enterprise_Knowledge_Architecture.md`](docs/architecture/COMPASS_Enterprise_Knowledge_Architecture.md)
- [`compass_enterprise_knowledge_guide.md`](docs/guides/compass_enterprise_knowledge_guide.md) - Enterprise user guide

**Human-AI Interface**:
- [`COMPASS_Interface_Architecture.md`](docs/architecture/COMPASS_Interface_Architecture.md)

**Research Papers** (in `docs/research/`):
- ICS-Based Multi-Agent AI Systems for Incident Investigation
- Evaluation of Learning Teams vs Root Cause Analysis
- Problems with Root Cause Analysis

---

## Development Status

### ✅ Completed
- [x] Product vision and requirements
- [x] Complete architecture design
- [x] Scientific framework specification
- [x] Multi-agent coordination design
- [x] Enterprise knowledge integration design
- [x] CLI interface design
- [x] Prototype code (scientific framework, database agent)
- [x] Comprehensive documentation
- [x] Test framework design

### 🏗️ In Progress
- [ ] MVP implementation (not started)

### 📋 Roadmap

**Phase 1: Foundation** (Weeks 1-2)
- Basic LGTM integration
- Single agent (database)
- CLI interface
- Cost tracking

**Phase 2: Trust** (Weeks 3-4)
- Hypothesis confidence scoring
- Evidence linking
- Graceful failure handling

**Phase 3: Value** (Weeks 5-6)
- Pattern learning
- Personal runbooks
- Metrics tracking

---

## Finding Information

### Search Planning Conversations

All planning conversations are indexed and searchable:

```bash
# Search the conversation index
grep -i "topic_name" docs/reference/COMPASS_CONVERSATIONS_INDEX.md

# Example: Find information about cost management
grep -i "cost" docs/reference/COMPASS_CONVERSATIONS_INDEX.md
```

See [`docs/reference/INDEXING_SYSTEM_SUMMARY.md`](docs/reference/INDEXING_SYSTEM_SUMMARY.md) for detailed usage.

### Documentation by Topic

- **Getting Started**: `docs/guides/`
- **Architecture Details**: `docs/architecture/`
- **Product Strategy**: `docs/product/`
- **Research Background**: `docs/research/`
- **Planning History**: `planning/`

---

## Key Design Principles

From [`docs/guides/claude.md`](docs/guides/claude.md):

1. **Production-First**: Every component production-ready from inception
2. **Test-Driven Development**: TDD rigorously from day 1
3. **OODA Loop Focus**: Optimize for iteration speed over perfect analysis
4. **Scientific Method**: Systematically disprove hypotheses before presenting
5. **Human Authority**: Humans decide, AI advises and accelerates
6. **Cost Management**: Token budget caps, transparent pricing
7. **Learning Culture**: Focus on contributing causes, not blame

---

## Contributing

See development guides:
- [`compass-tdd-workflow.md`](docs/guides/compass-tdd-workflow.md) - Test-driven development
- [`compass-claude-code-instructions.md`](docs/guides/compass-claude-code-instructions.md) - Claude Code workflow
- [`compass-day1-startup.md`](docs/guides/compass-day1-startup.md) - Day 1 setup guide

---

## License

[To be determined]

---

## Contact

[To be added]

---

**Ready to build!** See [`docs/guides/COMPASS_MVP_Build_Guide.md`](docs/guides/COMPASS_MVP_Build_Guide.md) to get started.
