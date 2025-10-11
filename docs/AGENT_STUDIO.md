# Agent Studio - Healthcare Agent Development Platform

## Overview

**Agent Studio** is a comprehensive, enterprise-grade front-end platform for developing, configuring, and managing healthcare agents with A2A protocol compliance and Google ADK framework integration.

**Access:** `http://localhost:8000/studio` (local) or `https://your-app.vercel.app/studio` (production)

---

## 🎯 Key Features

### 1. **Dashboard Overview**
- Real-time statistics (agents, use cases, applications)
- Quick action buttons for common tasks
- Recent agent activity tracking
- Performance metrics and trends

### 2. **Agent Management**
- Create, configure, and customize agents
- Visual agent cards with status indicators
- Bulk operations support
- Template-based creation
- Version control

### 3. **Constitution Explorer**
- Interactive constitution viewer and editor
- Define agent purpose, constraints, ethics, capabilities
- Live validation and error checking
- Template library for common patterns
- Version history tracking

### 4. **A2A Protocol Configuration**
- Complete A2A v0.2.9+ settings
- Protocol version management
- Transport configuration (JSON-RPC, HTTP, WebSocket)
- Capability toggles (streaming, FHIR, multi-protocol)
- Agent discovery endpoint setup
- Base URL configuration

### 5. **ADK Framework Settings**
- Google Agent Development Kit integration
- Constitution-based vs Spec-kit driven modes
- Task template library
- Auto-validation features
- Plan generation tools
- Agent type selection

### 6. **CQL/SQL Framework**
- Clinical Quality Language (CQL) editor
- SQL query builder
- Live query execution
- Result visualization
- Query validation
- Saved query library
- FHIR-based data queries

### 7. **FHIR MCP Configuration**
- FHIR server connection management
- Authentication setup (Bearer, OAuth2, SMART on FHIR)
- FHIR version selection (R4, R4B, R5)
- MCP feature toggles
- Resource type management
- Connection testing
- Live query execution

### 8. **Use Cases Library**
- 6 pre-built healthcare use cases
- Category filtering (screening, diagnosis, treatment, monitoring, admin)
- Complexity levels (basic, intermediate, advanced)
- Status tracking
- Tag-based organization
- Interactive preview

### 9. **Application Catalog**
- Healthcare application registry
- Integration management
- Version tracking
- Configuration interface
- Testing capabilities

---

## 🚀 Getting Started

### First Time Setup

1. **Access Agent Studio**
   ```
   http://localhost:8000/studio
   ```

2. **Create Your First Agent**
   - Click "Create New Agent" on dashboard
   - Fill in basic information
   - Select healthcare domain
   - Choose agent role (Applicant or Administrator)
   - Click "Create Agent"

3. **Explore Use Cases**
   - Navigate to "Use Cases" in sidebar
   - Browse 6 pre-built healthcare scenarios
   - Click on a use case to view details
   - Use as template for new agents

4. **Configure A2A Protocol**
   - Go to "A2A Protocol" section
   - Set protocol version
   - Configure transport method
   - Enable desired capabilities
   - Save configuration

---

## 📋 User Guide

### Navigation

The sidebar provides access to all major sections:

**Dashboard**
- 📊 Overview - Statistics and quick actions
- 🤖 Agents - Agent management

**Configuration**
- 📜 Constitutions - Agent constitutions
- 🔄 A2A Protocol - Protocol settings
- ⚙️ ADK Framework - Framework configuration
- 🏥 FHIR MCP - FHIR and MCP setup

**Data & Logic**
- 📝 CQL/SQL Framework - Query editor
- 💼 Use Cases - Use case library

**Applications**
- 📦 App Catalog - Application management

### Creating an Agent

**Step 1: Basic Information**
```
Agent Name: Diabetes Monitoring Agent
Description: Monitors patient vitals and alerts for diabetes management
Purpose: Automate diabetes monitoring and risk assessment
Domain: Chronic Care (select from dropdown)
Role: Administrator (processes data)
```

**Step 2: Constitution (Optional - can edit later)**
- Navigate to "Constitutions" section
- Select your agent
- Edit purpose, constraints, ethics, capabilities
- Save changes

**Step 3: Configure A2A**
- Go to "A2A Protocol"
- Enable required capabilities
- Set base URL if exposing externally
- Save configuration

### Managing Constitutions

1. **View Constitution**
   - Navigate to "Constitutions"
   - Select agent from dropdown
   - Review current constitution

2. **Edit Constitution**
   - Click in editor panel on right
   - Update purpose, constraints, ethics, capabilities
   - Click "Save"

3. **Constitution Components**
   - **Purpose**: Primary objective (single sentence)
   - **Constraints**: Operational boundaries (list)
   - **Ethics**: Ethical guidelines (list)
   - **Capabilities**: Technical abilities (list)

### Using CQL/SQL Framework

**CQL Example:**
```cql
library DiabetesMonitoring version '1.0.0'

using FHIR version '4.0.1'

context Patient

define "Has Diabetes":
  exists ([Condition: "Diabetes Mellitus"])

define "Recent HbA1c":
  [Observation: "HbA1c"] O
    where O.effectiveDateTime during Interval[Today() - 90 days, Today()]

define "Needs Monitoring":
  "Has Diabetes" and not exists "Recent HbA1c"
```

**SQL Example:**
```sql
SELECT
    p.id,
    p.name,
    c.code as condition,
    o.value as hba1c,
    o.effectiveDate
FROM patients p
JOIN conditions c ON p.id = c.patient_id
LEFT JOIN observations o ON p.id = o.patient_id
WHERE c.code = 'diabetes'
  AND (o.code = 'hba1c' OR o.id IS NULL)
  AND (o.effectiveDate > DATEADD(day, -90, GETDATE()) OR o.id IS NULL)
```

**Steps:**
1. Select CQL or SQL tab
2. Write your query
3. Click "Validate" to check syntax
4. Click "Execute" to run query
5. View results in "Results" tab
6. Click "Save Current" to add to library

### FHIR Configuration

**Connection Setup:**
1. Go to "FHIR MCP" section
2. Enter FHIR Base URL: `https://fhir.example.com/r4`
3. Select FHIR Version: R4 (4.0.1)
4. Choose Authentication Type
5. Enter Bearer Token (if required)
6. Click "Test Connection"

**MCP Features:**
- Enable FHIR MCP: Toggle on
- Free Text Context: Toggle on/off
- Local Bundle Access: Toggle on/off

**Test Query:**
1. Select Resource Type (Patient, Observation, etc.)
2. Enter Search Parameters: `_id=123` or `birthdate=gt1970-01-01`
3. Click "Execute"
4. View results

### Exploring Use Cases

**Available Use Cases:**

1. **Breast Cancer Screening Eligibility (BCS-E)**
   - Category: Screening
   - Complexity: Intermediate
   - Description: USPSTF guideline-based screening eligibility

2. **Clinical Trial Patient Matching**
   - Category: Treatment
   - Complexity: Advanced
   - Description: Match patients to trials based on criteria

3. **Prior Authorization Processing**
   - Category: Administrative
   - Complexity: Intermediate
   - Description: Automate insurance prior authorizations

4. **Chronic Disease Monitoring**
   - Category: Monitoring
   - Complexity: Intermediate
   - Description: Monitor vitals and alert for chronic conditions

5. **Specialist Referral Routing**
   - Category: Administrative
   - Complexity: Basic
   - Description: Route patients to appropriate specialists

6. **Medication Reconciliation**
   - Category: Treatment
   - Complexity: Intermediate
   - Description: Reconcile medications across care transitions

**Filtering:**
- By Category: screening, diagnosis, treatment, monitoring, administrative
- By Complexity: basic, intermediate, advanced
- By Status: active, draft, deprecated

---

## 🔧 Configuration Reference

### A2A Protocol Configuration

```javascript
{
  "protocolVersion": "0.2.9",
  "preferredTransport": "JSONRPC",
  "baseUrl": "https://your-agent.example.com",
  "capabilities": {
    "streaming": true,
    "multiProtocol": true,
    "fhir": true
  },
  "discoveryEndpoint": "/.well-known/agent-card.json"
}
```

### ADK Framework Settings

```javascript
{
  "mode": "constitution",           // or "spec-kit", "hybrid"
  "defaultAgentType": "healthcare", // or "workflow", "data", "decision"
  "features": {
    "autoValidation": true,
    "constitutionTemplates": true,
    "planGeneration": true
  }
}
```

### FHIR MCP Configuration

```javascript
{
  "fhirBaseUrl": "https://fhir.example.com/r4",
  "fhirVersion": "4.0.1",
  "authType": "bearer",              // or "oauth2", "smart", "none"
  "bearerToken": "your-token-here",
  "mcpFeatures": {
    "enableFhirMcp": true,
    "freeTextContext": true,
    "localBundleAccess": true
  },
  "supportedResources": [
    "Patient", "Observation", "Procedure",
    "Condition", "MedicationRequest", "DocumentReference"
  ]
}
```

---

## 💡 Best Practices

### Agent Development

1. **Start with Use Cases**
   - Browse the use case library first
   - Use templates as starting points
   - Customize for your specific needs

2. **Define Clear Constitutions**
   - Write specific, actionable constraints
   - Include all relevant ethical guidelines
   - List complete capabilities

3. **Test Incrementally**
   - Test A2A configuration first
   - Validate FHIR connectivity
   - Test CQL queries independently
   - Integration test full workflows

4. **Version Control**
   - Save configurations frequently
   - Document changes
   - Test before deploying

### Query Development

1. **CQL Best Practices**
   - Use meaningful library names
   - Include version numbers
   - Comment complex logic
   - Test with real data

2. **SQL Best Practices**
   - Optimize queries for performance
   - Use appropriate indexes
   - Limit result sets
   - Handle null values

### FHIR Integration

1. **Security**
   - Always use HTTPS in production
   - Store tokens securely
   - Implement proper authentication
   - Follow SMART on FHIR guidelines

2. **Performance**
   - Use search parameters efficiently
   - Implement pagination
   - Cache when appropriate
   - Monitor API usage

---

## 🎨 UI Components

### Dashboard Stats Cards
- Display key metrics
- Show trend indicators
- Color-coded status
- Click for details

### Configuration Panels
- Toggle switches for features
- Input fields with validation
- Dropdown selects
- Save/Cancel actions

### Code Editors
- Syntax highlighting
- Line numbers
- Error indicators
- Auto-completion (coming soon)

### List Items
- Title and metadata
- Status badges
- Action buttons
- Hover effects

### Modal Dialogs
- Form inputs
- Validation messages
- Submit/Cancel buttons
- Close on escape

---

## 🔒 Security

### Authentication
- Integrate with your authentication system
- Role-based access control recommended
- Audit all configuration changes

### Data Protection
- All sensitive data encrypted in transit (HTTPS)
- Bearer tokens masked in UI
- Configuration saved securely
- Access logs maintained

### FHIR Security
- Follow SMART on FHIR specification
- Implement proper scopes
- Use OAuth 2.0 for authorization
- Validate all input

---

## 📊 API Integration

Agent Studio integrates with these APIs:

```
GET  /api/agents/                    # List agents
POST /api/agents/                    # Create agent
GET  /api/agents/{id}                # Get agent
PUT  /api/agents/{id}                # Update agent
GET  /api/agents/{id}/card           # Get A2A card
GET  /api/agents/domains/list        # List domains
GET  /api/agents/templates/list      # List templates
POST /api/agents/samples/bcse        # Create sample
```

---

## 🚢 Deployment

### Local Development
```bash
# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access Agent Studio
open http://localhost:8000/studio
```

### Production (Vercel)
```bash
# Deploy
vercel deploy

# Production
vercel --prod

# Access
https://your-app.vercel.app/studio
```

### Docker
```bash
# Build
docker build -t agent-studio .

# Run
docker run -p 8000:8000 agent-studio

# Access
http://localhost:8000/studio
```

---

## 🎯 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + S` | Save current configuration |
| `Ctrl/Cmd + N` | Create new agent |
| `Ctrl/Cmd + K` | Open search |
| `Esc` | Close modal |
| `Ctrl/Cmd + Enter` | Execute query |
| `Ctrl/Cmd + /` | Comment/Uncomment |

---

## 🐛 Troubleshooting

### Agent Not Appearing
- Refresh the page
- Check browser console for errors
- Verify API endpoint is accessible
- Check agent status is "active"

### CQL Validation Errors
- Check syntax matches CQL specification
- Verify FHIR version compatibility
- Ensure all references are defined
- Test with simpler expressions first

### FHIR Connection Fails
- Verify base URL is correct
- Check authentication credentials
- Ensure FHIR server is accessible
- Review CORS settings
- Check network connectivity

### Save Not Working
- Check browser console for errors
- Verify you have write permissions
- Ensure all required fields are filled
- Check network connectivity

---

## 📚 Additional Resources

- [A2A Protocol Specification](https://github.com/anthropics/agent-protocol)
- [Google ADK Documentation](https://ai.google.dev/adk)
- [CQL Specification](https://cql.hl7.org/)
- [FHIR R4 Documentation](https://hl7.org/fhir/R4/)
- [SMART on FHIR](https://docs.smarthealthit.org/)

---

## 🤝 Support

For issues or questions:
- **GitHub Issues**: https://github.com/aks129/AgentInterOp/issues
- **Documentation**: Check docs/ folder
- **Examples**: See examples/ folder

---

## 📝 Changelog

### Version 2.0.0 (Current)
- ✨ Initial release of Agent Studio
- 🎨 Complete UI with 9 major sections
- 🤖 Agent management and customization
- 📜 Constitution explorer and editor
- 🔄 A2A protocol configuration
- ⚙️ ADK framework integration
- 📝 CQL/SQL query framework
- 🏥 FHIR MCP configuration
- 💼 Use cases library (6 scenarios)
- 📦 Application catalog

---

## 🎓 Tutorial

### Complete Workflow Example

**Scenario**: Create a Diabetes Monitoring Agent

**Step 1: Create Agent**
1. Navigate to Agent Studio (`/studio`)
2. Click "Create New Agent"
3. Fill in details:
   - Name: "Diabetes Monitoring Agent"
   - Description: "Monitors glucose levels and alerts for high-risk patients"
   - Purpose: "Automate diabetes monitoring and intervention"
   - Domain: "Chronic Care"
   - Role: "Administrator"
4. Click "Create Agent"

**Step 2: Define Constitution**
1. Go to "Constitutions" section
2. Select your new agent
3. Edit constitution:
   - Constraints: Add "Monitor glucose every 90 days", "Alert on HbA1c > 7%"
   - Ethics: Add "Protect patient privacy", "Ensure timely interventions"
   - Capabilities: Add "FHIR integration", "Alert generation", "Risk scoring"
4. Click "Save"

**Step 3: Configure FHIR**
1. Go to "FHIR MCP" section
2. Enter FHIR server URL
3. Select authentication type
4. Test connection
5. Enable MCP features

**Step 4: Write CQL Rules**
1. Go to "CQL/SQL Framework"
2. Write CQL for diabetes monitoring (see example above)
3. Validate query
4. Execute to test
5. Save to library

**Step 5: Test & Deploy**
1. Return to "Agents" section
2. Click "Configure" on your agent
3. Review all settings
4. Activate agent
5. Monitor dashboard for activity

---

## 🏆 Best Use Cases

Agent Studio excels at:

1. **Rapid Prototyping** - Quickly create and test healthcare agents
2. **Configuration Management** - Centralized agent configuration
3. **Query Development** - Interactive CQL/SQL editor
4. **FHIR Integration** - Easy FHIR server connectivity
5. **Use Case Implementation** - Template-based agent creation
6. **Team Collaboration** - Shared agent library
7. **Compliance** - Built-in A2A and FHIR compliance
8. **Monitoring** - Real-time agent status tracking

---

**Agent Studio** - Transforming healthcare agent development with an enterprise-grade platform. 🏥✨
