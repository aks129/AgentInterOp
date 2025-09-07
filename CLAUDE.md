# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the Application
```bash
# Flask development server (main entry point)
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app

# Alternative FastAPI server
python app/main.py
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Simple start scripts
python start.py
python simple_main.py
```

### Development Tools
```bash
# Install dependencies (Python 3.11+ required)
pip install -e .
# or for API-only dependencies
pip install -r api/requirements.txt

# Code formatting
black --line-length 100 .
isort --profile black --line-length 100 .
flake8 --max-line-length 100

# Testing
pytest
pytest --cov=app --cov-report=html
```

## High-Level Architecture

### Multi-Agent Interoperability Platform
This is a healthcare interoperability testing platform supporting dual protocols for agent-to-agent communication:

**Core Components:**
- **Dual Protocol Support**: A2A (Agent-to-Agent JSON-RPC) and MCP (Model Context Protocol)
- **Specialized Agents**: Applicant Agent and Administrator Agent with distinct roles
- **FHIR Integration**: Real-time connectivity to FHIR R4 servers for healthcare data
- **Scenario Engine**: Pluggable scenarios (BCSE, Clinical Trial, Prior Auth, etc.)
- **AI-Powered Processing**: Claude integration for narrative-to-JSON conversion

### Project Structure
```
app/
├── main.py                 # FastAPI application entry point
├── config.py              # Pydantic configuration models
├── engine.py              # Conversation management engine
├── agents/                 # Agent implementations (administrator, applicant)
├── protocols/             # Protocol implementations (A2A, MCP)
├── scenarios/             # Healthcare scenarios (BCSE, clinical trial, etc.)
├── eligibility/           # Eligibility checking engines
├── fhir/                  # FHIR server integration
├── ingest/               # FHIR-to-payload mapping
├── llm/                  # Claude AI integration
├── store/                # Data persistence (memory, file)
└── web/                  # Frontend templates and static assets

main.py                    # Flask-compatible WSGI entry point
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

### Entry Points
- **Development**: Use `main.py` (Flask) or `app/main.py` (FastAPI)
- **Production**: Use gunicorn with `main:app`
- **Vercel**: Serverless deployment via `api/` directory structure

### Testing Endpoints
- Health: `/healthz`, `/health`  
- Self-test: `/api/selftest`
- Version: `/version`
- Agent card: `/.well-known/agent-card.json`

The system is designed for healthcare interoperability testing and supports partner integrations through standardized agent cards and protocol endpoints.