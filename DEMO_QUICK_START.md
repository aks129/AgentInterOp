# 🚀 AgentInterOp - Quick Demo Start

## 30-Second Setup

```bash
# 1. Install dependencies (one-time)
pip install -e .

# 2. Set API key (optional, for custom scenarios)
export ANTHROPIC_API_KEY="your-key-here"

# 3. Start the server
python app/main.py
# OR
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

## 5-Minute Client Demo

### Option A: Guided Wizard (Best for New Clients)

1. Open: `http://localhost:8000`
2. Click **"Start Guided Demo"**
3. Follow the 4-step wizard
4. Done!

### Option B: Direct Access (Best for Quick Demo)

1. Open: `http://localhost:8000/simple`
2. Select scenario: **BCSE Screening**
3. Click **"Start New Conversation"**
4. Watch the magic happen!

## Key Features to Show

### 1. Dual Protocol Support ⚡
- Show both A2A and MCP protocols
- Switch between them mid-demo

### 2. FHIR Integration 🏥
- Connect to live FHIR server
- Import real patient data

### 3. Constitutional Agents 🛡️
- Show agent constitution
- Point out decision transparency

### 4. Custom Scenarios ✨
- Use natural language to describe a scenario
- Claude converts it to rules

## Pre-Loaded Demo Scenarios

- 🔬 **BCSE Screening** (Easiest - 30 seconds)
- 🧬 **Clinical Trial Matching** (Most Impressive - 2 minutes)
- 📋 **Prior Authorization** (Most Relatable - 1 minute)
- 👨‍⚕️ **Specialist Referrals** (1.5 minutes)
- 🎨 **Custom Scenario** (3 minutes)

## Resources

- **Full Demo Guide**: `DEMO_GUIDE.md`
- **Technical Docs**: `CLAUDE.md`
- **Landing Page**: `http://localhost:8000`
- **Quick Access**: `http://localhost:8000/simple`

---

**Ready? Start the server and wow your clients! 🎉**

```bash
python app/main.py
# Then open: http://localhost:8000
```
