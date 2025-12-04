# Clinical Informaticist Agent Demo Instructions

## Overview
This demo showcases an AI-powered Clinical Informaticist Agent that can:
1. Learn medical guidelines (USPSTF Breast Cancer Screening)
2. Build CQL (Clinical Quality Language) measures
3. Validate CQL syntax
4. Publish to Medplum FHIR server

## Prerequisites

### 1. Start the AgentInterOp Server
```bash
cd c:\Users\default.LAPTOP-BOBEDDVK\OneDrive\Documents\GitHub\AgentInterOp
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Verify Server is Running
Open browser: http://localhost:8000/health

## Demo Scenarios

---

## Scenario 1: Full Workflow Demo (Recommended)

### Using Claude Desktop with MCP

1. **Configure Claude Desktop** to use the CQL Builder MCP server

2. **Start conversation with Claude:**

```
I need to create a CQL quality measure for breast cancer screening based on USPSTF guidelines.

Please help me:
1. Learn the USPSTF breast cancer screening guidelines
2. Build a CQL measure (CMS125v11 - NQF 2372)
3. Validate the CQL syntax
4. Publish to Medplum FHIR server

Use the AgentInterOp Clinical Informaticist Agent at:
http://localhost:8000/api/bridge/cql-measure/a2a
```

### Expected Claude Response Flow:
- Claude will connect to the A2A endpoint
- Execute the workflow steps
- Return Library and Measure IDs from Medplum

---

## Scenario 2: Step-by-Step Demo

### Step 1: Learn Guidelines
Ask Claude:
```
Connect to the Clinical Informaticist Agent at http://localhost:8000/api/bridge/cql-measure/a2a
and ask it to learn the USPSTF breast cancer screening guidelines.
```

### Step 2: Build CQL
```
Now ask the agent to build a CQL measure for breast cancer screening
based on CMS125v11 (NQF 2372).
```

### Step 3: Validate
```
Ask the agent to validate the CQL measure syntax.
```

### Step 4: Publish
```
Finally, publish the validated measure to Medplum FHIR server.
```

---

## Scenario 3: Direct API Demo (curl)

### Test A2A Endpoint Directly

```bash
# Full workflow execution
curl -X POST http://localhost:8000/api/bridge/cql-measure/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "demo-1",
    "method": "message/send",
    "params": {
      "message": {
        "parts": [{
          "kind": "text",
          "text": "Execute full workflow for breast cancer screening and publish to Medplum"
        }]
      }
    }
  }'
```

### Expected Response:
```json
{
  "jsonrpc": "2.0",
  "id": "demo-1",
  "result": {
    "status": "completed",
    "artifacts": [...],
    "message": {
      "parts": [{
        "kind": "text",
        "text": "Successfully published to Medplum:\n- Library ID: xxx\n- Measure ID: xxx"
      }]
    }
  }
}
```

---

## Scenario 4: Web UI Demo

### Using the Inspector UI

1. Open http://localhost:8000/inspector

2. Enter Agent Card URL:
   ```
   http://localhost:8000/.well-known/agent-card.json
   ```

3. Click **Connect**

4. In the chat, type:
   ```
   Execute full workflow for breast cancer screening and publish to Medplum
   ```

5. Watch the agent process and return results

---

## Key Talking Points for Demo

### 1. Interoperability Standards
- **A2A Protocol**: Google's Agent-to-Agent JSON-RPC 2.0 standard
- **MCP Protocol**: Anthropic's Model Context Protocol
- **FHIR R4**: Healthcare data exchange standard
- **CQL**: Clinical Quality Language for quality measures

### 2. Healthcare Use Case
- **USPSTF Guidelines**: Evidence-based screening recommendations
- **CMS125v11**: Breast Cancer Screening quality measure
- **NQF 2372**: National Quality Forum measure ID

### 3. Technical Architecture
```
Claude Desktop
    ↓ (MCP or A2A)
AgentInterOp Platform
    ↓
Clinical Informaticist Agent
    ↓
CQL Builder MCP → Medplum FHIR Server
```

### 4. Medplum Integration
- OAuth2 client credentials authentication
- Creates FHIR Library resource (contains CQL)
- Creates FHIR Measure resource (references Library)
- Returns resource IDs for verification

---

## Verification Steps

### Check Published Resources in Medplum

1. Go to https://app.medplum.com
2. Login with your credentials
3. Navigate to **Library** resources
4. Find the newly created breast cancer screening library
5. Navigate to **Measure** resources
6. Find the linked measure

### Verify via API
```bash
# Get Library
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.medplum.com/fhir/R4/Library/LIBRARY_ID

# Get Measure
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.medplum.com/fhir/R4/Measure/MEASURE_ID
```

---

## Troubleshooting

### Server Not Starting
```bash
# Check if port is in use
netstat -ano | findstr :8000

# Kill existing process
taskkill /PID <PID> /F

# Try alternative port
python -m uvicorn app.main:app --port 8001
```

### Medplum Authentication Fails
- Verify client credentials in `app/agents/clinical_informaticist.py`
- Check Medplum project access permissions

### CQL Validation Errors
- The agent will report syntax issues
- Review CQL against CMS specifications

---

## Demo Script (5 minutes)

1. **Introduction** (30 sec)
   - "Today I'll demonstrate an AI Clinical Informaticist that builds quality measures"

2. **Show Architecture** (30 sec)
   - Display the A2A/MCP dual protocol support
   - Explain FHIR integration

3. **Execute Workflow** (2 min)
   - Run the full workflow command
   - Show real-time processing

4. **Verify in Medplum** (1 min)
   - Open Medplum dashboard
   - Show created Library and Measure

5. **Q&A** (1 min)
   - Discuss extensibility to other guidelines
   - Talk about production readiness

---

## Additional Resources

- [A2A Protocol Spec](https://github.com/google/A2A)
- [MCP Protocol](https://modelcontextprotocol.io)
- [FHIR R4](https://hl7.org/fhir/R4)
- [CQL Specification](https://cql.hl7.org)
- [USPSTF Guidelines](https://www.uspreventiveservicestaskforce.org)
- [Medplum](https://www.medplum.com)
