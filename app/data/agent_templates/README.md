# Agent Templates

This directory contains JSON-based templates for creating healthcare agents quickly.

## Available Templates

### 1. Diabetes Monitoring Agent
**File:** `diabetes_monitoring.json`
**Domain:** Chronic Care
**Role:** Administrator

Monitors patient A1C levels, glucose readings, and medication adherence. Identifies trends and generates alerts for providers.

**Key Features:**
- A1C tracking (target < 7.0%)
- Glucose monitoring (80-130 mg/dL target)
- Medication adherence scoring
- Risk stratification
- Automated alerts

**Use Cases:**
- Chronic disease management programs
- Remote patient monitoring
- Population health initiatives

---

### 2. Medication Reconciliation Agent
**File:** `medication_reconciliation.json`
**Domain:** Medication Management
**Role:** Administrator

Identifies medication discrepancies, drug interactions, and safety issues during care transitions.

**Key Features:**
- Multi-source medication list comparison
- Drug-drug interaction checking
- Allergy cross-referencing
- Dosage validation
- Discrepancy reporting

**Use Cases:**
- Hospital admissions
- Care transitions
- Post-discharge follow-up
- Pharmacy benefits management

---

### 3. Social Determinants of Health (SDOH) Agent
**File:** `social_determinants.json`
**Domain:** Population Health
**Role:** Applicant

Screens for social needs and connects patients with community resources.

**Key Features:**
- Food insecurity screening
- Housing stability assessment
- Transportation barrier identification
- Community resource matching
- Referral tracking

**Use Cases:**
- Value-based care programs
- Community health centers
- Care coordination
- Health equity initiatives

---

## Using Templates

### Via API

```bash
# List all templates
curl http://localhost:8000/api/agents/templates/list

# Get specific template
curl http://localhost:8000/api/agents/templates/template_diabetes_monitoring

# Create agent from template
curl -X POST http://localhost:8000/api/agents/templates/template_diabetes_monitoring/instantiate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Agent Name",
    "description": "Customized for my organization"
  }'
```

### Via UI

1. Navigate to Agent Studio: `http://localhost:8000/studio`
2. Click "Create from Template"
3. Select template
4. Customize settings
5. Click "Create Agent"

### Via Demo Script

```bash
# Run interactive demo
bash tools/demo_templates.sh

# Run against remote server
bash tools/demo_templates.sh https://your-server.com
```

---

## Template Structure

Each template JSON file contains:

```json
{
  "id": "template_<name>",
  "name": "Display Name",
  "description": "What this agent does",
  "purpose": "Primary objective",
  "domain": "healthcare_domain",
  "role": "applicant|administrator",

  "constitution": {
    "purpose": "...",
    "domain": "...",
    "constraints": [...],
    "ethics": [...],
    "capabilities": [...]
  },

  "plan": {
    "goals": [...],
    "tasks": [...],
    "workflows": [...],
    "success_criteria": [...]
  },

  "agent_card": {
    "protocolVersion": "0.2.9",
    "preferredTransport": "JSONRPC",
    "name": "...",
    "description": "...",
    "role": "...",
    "capabilities": {...},
    "skills": [...],
    "methods": [...],
    "supported_formats": [...]
  },

  "version": "1.0.0",
  "status": "template",
  "tags": ["tag1", "tag2"],

  "demo_data": {
    // Optional sample data for testing
  }
}
```

---

## Creating Custom Templates

1. **Copy an existing template** as a starting point
2. **Update the ID** to be unique: `template_<your_name>`
3. **Customize the fields:**
   - name, description, purpose
   - domain (see available domains in API)
   - role (applicant or administrator)
4. **Define the constitution:**
   - Clear purpose statement
   - Operational constraints
   - Ethical guidelines
   - Technical capabilities
5. **Build the operational plan:**
   - Primary goals
   - Task definitions with inputs/outputs
   - Workflow sequences
   - Success criteria
6. **Configure the agent card:**
   - Update skills with scenario-specific inputs/outputs
   - Define supported methods
   - Set capabilities flags
7. **Add demo data** (optional) for testing
8. **Save** to this directory
9. **Test** via API: `GET /api/agents/templates/<your_template_id>`

---

## Template Best Practices

### 1. Clear Purpose
- State the agent's primary objective clearly
- Focus on one main healthcare use case
- Avoid overly broad or generic purposes

### 2. Specific Constraints
- Define operational boundaries
- Include clinical guideline references
- Specify data requirements and sources

### 3. Ethical Guidelines
- Address patient privacy and confidentiality
- Consider equity and access issues
- Define decision-making principles

### 4. Measurable Success Criteria
- Use quantifiable metrics (%, seconds, accuracy rates)
- Include both clinical and operational measures
- Set realistic targets

### 5. Comprehensive Capabilities
- List all FHIR resources the agent processes
- Specify integration points (FHIR, MCP, databases)
- Document AI/ML capabilities if used

---

## Healthcare Domains

Available domains for templates:

- `preventive_screening` - Cancer screening and prevention
- `clinical_trial` - Clinical trial enrollment
- `referral_specialist` - Specialist referral coordination
- `prior_auth` - Prior authorization processing
- `chronic_care` - Chronic disease management
- `emergency_care` - Emergency care triage
- `mental_health` - Mental health services
- `pharmacy` - Pharmacy benefits management
- `medication_management` - Medication safety and reconciliation
- `population_health` - Population health and SDOH

---

## A2A Protocol Compliance

All templates generate A2A-compliant agents with:

- **Protocol Version**: 0.2.9+
- **Transport**: JSONRPC over HTTP
- **Agent Card**: Standards-compliant discovery endpoint
- **Skills**: Structured definitions with inputs/outputs
- **Methods**: Scenario-appropriate methods
- **Artifacts**: FHIR-compliant when applicable

---

## Support

- **API Documentation**: http://localhost:8000/docs
- **Agent Studio**: http://localhost:8000/studio
- **Main Documentation**: See `/docs` directory
- **Issues**: Report via GitHub Issues

---

## License

MIT License - See main LICENSE file
