# AgentInterOp - Multi-Agent Healthcare Interoperability Platform

A healthcare interoperability platform supporting dual protocols for agent-to-agent communication, real-time FHIR integration, and AI-powered processing.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com)
[![A2A Protocol](https://img.shields.io/badge/A2A-0.2.9-orange.svg)](https://github.com/google/A2A)

## Features

### Core Capabilities

- **Dual Protocol Support**: A2A (Agent-to-Agent JSON-RPC 2.0) and MCP (Model Context Protocol)
- **Real-time FHIR Integration**: Live connectivity to FHIR R4 servers for healthcare data
- **AI-Powered Processing**: Claude integration for narrative-to-JSON conversion and analysis
- **Scenario Engine**: Pluggable scenarios (BCSE, Clinical Trial, Prior Auth, CQL Measure)
- **Agent Card Discovery**: Standards-compliant `.well-known/agent-card.json` implementation

### Specialized Agents

- **Colonoscopy Scheduling Agent**: Automates 40+ question intake forms, insurance verification, and appointment booking
- **Clinical Informaticist Agent**: CQL measure development and quality measure authoring
- **Administrator Agent**: Benefits eligibility and prior authorization processing
- **Applicant Agent**: Patient-side conversation handling

### Supported Scenarios

| Scenario | Endpoint | Description |
|----------|----------|-------------|
| Colonoscopy Scheduling | `/api/colonoscopy-scheduler/a2a` | Automates complex scheduling workflow |
| BCSE | `/api/bridge/demo/a2a` | Breast Cancer Screening Eligibility |
| CQL Measure | `/api/bridge/cql-measure/a2a` | Clinical Quality Language measure development |
| Clinical Trial | `/api/bridge/clinical-trial/a2a` | Patient enrollment eligibility |
| Prior Auth | `/api/bridge/prior-auth/a2a` | Prior authorization processing |

## Quick Start

### 1. Install

```bash
git clone https://github.com/aks129/AgentInterOp.git
cd AgentInterOp
pip install -e .
```

### 2. Configure Environment

Create a `.env` file:

```bash
# Required for AI features
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional
SESSION_SECRET=your_secure_secret_here
PUBLIC_BASE_URL=https://your-domain.com
```

### 3. Run

```bash
# Development
make run
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production
gunicorn --bind 0.0.0.0:8000 app.main:app
```

### 4. Access

- **Main UI**: `http://localhost:8000`
- **Agent 2 Agent Chat**: `http://localhost:8000/experimental/banterop`
- **API Docs**: `http://localhost:8000/docs`
- **Agent Card**: `http://localhost:8000/.well-known/agent-card.json`

## Calling Agents via A2A Protocol

### Basic Request

```bash
curl -X POST "http://localhost:8000/api/bridge/cql-measure/a2a" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Build breast cancer screening CQL measure"}]
      }
    }
  }'
```

### Response Format

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "id": "task-id",
    "status": {"state": "input-required"},
    "history": [
      {"role": "user", "parts": [{"kind": "text", "text": "..."}]},
      {"role": "agent", "parts": [{"kind": "text", "text": "Built CQL measure..."}]}
    ],
    "artifacts": [
      {
        "kind": "file",
        "file": {
          "name": "BreastCancerScreening.cql",
          "mimeType": "text/cql",
          "bytes": "base64-encoded-content"
        }
      }
    ]
  }
}
```

### A2A Methods

| Method | Description |
|--------|-------------|
| `message/send` | Send message, get response |
| `message/stream` | Send message, get SSE stream |
| `tasks/get` | Get task status by ID |
| `tasks/resubscribe` | Resubscribe to task updates |

## FHIR Integration

Connect to FHIR R4 servers for patient data:

```bash
# Test servers
https://hapi.fhir.org/baseR4
https://r4.smarthealthit.org
```

Supported operations:

- `GET /metadata` - Server capabilities
- `GET /Patient?name=John` - Patient search
- `GET /Patient/123/$everything` - Complete patient bundle

## Development

```bash
# Install dev dependencies
make dev

# Code quality
make format     # black, ruff, isort
make lint       # ruff check, flake8
make typecheck  # mypy

# Testing
make test       # pytest
make smoke      # A2A smoke tests
```

### Project Structure

```text
app/
├── main.py              # FastAPI entry point
├── config.py            # Pydantic configuration
├── agents/              # Agent implementations
│   ├── administrator.py
│   ├── applicant.py
│   ├── clinical_informaticist.py
│   └── colonoscopy_scheduler.py
├── protocols/           # A2A, MCP implementations
├── scenarios/           # Healthcare scenarios
├── routers/             # FastAPI route handlers
├── banterop_ui/         # Agent 2 Agent Chat UI backend
├── fhir/                # FHIR server integration
├── llm/                 # Claude AI integration
└── web/                 # Frontend assets
    └── experimental/
        └── banterop/    # Agent 2 Agent Chat UI

api/index.py             # Vercel serverless entry
```

## Deployment

### Vercel (Serverless)

Pre-configured for Vercel:

- Routes configured in `vercel.json`
- Entry point: `api/index.py`
- Set environment variables in Vercel dashboard

**Live Demo**: <https://agent-inter-op.vercel.app>

### Docker

```bash
docker build -t agentinterop .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=your_key agentinterop
```

## API Endpoints

### Health & Status

| Endpoint | Description |
|----------|-------------|
| `GET /healthz` | Health check |
| `GET /version` | Version info |
| `GET /api/selftest` | Self-test suite |
| `GET /.well-known/agent-card.json` | Agent discovery |

### Agent 2 Agent Chat UI API

| Endpoint | Description |
|----------|-------------|
| `POST /api/experimental/banterop/scenario/load` | Load scenario |
| `POST /api/experimental/banterop/run/start` | Start conversation |
| `POST /api/experimental/banterop/a2a/proxy` | Proxy A2A requests |
| `GET /api/experimental/banterop/llm/status` | Claude status |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | For AI features | Claude API key |
| `SESSION_SECRET` | No | Session security (auto-generated) |
| `PUBLIC_BASE_URL` | No | Base URL for agent cards |
| `APP_ENV` | No | Set to `vercel` for serverless |

## License

MIT License - see LICENSE file for details.
