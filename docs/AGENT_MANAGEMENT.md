# Healthcare Agent Management System

## Overview

The Healthcare Agent Management System provides a comprehensive UI and API for creating, managing, and deploying A2A-compliant healthcare agents using **constitution-based design principles** (inspired by modern agent development frameworks like Google's ADK).

## Features

### ✨ Key Capabilities

- **🤖 Dynamic Agent Creation**: Create healthcare agents through an intuitive UI
- **📋 A2A Compliance**: All agents follow the A2A specification for interoperability
- **🏗️ Constitution-Based Framework**: Agent development with spec-kit driven approach (purpose, constraints, ethics, capabilities)
- **🏥 Healthcare-Specific**: Pre-configured domains and templates for healthcare scenarios
- **🔄 Protocol Support**: A2A (JSON-RPC) and MCP protocol implementations
- **📊 FHIR Integration**: Built-in support for FHIR R4 resources
- **🧪 Testing Framework**: Comprehensive Playwright E2E tests

## Architecture

### Components

```
app/
├── agents/
│   ├── registry.py          # Agent registry and storage
│   ├── administrator.py      # Administrator agent implementation
│   └── applicant.py         # Applicant agent implementation
├── api/
│   └── agents.py            # Agent management REST API
├── web/
│   └── templates/
│       └── agent_management.html  # Agent management UI
└── data/
    └── agents/              # Agent storage (JSON files)
```

### Agent Structure

Each healthcare agent includes:

1. **Constitution** (Design Framework)
   - Purpose: Primary objective
   - Domain: Healthcare domain
   - Constraints: Operational boundaries
   - Ethics: Ethical guidelines
   - Capabilities: Technical abilities

2. **Operational Plan**
   - Goals: Primary objectives
   - Tasks: Task definitions
   - Workflows: Process workflows
   - Success Criteria: Performance metrics

3. **A2A Agent Card**
   - Protocol version
   - Skills and methods
   - Supported formats
   - Transport preferences

## Usage

### Accessing the UI

Navigate to: `http://localhost:8000/agents`

### Creating an Agent

1. **Click "Create New Agent"**
2. **Fill in Basic Information**:
   - Agent Name
   - Description
   - Purpose
   - Healthcare Domain
   - Role (Applicant/Administrator)

3. **Define Constitution**:
   - Constraints (operational boundaries)
   - Ethics (ethical guidelines)
   - Capabilities (technical abilities)

4. **Define Operational Plan**:
   - Goals (primary objectives)
   - Success Criteria (performance metrics)

5. **Click "Create Agent"**

### Using Templates

Pre-built templates are available for common healthcare scenarios:

- **Breast Cancer Screening Eligibility (BCS-E)**
- **Clinical Trial Enrollment**
- **Prior Authorization**
- **Diabetes Monitoring** (NEW!)
- **Medication Reconciliation** (NEW!)
- **Social Determinants of Health (SDOH) Screening** (NEW!)

Click "Templates" tab and select "Use Template" to create from a template.

#### Creating Agents from Templates via API

```bash
# List all templates
curl http://localhost:8000/api/agents/templates/list

# Get specific template
curl http://localhost:8000/api/agents/templates/template_diabetes_monitoring

# Instantiate agent from template
curl -X POST http://localhost:8000/api/agents/templates/template_diabetes_monitoring/instantiate \
  -H "Content-Type: application/json" \
  -d '{"name": "Custom Diabetes Monitor"}'
```

### Managing Agents

- **View**: See detailed agent information
- **Activate/Deactivate**: Enable or disable agents
- **Archive**: Soft-delete agents
- **Filter**: Filter by status, domain, or role

## API Reference

### List Agents

```bash
GET /api/agents/
```

Query Parameters:
- `status`: Filter by status (active, inactive, archived)
- `domain`: Filter by healthcare domain
- `role`: Filter by role (applicant, administrator)

### Get Agent

```bash
GET /api/agents/{agent_id}
```

### Create Agent

```bash
POST /api/agents/
Content-Type: application/json

{
  "name": "Agent Name",
  "description": "Agent description",
  "purpose": "Agent purpose",
  "domain": "preventive_screening",
  "role": "administrator",
  "constitution": { ... },
  "plan": { ... },
  "agent_card": { ... }
}
```

### Update Agent

```bash
PUT /api/agents/{agent_id}
Content-Type: application/json

{
  "status": "inactive",
  "description": "Updated description"
}
```

### Delete Agent

```bash
DELETE /api/agents/{agent_id}
```

### Get Agent Card (A2A Discovery)

```bash
GET /api/agents/{agent_id}/card
```

### Create Sample BCS-E Agent

```bash
POST /api/agents/samples/bcse
```

### List Domains

```bash
GET /api/agents/domains/list
```

### List Templates

```bash
GET /api/agents/templates/list
```

## Healthcare Domains

Available domains for agent specialization:

- **Preventive Screening**: Cancer screening and prevention programs
- **Clinical Trial**: Clinical trial enrollment and matching
- **Specialist Referral**: Specialist referral coordination
- **Prior Authorization**: Insurance prior authorization processing
- **Chronic Care**: Chronic disease management programs
- **Emergency Care**: Emergency care triage and coordination
- **Mental Health**: Mental health service coordination
- **Pharmacy**: Pharmacy benefits management

## Sample Agent: BCS-E

The Breast Cancer Screening Eligibility (BCS-E) agent demonstrates full implementation:

### Constitution

- **Purpose**: Determine eligibility for breast cancer screening benefits
- **Domain**: Preventive Screening
- **Constraints**:
  - USPSTF guidelines compliance
  - Age range: 50-74 years
  - Gender: Female patients only
  - Mammogram history verification (27 months)

### Capabilities

- FHIR R4 resource processing
- Age calculation from birthDate
- Mammogram history verification
- QuestionnaireResponse generation
- Decision artifact creation

### Methods

- `requirements_message()`: Returns required data fields
- `validate()`: Evaluates eligibility criteria
- `finalize()`: Generates decision artifacts
- `load_patient()`: Loads patient FHIR bundle
- `answer_requirements()`: Creates QuestionnaireResponse

## Testing

### E2E Tests with Playwright

Install dependencies:

```bash
npm install
npm run playwright:install
```

Run tests:

```bash
# Run all tests
npm run test:e2e

# Run in headed mode (see browser)
npm run test:e2e:headed

# Run in UI mode (interactive)
npm run test:e2e:ui

# Run specific browser
npm run test:e2e:chromium

# Debug mode
npm run test:e2e:debug

# View test report
npm run test:report
```

### Test Coverage

The test suite covers:

- ✅ Page rendering and navigation
- ✅ Tab switching
- ✅ Agent creation workflow
- ✅ Form validation
- ✅ Agent filtering
- ✅ Agent management operations
- ✅ API integration
- ✅ Error handling
- ✅ Responsive design
- ✅ Mobile viewports

## A2A Compliance

All agents are A2A-compliant with:

- **Protocol Version**: 0.2.9+
- **Transport**: JSONRPC over HTTP
- **Methods**: message/send, message/stream, tasks/get, tasks/cancel, tasks/resubscribe
- **Agent Cards**: Standard agent card format for discovery
- **Skills**: Structured skill definitions with inputs/outputs
- **Artifacts**: FHIR-compliant artifacts with proper MIME types

## Constitution-Based Design Approach

The system implements a constitution-based agent development approach (inspired by frameworks like Google's ADK):

### Constitution-Based Development

Agents are defined by their:
- **Purpose**: Clear statement of intent
- **Constraints**: Operational boundaries
- **Ethics**: Ethical guidelines
- **Capabilities**: Technical abilities

### Spec-Kit Driven Framework

- **Plans**: Structured operational plans with goals and tasks
- **Tasks**: Discrete units of work with inputs/outputs
- **Workflows**: Multi-step processes
- **Success Criteria**: Measurable performance metrics

## Security Considerations

- **Input Validation**: All inputs validated on client and server
- **Authentication**: Integrate with your auth system
- **Authorization**: Role-based access control recommended
- **Data Encryption**: Use HTTPS in production
- **Audit Logging**: Track all agent operations
- **FHIR Security**: Follow SMART on FHIR guidelines

## Deployment

### Local Development

```bash
# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access UI
open http://localhost:8000/agents
```

### Production (Vercel)

The system is configured for serverless deployment on Vercel:

```bash
# Deploy to Vercel
vercel deploy

# Production deployment
vercel --prod
```

Agent data is stored in `/tmp/agents` on Vercel (ephemeral) or persistent storage should be configured.

### Docker

```bash
# Build image
docker build -t agent-interop .

# Run container
docker run -p 8000:8000 agent-interop
```

## Future Enhancements

- [ ] Agent versioning and rollback
- [ ] Agent collaboration workflows
- [ ] Real-time agent monitoring dashboard
- [ ] Agent performance analytics
- [ ] Agent marketplace
- [ ] Multi-tenant support
- [ ] Agent testing sandbox
- [ ] Integration with external agent platforms

## Contributing

To add a new healthcare domain:

1. Add domain to `app/api/agents.py` in `list_domains()` endpoint
2. Create scenario implementation in `app/scenarios/`
3. Register scenario in `app/scenarios/registry.py`
4. Create agent template in `list_templates()` endpoint

## Support

For issues or questions:
- GitHub Issues: https://github.com/anthropics/agentinterop/issues
- Documentation: https://docs.example.com
- Email: support@example.com

## License

MIT License - See LICENSE file for details
