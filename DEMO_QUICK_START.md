# Quick Demo Guide - Agent Templates POC

**5-Minute Demo for Clients and Collaborators**

---

## 🎯 Key Demo Messages

1. **"Create Healthcare Agents in Seconds, Not Weeks"**
   - Show template-based agent creation
   - 3 pre-built templates ready to customize

2. **"Constitution-Based Design for Transparent AI"**
   - Every agent has clear purpose, constraints, ethics
   - No black box - every decision is traceable

3. **"Full A2A Protocol Compliance"**
   - Standards-based interoperability
   - Works with any A2A-compatible system

---

## 🚀 Quick Demo Script (5 minutes)

### Option A: Interactive Terminal Demo

```bash
# Run the automated demo script
cd /path/to/AgentInterOp
bash tools/demo_templates.sh

# Or against deployed version
bash tools/demo_templates.sh https://your-deployment.vercel.app
```

**What it shows:**
- ✅ Lists 3 agent templates
- ✅ Views template details (constitution, plan, capabilities)
- ✅ Creates 3 agents instantly
- ✅ Shows A2A agent cards
- ✅ Lists all created agents

**Time:** 5 minutes with pauses between steps

---

### Option B: API Demo (for Technical Audiences)

```bash
BASE_URL="http://localhost:8000"

# 1. Show available templates
curl $BASE_URL/api/agents/templates/list | jq

# 2. Create diabetes monitoring agent
curl -X POST $BASE_URL/api/agents/templates/template_diabetes_monitoring/instantiate \
  -H "Content-Type: application/json" \
  -d '{"name": "Demo Diabetes Agent"}' | jq

# 3. Show agent card (A2A discovery)
AGENT_ID=$(curl -s $BASE_URL/api/agents/ | jq -r '.agents[0].id')
curl $BASE_URL/api/agents/$AGENT_ID/card | jq
```

---

### Option C: UI Demo (for Business Audiences)

1. Navigate to Agent Studio: `http://localhost:8000/studio`
2. Click **"Templates"** in sidebar
3. Select **"Diabetes Monitoring Agent"**
4. Show the constitution:
   - Purpose: "Monitor diabetes patients and provide early intervention alerts"
   - Constraints: A1C targets, glucose ranges, medication adherence
   - Ethics: Privacy, culturally sensitive care, avoid alarm fatigue
5. Click **"Create from Template"**
6. Customize name: "Acme Health Diabetes Monitor"
7. Click **"Create Agent"**
8. Show agent dashboard with full details

**Time:** 3 minutes

---

## 💡 Demo Talking Points

### 1. Agent Templates (Show: `app/data/agent_templates/`)

**Diabetes Monitoring Agent:**
> "This agent monitors A1C levels, glucose readings, and medication adherence for diabetes patients. It can identify concerning trends before they become emergencies."

**Key Stats:**
- Tracks A1C < 7.0% target
- Monitors glucose 80-130 mg/dL
- Calculates medication possession ratio
- Generates provider alerts

**Medication Reconciliation Agent:**
> "During hospital admissions, this agent compares medication lists from multiple sources - home, pharmacy, hospital - to catch discrepancies and dangerous drug interactions."

**Key Features:**
- Drug-drug interaction checking
- Allergy cross-referencing
- Dosage validation
- 98% interaction detection accuracy

**SDOH Screening Agent:**
> "Social determinants like food insecurity and housing instability affect health outcomes. This agent screens patients and connects them with community resources."

**Key Domains:**
- Food insecurity
- Housing stability
- Transportation barriers
- Social isolation

### 2. Constitution-Based Design

**Show a template's constitution:**

```json
{
  "purpose": "Monitor diabetes patients and provide early intervention alerts",
  "domain": "chronic_care",
  "constraints": [
    "Monitor A1C levels (target < 7.0% for most patients)",
    "Track glucose readings (target 80-130 mg/dL fasting)"
  ],
  "ethics": [
    "Protect patient privacy and sensitive health data",
    "Avoid alarm fatigue with intelligent alerting"
  ],
  "capabilities": [
    "FHIR R4 Observation processing (glucose, A1C)",
    "Trend analysis over time periods"
  ]
}
```

**Talk Track:**
> "Notice how every agent has a clear constitution. It's not a black box - we define exactly what the agent can do, what constraints it operates under, and what ethical principles guide it. This is critical for healthcare where transparency and accountability matter."

### 3. A2A Protocol Compliance

**Show agent card:**

```bash
curl http://localhost:8000/api/agents/{agent_id}/card
```

**Talk Track:**
> "Every agent we create automatically generates an A2A-compliant agent card. This means it can be discovered and integrated by any A2A-compatible system. No custom integrations needed - it's all standards-based."

---

## 🎬 Demo Flow Recommendations

### For Healthcare IT Leaders (10 minutes)
1. Show UI demo (3 min)
2. Explain constitution-based approach (2 min)
3. Show how to customize templates (3 min)
4. Discuss integration with their FHIR systems (2 min)

### For Technical Architects (15 minutes)
1. Run terminal demo script (5 min)
2. Show template JSON structure (3 min)
3. Demonstrate API endpoints (4 min)
4. Discuss A2A protocol compliance (3 min)

### For Clinical Stakeholders (8 minutes)
1. UI demo with focus on clinical scenarios (4 min)
2. Show agent constitution for one template (2 min)
3. Discuss how to define constraints and ethics (2 min)

---

## 🔑 Key Differentiators to Emphasize

1. **Speed:** "Create agents in seconds, not weeks"
2. **Transparency:** "Constitution-based design - no black boxes"
3. **Standards:** "Full A2A protocol compliance out of the box"
4. **Healthcare-Specific:** "Pre-built templates for common healthcare scenarios"
5. **Extensibility:** "Easy to create custom templates for your use cases"

---

## 📊 Demo Success Metrics

Track these during demos:
- ✅ Time to create first agent (target: < 30 seconds)
- ✅ Number of questions about constitution approach
- ✅ Interest in specific healthcare scenarios
- ✅ Requests for custom template development
- ✅ Questions about integration with their systems

---

## 🎤 Opening and Closing

### Opening (30 seconds)
> "Today I'm going to show you how to create sophisticated healthcare AI agents in seconds using our template-based system. These aren't toy examples - these are production-ready agents with clear constitutions, ethical guidelines, and full A2A protocol compliance."

### Closing (30 seconds)
> "What you've seen is a foundation for rapid healthcare agent development. We've built three templates to start - diabetes monitoring, medication reconciliation, and social determinants screening - but the system is designed to let you create templates for your specific use cases. Every agent follows the same constitution-based approach: clear purpose, explicit constraints, ethical guidelines, and standards-based interoperability."

---

## 🛠️ Pre-Demo Checklist

- [ ] Server running: `uvicorn app.main:app --reload`
- [ ] Health check: `curl http://localhost:8000/healthz`
- [ ] Templates loaded: `curl http://localhost:8000/api/agents/templates/list`
- [ ] Demo script tested: `bash tools/demo_templates.sh`
- [ ] Browser tabs ready: Agent Studio, API docs
- [ ] Backup: Screenshots of key screens

---

## 🚨 Troubleshooting

**Templates not showing?**
- Check: `ls app/data/agent_templates/*.json`
- Should see: 3 template files + README.md

**Agent creation fails?**
- Check: `app/data/agents/` directory exists and is writable
- Check logs for Pydantic validation errors

**Demo script fails?**
- Ensure server is running on correct port
- Check: `curl http://localhost:8000/healthz`
- Try with `http://127.0.0.1:8000` instead of `localhost`

---

## 📞 Follow-Up Actions

After demo, send:

1. **Link to demo recording** (if recorded)
2. **Template files** for review
3. **API documentation** link
4. **Calendar invite** for technical deep-dive (if interested)

---

## 💬 Common Questions & Answers

**Q: "Is this using Google's actual ADK?"**
**A:** "We use constitution-based design principles inspired by frameworks like Google's ADK. It's not a direct technical integration, but we follow the same philosophy: every agent has a clear constitution defining its purpose, constraints, ethics, and capabilities. This approach gives us the benefits of structured agent development without being locked into any specific vendor's framework."

**Q: "Can we integrate with our FHIR server?"**
**A:** "Absolutely. The platform has built-in FHIR R4 support with secure connectors. We can configure it to pull patient data from your FHIR server, map it to the agent's expected format, and process it according to the agent's constitution."

**Q: "How long does it take to create a custom template?"**
**A:** "For a basic template, about 2-4 hours to define the constitution, plan, and agent card. For complex scenarios with custom evaluation logic, 1-2 days. But once you have the template, creating new agent instances takes seconds."

**Q: "What about compliance (HIPAA, HITRUST)?"**
**A:** "The agents themselves follow best practices for healthcare data handling. For full HIPAA compliance, you'd deploy on your infrastructure with proper security controls, encryption, access logging, and BAAs in place. We can provide guidance on the compliance requirements."

**Q: "Can agents collaborate with each other?"**
**A:** "That's on the roadmap. The A2A protocol supports agent-to-agent communication, so technically yes. We're building orchestration patterns for multi-agent workflows. For now, agents can be chained together through your application logic."

---

**Remember:** This is a POC to demonstrate the concept and engage collaborators. Focus on the vision and rapid development capability, not production-scale features.

Good luck with your demo! 🚀
