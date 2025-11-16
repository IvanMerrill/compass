# COMPASS Documentation

This directory contains all documentation for the COMPASS project.

---

## Directory Structure

### `/architecture/` - System Architecture Documents

Core architecture specifications and technical designs:

- `COMPASS_MVP_Architecture_Reference.md` - **Start here** for architecture overview
- `COMPASS_MVP_Technical_Design.md` - Detailed technical specifications
- `COMPASS_Scientific_Framework_DOCS.md` - Scientific methodology framework
- `COMPASS_Enterprise_Knowledge_Architecture.md` - Enterprise knowledge system
- `COMPASS_Interface_Architecture.md` - Human-AI interface design
- `COMPASS_Future_Proofing_Architecture.md` - Extensibility and scaling
- `investigation_learning_human_collaboration_architecture.md` - Full multi-agent architecture
- `COMPASS_Architecture_Evaluation.docx` - Architecture evaluation document

**Total**: 8 files

---

### `/product/` - Product Strategy & Requirements

Product vision, strategy, and specifications:

- `COMPASS_Product_Reference_Document_v1_1.md` - **Primary product spec** (latest version)
- `COMPASS_Product_Reference_Document.md` - Original product spec
- `COMPASS_Product_Strategy.md` - Go-to-market and pricing strategy

**Total**: 3 files

---

### `/guides/` - Build Guides & Workflows

Step-by-step guides for development:

- `COMPASS_MVP_Build_Guide.md` - **Start here** for building MVP
- `compass-day1-startup.md` - Day 1 setup guide
- `compass-day1-reconciled.md` - Reconciled day 1 guide with TDD
- `compass-tdd-workflow.md` - Test-driven development process
- `compass-claude-code-instructions.md` - Working with Claude Code
- `compass_enterprise_knowledge_guide.md` - Enterprise user guide (for Thimo)
- `claude.md` - Development principles and guidelines

**Total**: 7 files

---

### `/reference/` - Quick References & Indexes

Quick access documents and search tools:

- `COMPASS_CONVERSATIONS_INDEX.md` - **Searchable index** of all planning conversations
- `INDEXING_SYSTEM_SUMMARY.md` - How to use the conversation index
- `compass-quick-reference.md` - Quick reference guide
- `IMPLEMENTATION_SUMMARY.md` - Implementation summary
- `FRAMEWORK_FLOW_DIAGRAM.txt` - Visual investigation flow diagram
- `RECONCILIATION_SUMMARY.md` - Day 1 reconciliation notes
- `review_code.txt` - Code review notes

**Total**: 7 files

---

### `/research/` - Research Papers (PDFs)

Academic and industry research informing COMPASS design:

- `Designing_ICSBased_MultiAgent_AI_Systems_for_Incident_Investigation.pdf`
- `Evaluation_of_Learning_Teams_Versus_Root_Cause_154.pdf`
- `Oct23LVI008TheProblemwithRootCauseAnalysis.pdf`
- `AI_PostMortem_Generation_COMPASS.pdf`
- `AI_PostMortem_Learning_Culture_COMPASS.pdf`

**Total**: 5 files

---

## Quick Navigation

### For New Team Members

1. **Understand the product**: `product/COMPASS_Product_Reference_Document_v1_1.md`
2. **Learn the architecture**: `architecture/COMPASS_MVP_Architecture_Reference.md`
3. **Start building**: `guides/COMPASS_MVP_Build_Guide.md`

### For Finding Information

Use the conversation index to search all planning discussions:

```bash
grep -i "your_topic" reference/COMPASS_CONVERSATIONS_INDEX.md
```

See `reference/INDEXING_SYSTEM_SUMMARY.md` for detailed usage.

### For Specific Topics

- **Multi-Agent Design**: `architecture/investigation_learning_human_collaboration_architecture.md`
- **Scientific Method**: `architecture/COMPASS_SCIENTIFIC_FRAMEWORK_DOCS.md`
- **Enterprise Features**: `architecture/COMPASS_Enterprise_Knowledge_Architecture.md`
- **CLI Interface**: `architecture/COMPASS_Interface_Architecture.md`
- **TDD Workflow**: `guides/compass-tdd-workflow.md`
- **Learning Teams Research**: `research/Evaluation_of_Learning_Teams_Versus_Root_Cause_154.pdf`

---

## Documentation Statistics

- **Total Files**: 30
- **Architecture Docs**: 8
- **Product Docs**: 3
- **Guides**: 7
- **References**: 7
- **Research Papers**: 5

---

**Last Updated**: 2025-11-16
