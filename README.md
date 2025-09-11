# Multi-Agent Interoperability Demo

A comprehensive test bench for multi-agent and FHIR interoperability, featuring dual protocol support (A2A and MCP), real-time FHIR integration, AI-powered narrative processing, and complete decision transparency.

## Features

### Core Capabilities
- **Dual Protocol Support**: A2A (Agent-to-Agent) JSON-RPC and MCP (Model Context Protocol)
- **Real-time FHIR Integration**: Connect to any FHIR server with full API support
- **AI-Powered Narrative Processing**: Convert natural language to structured JSON using Claude
- **Decision Transparency**: Complete trace and telemetry system ("Prove It" panel)
- **Room Export/Import**: Share conversation contexts across systems for external partner interoperability

### Supported Scenarios
- **BCSE**: Benefits Coverage Support Eligibility checking
- **Clinical Trial**: Patient enrollment and eligibility assessment
- **Referral Specialist**: Provider referral workflows
- **Prior Auth**: Prior authorization request processing
- **Custom**: Configurable scenarios for specific use cases

### Scheduling Links (Experimental)
- **SMART Scheduling Links**: Specialist slot discovery via bulk publishers
- **Deep-link Hand-off**: Provider booking portal integration
- **A2A/MCP Compatible**: Works with both protocol flows
- **Trace Integration**: Complete scheduling audit trail

## Quick Start

### Environment Setup

1. Create a `.env` file in the project root:
```bash
# Required for AI narrative processing
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Session security (auto-generated if not set)
SESSION_SECRET=your_secret_key_here
```

2. Start the application:
```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

3. Open your browser to `http://localhost:5000`

## FHIR Connector

### Setup and Configuration

The FHIR connector enables real-time integration with any FHIR R4-compatible server:

1. **Configure Connection**: In the left panel, enter:
   - **Base URL**: Your FHIR server endpoint (e.g., `https://hapi.fhir.org/baseR4`)
   - **Token**: Optional Bearer token for authentication

2. **Test Connection**: Click "Test Connection" to verify:
   - Server capabilities discovery
   - Authentication validation
   - API compatibility check

### Quick Tests

#### Server Capabilities
```bash
curl -X GET "https://hapi.fhir.org/baseR4/metadata" \
  -H "Accept: application/fhir+json"
```

#### Patient Search
```bash
curl -X GET "https://hapi.fhir.org/baseR4/Patient?name=John&_count=5" \
  -H "Accept: application/fhir+json" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Patient $everything Operation
```bash
curl -X GET "https://hapi.fhir.org/baseR4/Patient/123456/$everything" \
  -H "Accept: application/fhir+json" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### FHIR Data Ingestion

1. Use the patient search to find relevant records
2. Click "Ingest" to pull complete patient data via `$everything`
3. The system automatically maps FHIR bundles to scenario-specific payloads
4. Toggle "Use Ingested FHIR" in the applicant payload editor

## Narrative → JSON with Claude

Transform natural language descriptions into structured JSON schemas using AI:

### Setup
Ensure `ANTHROPIC_API_KEY` is set in your `.env` file.

### Sample Prior-Auth Narrative
```
Patient John Smith, age 45, requires MRI scan of lumbar spine due to chronic lower back pain persisting for 6 months. Conservative treatments including physical therapy and medication have failed. Patient has BlueCross BlueShield insurance, member ID 12345678. Requesting provider is Dr. Sarah Johnson, NPI 1234567890, at Metro Orthopedic Clinic. Procedure code 72148, estimated cost $2,800. Patient has met deductible, requires prior authorization for coverage.
```

### Usage
1. Enter your narrative in the text area
2. Click "Generate JSON Schema"
3. Review and apply the generated structured data
4. The system converts natural language into properly formatted eligibility payloads

## Agent Discovery & A2A Agent Card

The platform exposes an A2A-compliant Agent Card for agent discovery and interoperability:

### Fetch Agent Card
```bash
# Get the A2A-compliant agent card
curl -s https://agent-inter-op.vercel.app/.well-known/agent-card.json | jq .

# Example response structure:
{
  "name": "AgentInterOp Healthcare Platform",
  "description": "A healthcare interoperability platform supporting dual protocols...",
  "url": "https://agent-inter-op.vercel.app",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": true
  },
  "skills": [
    {
      "id": "bcse",
      "name": "Breast Cancer Screening Evaluator",
      "description": "Evaluates BCS eligibility using FHIR data...",
      "a2a.config64": "eyJzY2VuYXJpbyI6ImJjc2UifQ=="
    }
  ]
}
```

### Inspect Base64 Configuration
```bash
# Decode the binding configuration
curl -s https://agent-inter-op.vercel.app/.well-known/agent-card.json | \
  jq -r '.skills[0]["a2a.config64"]' | \
  base64 -d | jq .
```

## A2A Protocol API

### Message Streaming
```bash
curl -X POST "http://localhost:5000/api/bridge/demo/a2a" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/stream",
    "params": {
      "contextId": "ctx_123",
      "parts": [{"kind": "text", "text": "Begin eligibility check"}]
    },
    "id": 1
  }'
```

### Task Resubscription
Reconnect to an existing task and receive all subsequent frames:

```bash
curl -X POST "http://localhost:5000/api/bridge/demo/a2a" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/resubscribe",
    "params": {
      "id": "task_abc123"
    },
    "id": 2
  }'
```

### Task Cancellation
```bash
curl -X POST "http://localhost:5000/api/bridge/demo/a2a" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/cancel",
    "params": {
      "taskId": "task_abc123"
    },
    "id": 3
  }'
```

## Decision Trace & Telemetry

### "Prove It" Panel

Complete transparency into agent decision-making:

- **Wire Protocol Traces**: See all A2A and MCP message exchanges
- **Decision Points**: Track eligibility determinations and reasoning
- **Performance Metrics**: Monitor response times and processing steps
- **Error Tracking**: Detailed error logs with context

### Usage
1. Start any demo scenario
2. Open the "Prove It" panel in the main interface
3. View real-time trace events as they occur
4. Download complete traces for analysis or audit

### Trace Export
```bash
curl -X GET "http://localhost:5000/api/trace/ctx_123" \
  -H "Accept: application/json"
```

## Room Export/Import

Enable interoperability with external partner systems:

### Export a Room
1. Complete a conversation or scenario
2. Click "Export Room" in the left panel
3. Download the JSON file containing:
   - Context ID and scenario configuration
   - Last applicant payload
   - Conversation state and artifacts metadata
   - Configuration snapshot

### Import a Room
1. Click "Import Room" and select a JSON export file
2. The system creates a new context with imported configuration
3. UI automatically switches to the new imported context
4. Continue the conversation from the imported state

### API Endpoints

#### Export
```bash
curl -X GET "http://localhost:5000/api/room/export/ctx_123" \
  -H "Accept: application/json"
```

#### Import
```bash
curl -X POST "http://localhost:5000/api/room/import" \
  -H "Content-Type: application/json" \
  -d @exported_room.json
```

## Agent Discovery

The system provides an agent card for external discovery at:
```
GET /.well-known/agent-card.json
```

Example response:
```json
{
  "protocolVersion": "0.2.9",
  "preferredTransport": "JSONRPC",
  "capabilities": {"streaming": true},
  "skills": [{
    "id": "scenario",
    "a2a": {
      "config64": "eyJzY2VuYXJpbyI6ImJjc2UiLCJ0YWdzIjpbXX0="
    }
  }],
  "endpoints": {
    "jsonrpc": "https://your-domain.com/api/bridge/demo/a2a"
  }
}
```

## Development

### Project Structure
```
app/
├── config.py              # Configuration management
├── engine.py              # Conversation engine
├── fhir/                  # FHIR integration
│   ├── connector.py       # FHIR client
│   └── service.py         # FHIR operations
├── ingest/                # Data ingestion
│   └── mapper.py          # FHIR to payload mapping
├── llm/                   # AI integration
│   └── anthropic.py       # Claude API client
├── protocols/             # Protocol implementations
│   ├── a2a.py            # A2A JSON-RPC
│   └── mcp.py            # MCP protocol
├── scenarios/             # Scenario definitions
├── store/                 # Data storage
│   └── memory.py         # In-memory storage
└── web/                   # Web interface
    ├── static/
    └── templates/
```

### Configuration
- Runtime configuration stored in `app/config.runtime.json`
- Environment variables loaded from `.env`
- Scenarios and rules defined in `app/scenarios/`

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit `.env` files or tokens to version control**
2. **API keys are read from environment variables only**
3. **The agent card is hidden when no public base URL is configured**
4. **Use proper authentication tokens for production FHIR servers**
5. **Room exports may contain sensitive patient data - handle appropriately**

### Example .gitignore entries:
```
.env
*.token
config.runtime.json
*.key
```

## Scheduling Links (Experimental)

### Overview

The Scheduling Links feature implements SMART Scheduling Links specification for specialist slot discovery and booking. When a patient is eligible for screening (e.g., BCS-E), the system automatically discovers available appointment slots from configured publishers and provides deep-link hand-off to provider booking portals.

### Features

- **Bulk Publisher Integration**: Connects to SMART Scheduling Links publishers via `/$bulk-publish` endpoints
- **Real-time Slot Discovery**: Searches available slots with filtering by specialty, time window, location, and organization
- **Deep-link Hand-off**: Opens provider booking portals or provides simulated booking for demo purposes
- **A2A/MCP Integration**: Works seamlessly with both protocol flows
- **Caching & Performance**: Intelligent caching with configurable TTL for optimal performance
- **Trace & Audit**: Complete scheduling events logged in the Trace/Prove-It panel

### Configuration

#### UI Configuration (Experimental Mode)

1. Set `UI_EXPERIMENTAL=true` environment variable
2. In the Settings panel, configure "Scheduling Links":
   - **Publishers**: One URL per line (e.g., `https://zocdoc-smartscheduling.netlify.app`)
   - **Cache TTL**: Time-to-live for cached publisher data (300 seconds default)
   - **Default Specialty**: Default specialty for searches (e.g., "mammography")
   - **Default Radius**: Search radius in kilometers (50 km default)
   - **Default Timezone**: Timezone for slot display (America/New_York default)

#### API Configuration

```bash
# Get current configuration
curl -X GET "http://localhost:5000/api/scheduling/config"

# Update configuration
curl -X POST "http://localhost:5000/api/scheduling/config" \
  -H "Content-Type: application/json" \
  -d '{
    "publishers": ["https://zocdoc-smartscheduling.netlify.app"],
    "cache_ttl_seconds": 300,
    "default_specialty": "mammography",
    "default_radius_km": 50,
    "default_timezone": "America/New_York"
  }'

# Test publishers
curl -X POST "http://localhost:5000/api/scheduling/publishers/test"
```

### Usage Workflow

#### 1. BCS Eligibility → Automatic Scheduling

When a patient is determined eligible through BCS-E evaluation:
1. The system automatically triggers slot discovery using configured defaults
2. A "Schedule Screening" panel appears in the UI
3. Available slots are displayed with booking options

#### 2. Manual Scheduling Search

Use the "Schedule Screening" panel to manually search for slots:
- **Specialty**: Filter by service type (e.g., "mammography", "cardiology")
- **Date Range**: Start and end dates for appointment availability
- **Location**: Geographic filters (city/state text or lat/lng with radius)
- **Organization**: Filter by provider name (contains match)

#### 3. Slot Booking

Click "Book" on any slot to:
- Record the selection in the audit trace
- Open the provider's booking portal (if available)
- Show simulated booking page for demo publishers

### API Endpoints

#### Slot Discovery

```bash
curl -X POST "http://localhost:5000/api/scheduling/search" \
  -H "Content-Type: application/json" \
  -d '{
    "specialty": "mammography",
    "start": "2024-12-15T00:00:00Z",
    "end": "2024-12-29T23:59:59Z",
    "radius_km": 50,
    "lat": 40.7128,
    "lng": -74.0060,
    "limit": 25
  }'
```

#### Slot Selection

```bash
curl -X POST "http://localhost:5000/api/scheduling/choose" \
  -H "Content-Type: application/json" \
  -d '{
    "slot_id": "slot_12345",
    "publisher_url": "https://publisher.example.com",
    "note": "Booked from API"
  }'
```

### A2A Protocol Integration

When BCS eligibility is determined as "eligible", A2A responses automatically include:

- **ProposedAppointments Artifact**: JSON containing discovered slots
- **Guidance Messages**: Text guidance about available appointments
- **Trace Events**: Complete audit trail in the task history

Example A2A response with scheduling:
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "id": "task_123",
    "status": {"state": "completed"},
    "history": [
      {"role": "user", "parts": [{"kind": "text", "text": "{...eligibility_data...}"}]},
      {"role": "agent", "parts": [{"kind": "text", "text": "{\"eligible\": true, \"reason\": \"...\""}]},
      {"role": "agent", "parts": [{"kind": "text", "text": "Eligible for screening. Found 5 available appointment slots."}]}
    ],
    "artifacts": [
      {
        "name": "ProposedAppointments.json",
        "content": "{\"kind\": \"ProposedAppointments\", \"slots\": [...], \"searched_at\": \"2024-12-15T10:00:00Z\"}",
        "mimeType": "application/json"
      }
    ]
  }
}
```

### MCP Protocol Integration

Two new MCP tools are available:

#### find_specialist_slots

```bash
curl -X POST "http://localhost:5000/api/mcp/bcse/find_specialist_slots" \
  -H "Content-Type: application/json" \
  -d '{
    "specialty": "mammography",
    "start_date": "2024-12-15T00:00:00Z",
    "end_date": "2024-12-29T23:59:59Z",
    "radius_km": 50,
    "limit": 10
  }'
```

#### choose_slot

```bash
curl -X POST "http://localhost:5000/api/mcp/bcse/choose_slot" \
  -H "Content-Type: application/json" \
  -d '{
    "slot_id": "slot_12345",
    "publisher_url": "https://publisher.example.com",
    "note": "MCP booking"
  }'
```

### Demo Instructions

#### Setup for Connectathon Demo

1. **Enable Experimental UI**:
   ```bash
   export UI_EXPERIMENTAL=true
   ```

2. **Configure Test Publisher**:
   - In Settings → Scheduling Links
   - Add publisher: `https://zocdoc-smartscheduling.netlify.app`
   - Set specialty: `mammography`
   - Set radius: `50` km
   - Click "Save Scheduling Config"

3. **Test Publishers**:
   - Click "Test Publishers" 
   - Verify success and slot counts in results

#### Demo Flow

1. **Run BCS Eligibility Check**:
   - Use demo patient data (female, age 56, recent mammogram)
   - Submit eligibility check
   - Observe "eligible" result

2. **Automatic Scheduling Trigger**:
   - Notice "Schedule Screening" panel appears
   - See message: "Patient is eligible! Schedule screening now."

3. **Search and Book Slots**:
   - Verify search fields are pre-populated
   - Click "Search Slots"
   - Browse available appointments
   - Click "Book" on preferred slot

4. **Trace Verification**:
   - Open Trace/Prove-It panel
   - Verify scheduling events are logged:
     - `discovery_query` with search parameters
     - `discovery_results_count` with slot counts
     - `chosen_slot` with booking details
     - `handoff_url` with booking link

5. **Booking Hand-off**:
   - Observe new tab opens with booking portal
   - For demo publisher: simulated booking page
   - For real publishers: actual provider portal

### Data Safety & Compliance

- **No PHI in URLs**: Patient data never included in query parameters to publishers
- **Timeout Protection**: All publisher requests have 8-10s timeouts
- **Graceful Degradation**: System continues to work if publishers are unavailable
- **Cache Management**: Automatic cache expiration and cleanup
- **Audit Trail**: Complete scheduling activity logged for compliance

### Testing

Run the comprehensive test suite:

```bash
pytest tests/test_scheduling.py -v
```

Test coverage includes:
- Configuration management
- Bulk publisher fetch (JSON/NDJSON)
- Index building and reference resolution
- Slot discovery and filtering
- Geographic distance calculations
- Specialty matching
- Time window filtering
- Slot selection and booking
- Integration scenarios

## Experimental Agent UX

### Overview

The Experimental Agent UX feature provides Claude-powered AI assistance for agent interactions, including intelligent response generation, automated testing, and enhanced conversation analytics. This feature is designed to showcase advanced agent capabilities and provide a testing framework for AI-driven healthcare interoperability scenarios.

### Features

- **Claude-Powered Response Generation**: AI-generated responses for both applicant and administrator roles
- **BCS Test Harness**: Automated testing of breast cancer screening eligibility scenarios
- **Two-Lane Transcript**: Visual separation of applicant and administrator conversations
- **State Management**: Visual indicators for working, input-required, and completed states
- **Response Cards**: Contextual action cards for information requests, decisions, documentation, and scheduling
- **Trace & Artifacts Tabs**: Complete conversation analysis with raw JSON inspection
- **Claude API Status**: Real-time monitoring of Claude API availability and latency

### Enabling Experimental Agent UX

#### Method 1: URL Parameter
Add `?experimental=1` to any page URL:
```
http://localhost:5000/?experimental=1
```

#### Method 2: Settings Panel
1. Navigate to the Settings panel
2. Check "Enable Experimental Agent UX"
3. The feature will be enabled for your session

#### Method 3: Environment Variable
Set the environment variable to enable by default:
```bash
UI_EXPERIMENTAL=true
```

### Prerequisites

To use Claude-powered features, you must configure your Anthropic API key:

```bash
# Add to your .env file
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### UI Components

#### Claude Status Indicator
- **Green "Ready"**: Claude API key configured and accessible
- **Yellow "Not Ready"**: ANTHROPIC_API_KEY not configured
- **Red "Error"**: API connection failed
- Displays response latency when available

#### Two-Lane Transcript
- **Left Lane**: Applicant messages and actions
- **Right Lane**: Administrator messages and actions
- Real-time state indicators for each role
- Timestamp and status badges for each message

#### Response Generation Panel
1. **Role Selection**: Choose "Applicant" or "Administrator"
2. **Hint Selection**: Guide Claude's response type:
   - **Requirements**: Request additional information
   - **Documentation**: Ask for supporting documents
   - **Decision**: Make eligibility determination
   - **Scheduling**: Propose appointment slots
   - **Free Response**: Open-ended response
3. **Generate Response**: Creates AI-powered response
4. **Use This Response**: Applies the generated response to the conversation

#### Response Cards
Claude generates contextual action cards based on the scenario:

- **Information Request Cards**: Interactive forms for gathering patient data
- **Decision Cards**: Color-coded eligibility determinations with rationale
- **Documentation Cards**: Checklists for required supporting documents
- **Scheduling Cards**: Available appointment slots with booking buttons

#### Right Rail Tabs
- **Trace**: Complete conversation flow with timestamps and actions
- **Artifacts**: Generated documents and decision bundles
- **Raw JSON**: Full conversation data in JSON format for debugging

### BCS Test Harness

The automated test harness validates breast cancer screening eligibility logic using Claude AI:

#### Test Cases
1. **Eligible-RecentMammo**: Female, age 55, recent mammogram (should be eligible)
2. **Needs-Info-NoMammo**: Female, age 46, no mammogram history (needs more info)
3. **Ineligible-Age**: Female, age 25, recent mammogram (too young, ineligible)

#### Running Tests
1. Enable Experimental Agent UX
2. Click "Run BCS Tests" in the Agent UX panel
3. View real-time test execution with PASS/FAIL indicators
4. Review detailed results including expected vs. actual decisions

#### API Access
```bash
# Get test cases
curl -X GET "http://localhost:5000/api/experimental/tests/bcse"

# Run a specific test case
curl -X POST "http://localhost:5000/api/experimental/tests/bcse/run" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Eligible-RecentMammo",
    "payload": {"sex": "female", "birthDate": "1969-08-10", "last_mammogram": "2024-05-01"},
    "expect": "eligible"
  }'
```

### Claude Agent Response API

#### Generate Role-Specific Response
```bash
curl -X POST "http://localhost:5000/api/experimental/agent/respond" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "administrator",
    "context": [
      {"role": "user", "content": "Patient data for BCS evaluation"},
      {"role": "assistant", "content": "Reviewing eligibility criteria"}
    ],
    "facts": {
      "scenario": "bcse",
      "applicant_payload": {"sex": "female", "birthDate": "1969-08-10", "last_mammogram": "2024-05-01"}
    },
    "hint": "decision"
  }'
```

#### Response Format
```json
{
  "ok": true,
  "result": {
    "role": "administrator",
    "state": "completed",
    "message": "Based on the provided information, the patient is **eligible** for breast cancer screening.",
    "actions": [
      {
        "kind": "propose_decision",
        "decision": "eligible",
        "rationale": "Female patient, age 55, with recent mammogram within 27-month window."
      }
    ],
    "artifacts": []
  }
}
```

#### Claude API Status
```bash
curl -X GET "http://localhost:5000/api/experimental/agent/status"
```

### Narrative Processing

Transform clinical narratives into structured JSON using Claude AI:

```bash
curl -X POST "http://localhost:5000/api/experimental/narrative/parse" \
  -H "Content-Type: application/json" \
  -d '{
    "narrative": "55-year-old female with recent mammogram in May 2024, requesting BCS eligibility evaluation",
    "target_schema": "bcse"
  }'
```

### Security & Safety

#### API Key Protection
- API keys are never exposed in client-side code
- All Claude API calls are server-side only
- Graceful degradation when API key is not configured

#### Content Safety
- Healthcare-focused system prompts ensure appropriate responses
- Structured JSON output prevents prompt injection
- Rate limiting and timeout protection on all AI requests

#### Data Privacy
- Patient data is only used for eligibility evaluation context
- No persistent storage of patient information in Claude calls
- All trace data can be cleared or exported for compliance

### Development & Debugging

#### Enabling Debug Mode
```javascript
// In browser console
window.claudeUX.debug = true;
```

#### Trace Analysis
All experimental features generate detailed trace events:
- Claude API request/response timing
- User interactions and state changes
- Test execution results
- Response generation context

#### Error Handling
- Network failures gracefully degrade to manual operation
- Invalid JSON responses are caught and logged
- UI components remain functional even when AI features are unavailable

### Integration with Main Protocols

#### A2A Protocol
Experimental responses can be directly submitted to A2A conversations using the "Use This Response" button, which automatically formats the response for the appropriate protocol.

#### MCP Protocol
Generated responses integrate seamlessly with MCP tool calls, providing intelligent suggestions for agent interactions.

### Future Enhancements

The experimental Agent UX framework is designed to support:
- Multi-scenario AI training and testing
- Custom prompt engineering for specialized healthcare use cases
- Integration with additional AI providers beyond Claude
- Advanced conversation analytics and quality metrics
- Real-time collaboration between human operators and AI agents

## Legacy Demo (Original BCS-E)

### BCS-E Eligibility Logic

#### Criteria
- **Age**: Patient must be 50-74 years old
- **Gender**: Must be female
- **Recent Mammogram**: Must have mammogram within 27 months of evaluation date

#### 27-Month Window Calculation
The system uses precise date arithmetic with `dateutil.relativedelta` to subtract exactly 27 months from the measurement date (default: today). For example:
- Measurement Date: 2024-01-15
- Cutoff Date: 2021-10-15 (27 months prior)
- Mammogram on 2021-11-01: ✅ Valid (within window)
- Mammogram on 2021-09-15: ❌ Invalid (outside window)

## Smoke Test

Complete end-to-end validation of all system features:

### 1) Configure FHIR
- Enter Base URL (e.g., `https://hapi.fhir.org/baseR4`) and leave token blank
- Test Capabilities → success
- Search Patient name="Petersen" → pick an id → Ingest $everything

### 2) Scenario = BCS-E
- Toggle "Use Ingested FHIR" → see Applicant Payload auto-filled
- Start Demo (A2A) → Admin posts requirements
- Send Applicant Info → decision + artifacts; see Trace populate

### 3) Switch to MCP
- Begin chat thread; send message; poll replies → same decision flow

### 4) Narrative → JSON
- Paste narrative of "Prior-Auth for 97110…"
- Convert with Claude → Apply → rerun flow

### 5) Export/Import room
- Export context; Import to new context; confirm continuity

## Share with Partners (BCS only)
Base URL: `<YOUR_BASE_URL>`

Discovery:
- Health: `GET /healthz`
- Version: `GET /version`
- Agent Card: `GET /.well-known/agent-card.json`
- Self-Test: `GET /api/selftest`
- OpenAPI: `/docs`

### A2A (BCS) — JSON-RPC over HTTP
**message/send (text prompt):**
```bash
curl -s <BASE>/api/bridge/bcse/a2a -H 'Content-Type: application/json' -d '{
  "jsonrpc":"2.0","id":"1","method":"message/send",
  "params":{"message":{"parts":[{"kind":"text","text":"Hello, begin."}]}}
}'
```

**message/send (JSON payload for evaluation):**
```bash
curl -s <BASE>/api/bridge/bcse/a2a -H 'Content-Type: application/json' -d '{
  "jsonrpc":"2.0","id":"1","method":"message/send",
  "params":{"message":{"parts":[{"kind":"text","text":"{\"sex\":\"female\",\"birthDate\":\"1968-05-10\",\"last_mammogram\":\"2024-12-01\"}"}]}}
}'
```

**message/stream (SSE):**
```bash
curl -s <BASE>/api/bridge/bcse/a2a -H 'Content-Type: application/json' -d '{
  "jsonrpc":"2.0","id":"1","method":"message/stream","params":{}
}' -H 'Accept: text/event-stream'
```

**tasks/get:**
```bash
curl -s <BASE>/api/bridge/bcse/a2a -H 'Content-Type: application/json' -d '{
  "jsonrpc":"2.0","id":"1","method":"tasks/get","params":{"id":"TASK_ID"}
}'
```

### MCP (BCS)
**begin_chat_thread:**
```bash
curl -s -X POST <BASE>/api/mcp/bcse/begin_chat_thread
```

**send_message_to_chat_thread:**
```bash
curl -s -X POST <BASE>/api/mcp/bcse/send_message_to_chat_thread \
  -H 'Content-Type: application/json' \
  -d '{"conversationId":"CONV_ID","message":"Hello from partner"}'
```

**check_replies:**
```bash
curl -s -X POST <BASE>/api/mcp/bcse/check_replies \
  -H 'Content-Type: application/json' \
  -d '{"conversationId":"CONV_ID","waitMs":500}'
```

### Direct BCS Evaluation
**Ingest demo FHIR bundle:**
```bash
curl -s -X POST <BASE>/api/bcse/ingest/demo
```

**Evaluate eligibility:**
```bash
curl -s -X POST <BASE>/api/bcse/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"sex":"female","birthDate":"1968-05-10","last_mammogram":"2024-12-01"}'
```

## License

This project is designed for healthcare interoperability testing and demonstration purposes.