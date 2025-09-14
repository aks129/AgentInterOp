# AgentInterOp - Multi-Agent Healthcare Interoperability Platform

A comprehensive healthcare interoperability testing platform supporting dual protocols for agent-to-agent communication, real-time FHIR integration, AI-powered processing, and advanced decision transparency.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com)
[![A2A Protocol](https://img.shields.io/badge/A2A-0.2.9-orange.svg)](https://github.com/pathbird/agent-to-agent-protocol)

## 🚀 Features

### Core Capabilities
- **Dual Protocol Support**: A2A (Agent-to-Agent JSON-RPC) and MCP (Model Context Protocol)
- **Real-time FHIR Integration**: Live connectivity to FHIR R4 servers for healthcare data
- **AI-Powered Processing**: Claude integration for narrative-to-JSON conversion and analysis
- **Scenario Engine**: Pluggable scenarios (BCSE, Clinical Trial, Prior Auth, etc.)
- **Decision Transparency**: Complete audit trail with "Prove It" functionality
- **Agent Card Discovery**: Standards-compliant `.well-known/agent-card.json` implementation

### Experimental Features 🧪
- **Banterop-style UI**: Console interface for scenario testing with remote agents
- **Smart Scheduling Links**: SMART on FHIR appointment discovery and booking
- **Claude Analysis**: AI-powered conversation summaries and guideline rationale
- **Room Export/Import**: Share conversation contexts across systems

### Supported Healthcare Scenarios
- **BCSE**: Benefits Coverage Support Eligibility (breast cancer screening)
- **Clinical Trial**: Patient enrollment and eligibility assessment
- **Referral Specialist**: Provider referral workflows
- **Prior Authorization**: Prior auth request processing
- **Custom**: Configurable scenarios for specific use cases

## 🏃 Quick Start

### Environment Setup

1. **Clone and Install**:
```bash
git clone <repository-url>
cd AgentInterOp
pip install -e .
```

2. **Configure Environment** - Create `.env` file:
```bash
# Required for AI features
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Session security (auto-generated if not set)
SESSION_SECRET=your_secure_secret_here

# Optional: Public base URL for Agent Card discovery
PUBLIC_BASE_URL=https://your-domain.com
```

3. **Start the Server**:
```bash
# Development (recommended)
make run
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

4. **Access the Application**:
- **Main UI**: `http://localhost:8000`
- **Experimental Banterop UI**: `http://localhost:8000/experimental/banterop`
- **API Documentation**: `http://localhost:8000/docs`
- **Agent Card**: `http://localhost:8000/.well-known/agent-card.json`

## 📋 Key Endpoints

### Core A2A Endpoints
- `POST /api/bridge/demo/a2a` - Primary A2A JSON-RPC endpoint
- `GET /.well-known/agent-card.json` - Agent discovery card

### Health & Status
- `GET /healthz` - Health check
- `GET /version` - Version info
- `GET /api/selftest` - Self-test suite

### Experimental Banterop UI
- `POST /api/experimental/banterop/scenario/load` - Load scenario from URL
- `POST /api/experimental/banterop/agentcard/load` - Load remote agent card
- `POST /api/experimental/banterop/run/start` - Start conversation run
- `POST /api/experimental/banterop/llm/narrative` - Generate AI summary
- `POST /api/experimental/banterop/test/smoke` - Run smoke test

## 🧪 Experimental Banterop UI

The Banterop-style console provides a comprehensive testing interface:

### Getting Started
1. Navigate to `/experimental/banterop`
2. **Load a Scenario**: Use sample BCS or provide JSON URL
3. **Configure Remote Agent**: Load from CareCommons or provide agent card URL
4. **Optional FHIR Setup**: Connect to FHIR server for patient data
5. **Start Run**: Begin conversation with remote agent
6. **Send Messages**: Use the composer to interact
7. **Analyze with Claude**: Generate summaries and rationales

### Features
- **Two-column Transcript**: Side-by-side conversation view
- **Real-time Streaming**: SSE support for live responses
- **FHIR Integration**: Fetch patient data with `$everything` operation
- **BCS Evaluation**: Built-in breast cancer screening rules engine
- **Claude Analysis**: AI-powered conversation insights
- **Smoke Testing**: Automated multi-turn test scripts

## 🏥 FHIR Integration

### Quick Setup
1. **Configure Connection**: Enter FHIR base URL and optional Bearer token
2. **Test Connection**: Verify server compatibility and authentication
3. **Search Patients**: Find relevant records by name or ID
4. **Fetch $everything**: Pull complete patient bundle
5. **Auto-mapping**: System converts FHIR to scenario payloads

### Example FHIR Servers
- **HAPI FHIR**: `https://hapi.fhir.org/baseR4` (public test server)
- **SMART Health IT**: `https://r4.smarthealthit.org` (test server)
- **Your Organization**: Configure with appropriate base URL and token

### Supported Operations
- `GET /metadata` - Server capabilities
- `GET /Patient?name=John` - Patient search
- `GET /Patient/123/$everything` - Complete patient data

## 🤖 Claude AI Integration

### Features
- **Conversation Summaries**: Patient and administrator perspectives
- **Guideline Rationale**: Detailed explanation of BCS evaluation decisions
- **Custom Analysis**: General-purpose LLM completion endpoint

### Setup
1. Get API key from [Anthropic](https://console.anthropic.com)
2. Set `ANTHROPIC_API_KEY` environment variable
3. Claude features auto-enable when key is detected

### API Usage
```bash
# Check Claude status
curl http://localhost:8000/api/experimental/banterop/llm/status

# Generate narrative summary
curl -X POST http://localhost:8000/api/experimental/banterop/llm/narrative \
  -H "Content-Type: application/json" \
  -d '{"role":"applicant","transcript":[...]}'

# Get guideline rationale
curl -X POST http://localhost:8000/api/experimental/banterop/llm/rationale \
  -H "Content-Type: application/json" \
  -d '{"patient_facts":{...},"evaluation":{...},"guidelines":{...}}'
```

## 🔧 Development

### Available Commands
```bash
# Install development dependencies
make dev

# Code formatting and linting
make format
make lint
make typecheck

# Run tests
make test

# Run smoke tests
make smoke
# or manually:
bash tools/smoke_a2a.sh http://localhost:8000

# Clean build artifacts
make clean
```

### Project Structure
```
app/
├── main.py                 # FastAPI application entry point
├── config.py              # Pydantic configuration models
├── agents/                 # Agent implementations (administrator, applicant)
├── protocols/             # Protocol implementations (A2A, MCP)
├── scenarios/             # Healthcare scenarios (BCSE, clinical trial, etc.)
├── eligibility/           # Eligibility checking engines
├── fhir/                  # FHIR server integration
├── llm/                   # Claude AI integration
├── banterop_ui/           # Experimental Banterop-style UI backend
├── experimental/          # Other experimental features
└── web/                   # Frontend templates and static assets
    └── experimental/
        └── banterop/      # Banterop UI frontend (HTML/JS)

main.py                    # Flask-compatible WSGI entry point (legacy)
api/index.py              # Vercel serverless entry point
tools/                    # Development scripts
scripts/                  # CI/build scripts
```

## 🚢 Deployment

### Vercel (Serverless)
The application is pre-configured for Vercel deployment:
- `vercel.json` routes all traffic to `api/index.py`
- `api/index.py` imports the FastAPI app
- Environment variables configured in Vercel dashboard

### Traditional Hosting
```bash
# Using gunicorn (recommended for production)
gunicorn --bind 0.0.0.0:8000 app.main:app

# Using uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker
```bash
# Build image
docker build -t agentinterop .

# Run container
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=your_key agentinterop
```

## 🧪 Testing & Integration

### Smoke Tests
```bash
# Test local instance
bash tools/smoke_a2a.sh

# Test remote instance
bash tools/smoke_a2a.sh https://your-domain.com

# Expected output:
# 1. Health check: OK
# 2. Agent Card: /api/bridge/demo/a2a
# 3. A2A message/send test: {"result":{"taskId":"..."}}
# 4. A2A tasks/get test: {"result":{"tasks":[...]}}
```

### Partner Integration Testing
1. **Agent Card Discovery**: Verify your card at `/.well-known/agent-card.json`
2. **A2A Compliance**: Test JSON-RPC 2.0 compatibility
3. **Streaming Support**: Test Server-Sent Events (SSE)
4. **BCSE Scenario**: Validate breast cancer screening workflow

### Using with External Partners
- **CareCommons**: `https://care-commons.meteorapp.com`
- **Banterop**: Compatible with Banterop's console interface
- **Your Partners**: Provide your agent card URL for integration

## 📚 API Reference

### A2A Protocol Methods
- `message/send` - Send message with optional task context
- `message/stream` - Send message with streaming response
- `tasks/get` - Retrieve active tasks
- `tasks/cancel` - Cancel specific task
- `tasks/resubscribe` - Resubscribe to task updates

### MCP Protocol Tools
- `begin_chat_thread` - Start new conversation
- `send_message_to_chat_thread` - Send message to thread
- `check_replies` - Check for new responses

### Response Formats
All endpoints return consistent JSON structure:
```json
{
  "success": true|false,
  "data": {...},
  "error": "Error message (if success=false)",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## ❓ Troubleshooting

### Common Issues

**404 on A2A endpoint**:
- Verify URL: `/api/bridge/demo/a2a` (not `/a2a`)
- Check server is running on correct port

**CORS errors**:
- Application allows all origins by default
- Check your request headers include `Content-Type: application/json`

**SSE timeout**:
- Streams auto-close after 30 seconds of inactivity
- Implement reconnection logic in client

**Agent Card not found**:
- Endpoint is `/.well-known/agent-card.json`
- Should return `url` field with A2A endpoint

**Claude features disabled**:
- Set `ANTHROPIC_API_KEY` environment variable
- Restart application after setting key
- Check `/api/experimental/banterop/llm/status`

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | No | None | Claude API key for AI features |
| `SESSION_SECRET` | No | Auto-generated | Flask session security key |
| `PUBLIC_BASE_URL` | No | Request URL | Base URL for agent card generation |
| `APP_ENV` | No | None | Set to `vercel` for serverless deployment |
| `UI_EXPERIMENTAL` | No | `false` | Enable experimental UI features |

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run quality checks: `make format lint typecheck test`
5. Commit changes: `git commit -am 'Add my feature'`
6. Push to branch: `git push origin feature/my-feature`
7. Create pull request

## 📞 Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: Additional docs available in `docs/` directory
- **API Docs**: Interactive documentation at `/docs` when server is running

---

*Built with ❤️ for healthcare interoperability*