# Demo Day Playbook
## Healthcare Interoperability Platform - Connectathon Demo

**Duration: 5 minutes**  
**Audience: Healthcare interoperability partners and stakeholders**  
**Goal: Demonstrate Language-First Interoperability with BCS end-to-end workflow**

---

## Pre-Demo Checklist (30 minutes before)

### Technical Setup
- [ ] **Verify deployment**: https://agent-inter-op.vercel.app/health
- [ ] **Agent card accessible**: https://agent-inter-op.vercel.app/.well-known/agent-card.json
- [ ] **Self-test passing**: https://agent-inter-op.vercel.app/api/selftest
- [ ] **UI loading correctly**: https://agent-inter-op.vercel.app/
- [ ] **Partner Connect working**: https://agent-inter-op.vercel.app/partner_connect
- [ ] **Test Harness functional**: https://agent-inter-op.vercel.app/test_harness

### Demo Environment
- [ ] **Browser tabs prepared**:
  - Main UI: https://agent-inter-op.vercel.app/
  - Partner Connect: https://agent-inter-op.vercel.app/partner_connect
  - Agent Card: https://agent-inter-op.vercel.app/.well-known/agent-card.json
- [ ] **Terminal ready** with prepared cURL commands
- [ ] **Backup demo data** available (patient_bcse.json)
- [ ] **Network connectivity** verified

### Contingency Preparation
- [ ] **Local server** ready as backup: `python app/main.py`
- [ ] **cURL recipes** copied to clipboard
- [ ] **Screenshot backups** of expected UI states
- [ ] **Demo script** printed for reference

---

## 5-Minute Demo Script

### 1. Opening - Agent Discovery (30 seconds)

**"Welcome to our Healthcare Interoperability demonstration. We're showing Language-First Interoperability - where agents communicate using natural language patterns, not just rigid APIs."**

```bash
# Show agent card discovery
curl https://agent-inter-op.vercel.app/.well-known/agent-card.json | jq
```

**Key points to highlight:**
- Protocol version 0.2.9 compliance
- Dual transport support (JSON-RPC + MCP)
- BCS-E scenario capability
- Streaming support enabled

### 2. Protocol Compliance Demo (1 minute)

**"Let's verify our protocol compliance with a quick self-test."**

```bash
# Self-test endpoint
curl https://agent-inter-op.vercel.app/api/selftest | jq
```

**Navigate to Partner Connect UI** (https://agent-inter-op.vercel.app/partner_connect)

**"This is our Partner Connect interface where external systems can test against our endpoints."**

- Enter endpoint: `https://agent-inter-op.vercel.app/api/bridge/bcse/a2a`
- Click "Ping (message/send)"
- Show JSON-RPC response in the logs

**Expected result:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "id": "...",
    "status": {"state": "working"},
    "history": [...]
  }
}
```

### 3. BCS End-to-End Workflow (2.5 minutes)

**"Now let's see the complete Breast Cancer Screening eligibility workflow."**

**Navigate to main UI** (https://agent-inter-op.vercel.app/)

#### Step 3a: A2A Protocol Demo (1 minute)
- Select **A2A Protocol** in top toggle
- Click **"Start Demo"**
- Show real-time transcript updates
- Click **"Send Applicant Info"**

**Expected flow:**
1. System message: "Starting BCS-E eligibility demo..."
2. A2A protocol initialization
3. Agent requests: "Provide sex, birthDate, last_mammogram (YYYY-MM-DD)"
4. Applicant submission processes
5. **Decision appears**: "Status: eligible" with rationale

#### Step 3b: MCP Protocol Demo (1 minute)
- Switch to **MCP Protocol**
- Click **"Reset"** then **"Start Demo"** 
- Show MCP triplet: begin → send → check
- Demonstrate conversation flow

**Key conversation:**
- MCP conversation started
- Agent: "Provide sex, birthDate, last_mammogram"
- System processes BCS-E evaluation
- **Final decision**: Eligibility determination with clear rationale

#### Step 3c: FHIR Integration (30 seconds)
**"Let's show live FHIR integration with real healthcare data."**

```bash
# Demo FHIR ingestion
curl -X POST https://agent-inter-op.vercel.app/api/bcse/ingest/demo | jq
```

**Expected response:**
```json
{
  "ok": true,
  "applicant_payload": {
    "sex": "female",
    "birthDate": "1968-05-10", 
    "last_mammogram": "2024-12-01"
  },
  "source": "demo"
}
```

### 4. Decision Rationale & Traceability (1 minute)

**"Our system provides full decision traceability and audit trails."**

#### Show Decision Logic
```bash
# Evaluate BCS-E criteria directly
curl -X POST https://agent-inter-op.vercel.app/api/bcse/evaluate \
  -H "Content-Type: application/json" \
  -d '{"sex": "female", "birthDate": "1968-05-10", "last_mammogram": "2024-12-01"}' | jq
```

**Expected result:**
```json
{
  "ok": true,
  "decision": {
    "status": "eligible",
    "rationale": ["Age 57, female, mammogram within 27 months."]
  }
}
```

#### Demonstrate Edge Cases
```bash
# Show ineligible case (male patient)
curl -X POST https://agent-inter-op.vercel.app/api/bcse/evaluate \
  -H "Content-Type: application/json" \
  -d '{"sex": "male", "birthDate": "1968-05-10", "last_mammogram": "2024-12-01"}' | jq
```

**Expected result:**
```json
{
  "ok": true,
  "decision": {
    "status": "ineligible",
    "rationale": ["Requires female sex."]
  }
}
```

**"Notice how our system clearly explains why each decision was made - critical for healthcare compliance and trust."**

---

## cURL Recipe Card (For Partners)

### A2A JSON-RPC Protocol
```bash
# Basic A2A message/send
curl -X POST https://agent-inter-op.vercel.app/api/bridge/bcse/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "parts": [{
          "kind": "text",
          "text": "{\"sex\":\"female\",\"birthDate\":\"1968-05-10\",\"last_mammogram\":\"2024-12-01\"}"
        }]
      }
    },
    "id": "demo-request"
  }'

# A2A tasks/get
curl -X POST https://agent-inter-op.vercel.app/api/bridge/bcse/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", 
    "method": "tasks/get",
    "params": {"id": "TASK_ID_FROM_PREVIOUS_RESPONSE"},
    "id": "get-task"
  }'

# A2A tasks/cancel  
curl -X POST https://agent-inter-op.vercel.app/api/bridge/bcse/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/cancel", 
    "params": {"id": "TASK_ID_TO_CANCEL"},
    "id": "cancel-task"
  }'
```

### MCP Protocol Triplet
```bash
# 1. Begin chat thread
CONV_RESPONSE=$(curl -s -X POST https://agent-inter-op.vercel.app/api/mcp/bcse/begin_chat_thread -d '{}')
CONV_ID=$(echo $CONV_RESPONSE | jq -r '.content[0].text | fromjson.conversationId')

# 2. Send message to chat thread
curl -X POST https://agent-inter-op.vercel.app/api/mcp/bcse/send_message_to_chat_thread \
  -H "Content-Type: application/json" \
  -d "{
    \"conversationId\": \"$CONV_ID\",
    \"message\": \"Please evaluate BCS-E eligibility for a female patient, age 56, with recent mammogram\"
  }"

# 3. Check replies
curl -X POST https://agent-inter-op.vercel.app/api/mcp/bcse/check_replies \
  -H "Content-Type: application/json" \
  -d "{
    \"conversationId\": \"$CONV_ID\",
    \"waitMs\": 2000
  }"
```

### Direct BCS-E Evaluation
```bash
# Eligible patient
curl -X POST https://agent-inter-op.vercel.app/api/bcse/evaluate \
  -H "Content-Type: application/json" \
  -d '{"sex": "female", "birthDate": "1968-05-10", "last_mammogram": "2024-12-01"}'

# Ineligible patient (wrong sex)
curl -X POST https://agent-inter-op.vercel.app/api/bcse/evaluate \
  -H "Content-Type: application/json" \
  -d '{"sex": "male", "birthDate": "1968-05-10", "last_mammogram": "2024-12-01"}'

# Needs more info (missing mammogram)
curl -X POST https://agent-inter-op.vercel.app/api/bcse/evaluate \
  -H "Content-Type: application/json" \
  -d '{"sex": "female", "birthDate": "1968-05-10"}'
```

---

## Rollback & Contingency Plan

### If Vercel is Down
1. **Immediate fallback**: Use local server
   ```bash
   cd /path/to/AgentInterOp
   python app/main.py
   # Demo at http://localhost:8000
   ```

2. **Update all URLs** in demo to `http://localhost:8000`
3. **Verify self-test**: `curl http://localhost:8000/api/selftest`

### If FHIR Integration Fails
1. **Switch to canned data**: Use `/api/bcse/ingest/demo` endpoint
2. **Emphasize**: "In production, this connects to live FHIR servers"
3. **Show static patient data**: Display contents of `app/demo/patient_bcse.json`

### If SSE Streaming Fails
1. **Use polling fallback**: MCP check_replies with waitMs
2. **Demonstrate**: `tasks/get` for task status polling
3. **Explain**: "Production systems support both streaming and polling"

### If UI is Broken
1. **Use Test Harness**: https://agent-inter-op.vercel.app/test_harness
2. **Pure cURL demo**: Focus on API responses
3. **Partner Connect**: Show partner integration interface

### If Demo Data is Wrong
**Backup BCS-E payloads:**
```json
{
  "eligible": {
    "sex": "female", 
    "birthDate": "1968-05-10",
    "last_mammogram": "2024-12-01"
  },
  "ineligible_age": {
    "sex": "female",
    "birthDate": "2010-01-01", 
    "last_mammogram": "2024-12-01"
  },
  "needs_more_info": {
    "sex": "female",
    "birthDate": "1968-05-10"
  }
}
```

---

## Demo Success Metrics

### Technical Demonstrations
- [ ] **Agent Card Discovery** working and spec-compliant
- [ ] **A2A JSON-RPC** method compliance (message/send, tasks/get, tasks/cancel)
- [ ] **MCP Triplet** workflow (begin → send → check)  
- [ ] **SSE Streaming** functional with proper event framing
- [ ] **BCS-E Logic** accurate (eligible/ineligible/needs-more-info)
- [ ] **FHIR Integration** demonstrated (live or canned)
- [ ] **Decision Rationale** clear and auditable

### Audience Engagement
- [ ] **Clear value proposition** communicated
- [ ] **Technical competency** demonstrated  
- [ ] **Interoperability benefits** explained
- [ ] **Partner integration** path shown
- [ ] **Questions answered** confidently
- [ ] **Follow-up interest** generated

### Key Messages Delivered
1. **"Language-First Interoperability"** - Agents communicate naturally
2. **"Dual Protocol Support"** - Flexible integration options
3. **"Healthcare-Grade Decisions"** - Transparent, auditable, compliant
4. **"Partner-Ready"** - Standard discovery and integration patterns
5. **"Production-Capable"** - Robust, scalable, monitored

---

## Post-Demo Actions

### Immediate (Within 1 hour)
- [ ] **Collect feedback** from attendees
- [ ] **Document issues** encountered during demo
- [ ] **Share cURL recipes** with interested partners
- [ ] **Schedule follow-ups** with engaged prospects

### Follow-up (Within 24 hours)  
- [ ] **Send thank you** emails with demo summary
- [ ] **Share GitHub repository** with demo code
- [ ] **Provide technical documentation** for integration
- [ ] **Schedule technical deep-dives** with interested partners

### Analysis (Within 1 week)
- [ ] **Demo performance review** - what worked/didn't work
- [ ] **Technical improvements** based on demo experience
- [ ] **Partner feedback integration** into roadmap
- [ ] **Next demo iteration** planning

---

## Emergency Contacts

- **Lead Developer**: [Contact info]
- **DevOps Support**: [Contact info]  
- **Product Manager**: [Contact info]
- **Technical Support**: [Contact info]

## Quick Reference URLs

- **Production**: https://agent-inter-op.vercel.app/
- **Agent Card**: https://agent-inter-op.vercel.app/.well-known/agent-card.json
- **Self-test**: https://agent-inter-op.vercel.app/api/selftest
- **Health**: https://agent-inter-op.vercel.app/health
- **Partner Connect**: https://agent-inter-op.vercel.app/partner_connect  
- **Test Harness**: https://agent-inter-op.vercel.app/test_harness
- **GitHub**: https://github.com/[username]/AgentInterOp

**Remember: Confidence, clarity, and technical competence. You've got this! 🚀**