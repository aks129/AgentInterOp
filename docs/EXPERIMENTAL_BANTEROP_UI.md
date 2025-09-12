# Experimental Banterop UI

The Experimental Banterop UI provides a comprehensive scenario-driven interface for testing Agent-to-Agent (A2A) interoperability. This feature implements a Banterop-style workflow for loading scenarios, connecting to remote agents, and executing end-to-end healthcare interoperability tests.

## Access

Navigate to `/experimental/banterop` on your AgentInterOp instance:

- **Local Development**: http://localhost:8000/experimental/banterop
- **Vercel Deployment**: https://agent-inter-op.vercel.app/experimental/banterop

## Features

### 1. Scenario Management
- **Load Scenarios**: Import scenario JSON from URLs or local files
- **Sample BCS Scenario**: Pre-built breast cancer screening scenario
- **Role Selection**: Choose your agent role (Applicant, Administrator, or custom scenario roles)
- **Validation**: Automatic scenario validation and agent enumeration

### 2. Remote Agent Discovery
- **Agent Card Loading**: Fetch and parse `.well-known/agent-card.json` from remote agents
- **Preset Connections**: Quick connect to CareCommons and other known agents
- **A2A Endpoint Resolution**: Automatic discovery of JSON-RPC endpoints from agent cards
- **Protocol Detection**: Support for various agent card formats and A2A endpoint specifications

### 3. FHIR Integration
- **Patient Data Retrieval**: Fetch patient data using `$everything` operation
- **Minimal Facts Extraction**: Parse FHIR bundles into structured patient facts
- **Bearer Token Support**: Secure FHIR server authentication
- **Configurable Codes**: Customizable CPT and LOINC code mappings

### 4. BCS (Breast Cancer Screening) Evaluation
- **Clinical Guidelines**: Configurable AMA-based screening guidelines
- **Eligibility Assessment**: Automated screening eligibility evaluation
- **Rules Editor**: JSON-based rules configuration interface
- **Decision Rationale**: Detailed explanations for screening recommendations

### 5. Conversation Management
- **Dual-Mode Operation**:
  - **Remote Mode**: Live A2A communication with external agents
  - **Local Mode**: Simulated responses for testing without external dependencies
- **Message Composer**: Rich text input with streaming response support
- **Transcript View**: Two-column conversation display (Mine vs Remote)
- **State Tracking**: Maintains conversation context and task IDs

### 6. Debugging & Monitoring
- **Trace Viewer**: Full JSON trace of all A2A exchanges
- **Artifacts**: Collection of generated documents and responses
- **Facts Display**: FHIR patient data visualization
- **Export Capabilities**: JSON export of complete interaction traces

### 7. Smoke Testing
- **Automated Test Scripts**: Pre-configured 2-3 turn conversation tests
- **Remote Endpoint Testing**: Validate A2A connectivity and basic functionality
- **Pass/Fail Results**: Clear test outcome reporting with detailed logs

## Getting Started

### Basic BCS Workflow

1. **Load Sample Scenario**
   - Click "Sample BCS" to load the built-in breast cancer screening scenario
   - Select your role (typically "Applicant" or "Administrator")

2. **Connect to Remote Agent**
   - Enter agent card URL (e.g., `https://care-commons.meteorapp.com`)
   - Click "Load Agent Card" to discover A2A endpoints
   - Or click "CareCommons" preset for quick connection

3. **Configure FHIR (Optional)**
   - Expand "FHIR Configuration" section
   - Enter FHIR server base URL and patient ID
   - Add Bearer token if required
   - Click "Fetch $everything" to retrieve patient data

4. **Evaluate BCS Eligibility**
   - After FHIR data is loaded, click "Evaluate BCS"
   - Review eligibility decision and rationale
   - Modify BCS rules if needed using the Rules Editor

5. **Start Conversation**
   - Choose conversation mode (Remote for live A2A, Local for simulation)
   - Click "Start Run"
   - Use the message composer to interact with the remote agent

6. **Monitor & Export**
   - Switch between tabs to view transcript, trace, artifacts, and facts
   - Export full trace as JSON for analysis or reporting

### Advanced Usage

#### Custom Scenarios
Create custom scenario JSON files following this structure:
```json
{
  "metadata": {
    "id": "my_scenario",
    "name": "My Healthcare Scenario",
    "description": "Custom interoperability test scenario"
  },
  "agents": [
    {
      "agentId": "my_agent",
      "name": "My Agent",
      "role": "custom_role",
      "systemPrompt": "You are a healthcare agent...",
      "messageToUseWhenInitiatingConversation": "Hello, I need assistance with..."
    }
  ],
  "settings": {
    "enableFhir": true,
    "enableBcsEvaluation": false
  }
}
```

#### Custom BCS Rules
Modify screening guidelines by editing the BCS Rules JSON:
```json
{
  "ageRangeYears": [40, 80],
  "screeningIntervalMonths": 12,
  "sexRequired": "female",
  "rationales": {
    "eligible": "Custom eligibility message...",
    "ineligible": "Custom ineligibility message..."
  }
}
```

## Sample Scenarios

### BCS Interoperability Test
**URL**: `file://bcs_scenario.json` (built-in)
- **Agents**: Healthcare Consumer (Applicant) + Healthcare Administrator
- **Features**: FHIR integration, BCS evaluation, appointment scheduling
- **Use Case**: End-to-end breast cancer screening eligibility and scheduling

## Agent Card URLs

### CareCommons
**URL**: `https://care-commons.meteorapp.com`
- **Agent**: Honeycomb Administrator Agent
- **Transport**: JSON-RPC over HTTP
- **Streaming**: Supported
- **Use Case**: Healthcare eligibility processing

### Local Testing
**URL**: `http://localhost:8000` or your deployment URL
- **Agent**: AgentInterOp Healthcare Platform
- **Transport**: JSON-RPC over HTTP
- **Use Case**: Local testing and development

## Technical Architecture

### Backend Components
- **Scenario Loader**: Fetch and validate scenario JSON from URLs or files
- **Agent Card Resolver**: Parse agent cards and extract A2A endpoints
- **FHIR Bridge**: Connect to FHIR servers and extract patient facts
- **BCS Evaluator**: Apply clinical guidelines to patient data
- **A2A Proxy**: Handle remote agent communication with streaming support
- **Run Manager**: Maintain conversation state and transcript history

### Frontend Interface
- **React-like Architecture**: Modular JavaScript with class-based components
- **Responsive Design**: Mobile-friendly layout with collapsible sections
- **Real-time Updates**: Automatic transcript refresh and status monitoring
- **Error Handling**: Comprehensive error reporting and user guidance

## Limitations

### Security
- **No PHI Logging**: Patient data is processed in memory only, not persisted
- **API Keys Server-Side**: Sensitive credentials never exposed to browser
- **CORS Proxy**: Server-side proxy handles cross-origin A2A requests

### Technical
- **SSE Fallback**: Streaming uses Server-Sent Events with polling fallback
- **Memory Storage**: Run state maintained in server memory (not persistent)
- **Development Mode**: Experimental feature, not production-ready

### Protocol Support
- **A2A Focus**: Primarily designed for Agent-to-Agent JSON-RPC protocol
- **FHIR R4**: Tested with FHIR R4 servers, may work with other versions
- **Agent Card Variants**: Supports multiple agent card formats but may not cover all edge cases

## Troubleshooting

### Common Issues

#### "Failed to fetch agent card"
- Verify the URL is accessible and returns valid JSON
- Check for CORS restrictions (the system uses a proxy to bypass these)
- Ensure the agent card follows the `.well-known/agent-card.json` convention

#### "No A2A endpoint found"
- Agent card may use non-standard endpoint specification
- Check the raw agent card data in the browser console
- Try alternative agent card URLs or formats

#### "FHIR data fetch failed"
- Verify FHIR server URL and patient ID
- Check Bearer token if authentication is required
- Ensure FHIR server supports `$everything` operation

#### "Message send failed"
- Verify remote agent A2A endpoint is operational
- Check network connectivity and firewall restrictions
- Review detailed error messages in the trace viewer

### Debug Mode
Enable detailed logging by opening browser developer console:
- All A2A requests/responses are logged
- Agent card parsing details are shown
- Run state changes are tracked

## Support

For issues, feature requests, or contributions:
- **GitHub Issues**: https://github.com/anthropics/claude-code/issues
- **Documentation**: Check the main AgentInterOp README
- **Examples**: Sample scenarios and agent cards in the `/scenarios` directory