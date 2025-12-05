# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the Application

```bash
# Development (recommended) - FastAPI with hot reload
make run
# or directly:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production - Flask/gunicorn
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

### Development Tools

```bash
# Install dependencies (Python 3.11+ required)
pip install -e .
# or with dev dependencies:
pip install -e ".[dev]"

# Use Makefile targets (recommended)
make format    # black, ruff, isort
make lint      # ruff check, flake8
make typecheck # mypy
make test      # pytest
make smoke     # A2A smoke tests against local server

# Manual formatting (line length: 100)
black --line-length 100 app/ tests/
isort --profile black --line-length 100 app/ tests/
ruff check app/ tests/
```

### Testing

```bash
# Run all tests
make test
# or: pytest tests/ -v

# Run single test file
pytest tests/test_specific.py -v

# With coverage
pytest --cov=app --cov-report=html

# Smoke tests (requires running server)
make smoke
# or: bash tools/smoke_a2a.sh http://localhost:8000
```

## High-Level Architecture

### Multi-Agent Interoperability Platform

This is a healthcare interoperability testing platform supporting dual protocols for agent-to-agent communication:

**Core Components:**

- **Dual Protocol Support**: A2A (Agent-to-Agent JSON-RPC) and MCP (Model Context Protocol)
- **Specialized Agents**: Applicant, Administrator, Clinical Informaticist agents with distinct roles
- **FHIR Integration**: Real-time connectivity to FHIR R4 servers for healthcare data
- **Scenario Engine**: Pluggable scenarios (BCSE, Clinical Trial, Prior Auth, CQL Measure, etc.)
- **AI-Powered Processing**: Claude integration for narrative-to-JSON conversion

### Project Structure

```text
app/
├── main.py                 # FastAPI application entry point
├── config.py               # Pydantic configuration models
├── engine.py               # Conversation management engine
├── agents/                 # Agent implementations (administrator, applicant, clinical_informaticist)
├── protocols/              # Protocol implementations (A2A, MCP)
├── scenarios/              # Healthcare scenarios (BCSE, clinical trial, etc.)
├── routers/                # FastAPI route handlers
├── banterop_ui/            # Experimental Banterop UI backend
├── eligibility/            # Eligibility checking engines
├── fhir/                   # FHIR server integration
├── ingest/                 # FHIR-to-payload mapping
├── llm/                    # Claude AI integration
├── store/                  # Data persistence (memory, file)
└── web/                    # Frontend templates and static assets
    └── experimental/
        └── banterop/       # Banterop V2 UI (HTML/JS)

main.py                     # Flask-compatible WSGI entry point
api/index.py                # Vercel serverless entry point
```

### Protocol Architecture

**A2A Protocol**: JSON-RPC 2.0 with Server-Sent Events

- Methods: `message/send`, `message/stream`, `tasks/get`, `tasks/cancel`, `tasks/resubscribe`
- Endpoints: `/api/bridge/{scenario}/a2a`

**MCP Protocol**: Tool-based interactions

- Tools: `begin_chat_thread`, `send_message_to_chat_thread`, `check_replies`
- Endpoints: `/api/mcp/{scenario}/`

### Configuration System

Configuration is managed through Pydantic models in `app/config.py`:

- Runtime config stored in `app/config.runtime.json` (gitignored)
- Environment variables loaded from `.env` file
- Scenarios dynamically registered in `app/scenarios/registry.py`

### FHIR Integration

The platform connects to live FHIR servers for real healthcare data testing:

- Server capabilities discovery
- Patient search and `$everything` operations
- Automatic payload mapping per scenario
- Bearer token authentication support

### Agent Card Discovery

Implements `.well-known/agent-card.json` for external agent discovery with:

- Protocol version and transport preferences
- Skill definitions and endpoints
- Base64-encoded configuration payloads

### Key Environment Variables

- `ANTHROPIC_API_KEY`: Required for AI narrative processing
- `SESSION_SECRET`: Flask session security (auto-generated if not set)
- `APP_ENV=vercel`: Changes config file location for serverless deployment
- `PUBLIC_BASE_URL`: Base URL for agent card generation

### Entry Points

- **Development**: Use `app/main.py` (FastAPI) - `make run`
- **Production**: Use gunicorn with `main:app`
- **Vercel**: Serverless deployment via `api/index.py`

### Testing Endpoints

- Health: `/healthz`, `/health`
- Self-test: `/api/selftest`
- Version: `/version`
- Agent card: `/.well-known/agent-card.json`
- Banterop UI: `/experimental/banterop/`

### Calling Agents via A2A

```bash
curl -X POST "http://localhost:8000/api/bridge/cql-measure/a2a" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"Build breast cancer screening CQL measure"}]}}}'
```

Response contains `history[]` (messages) and `artifacts[]` (generated files like CQL).
