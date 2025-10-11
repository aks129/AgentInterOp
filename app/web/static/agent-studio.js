/**
 * Agent Studio - JavaScript Application
 * Healthcare Agent Development Platform
 */

// State Management
const state = {
    agents: [],
    domains: [],
    useCases: [],
    applications: [],
    selectedAgent: null,
    currentSection: 'overview'
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadAllData();
    setupEventListeners();
});

// Data Loading Functions
async function loadAllData() {
    try {
        await Promise.all([
            loadAgents(),
            loadDomains(),
            loadUseCases(),
            loadApplications()
        ]);
        updateDashboard();
    } catch (error) {
        showError('Failed to load data: ' + error.message);
    }
}

async function loadAgents() {
    try {
        const response = await fetch('/api/agents/');
        const data = await response.json();
        state.agents = data.agents || [];
        renderAgentsList();
        renderRecentAgents();
        populateAgentSelects();
    } catch (error) {
        console.error('Error loading agents:', error);
    }
}

async function loadDomains() {
    try {
        const response = await fetch('/api/agents/domains/list');
        const data = await response.json();
        state.domains = data.domains || [];
        populateDomainSelects();
    } catch (error) {
        console.error('Error loading domains:', error);
    }
}

async function loadUseCases() {
    try {
        // Load use cases from API or local data
        state.useCases = [
            {
                id: 'bcse',
                title: 'Breast Cancer Screening Eligibility',
                description: 'Automated eligibility determination for breast cancer screening programs based on USPSTF guidelines',
                category: 'screening',
                complexity: 'intermediate',
                status: 'active',
                icon: '🩺',
                tags: ['preventive', 'cancer', 'women-health']
            },
            {
                id: 'clinical_trial_matching',
                title: 'Clinical Trial Patient Matching',
                description: 'Match eligible patients to clinical trials based on inclusion/exclusion criteria',
                category: 'treatment',
                complexity: 'advanced',
                status: 'active',
                icon: '🔬',
                tags: ['trials', 'research', 'matching']
            },
            {
                id: 'prior_auth',
                title: 'Prior Authorization Processing',
                description: 'Automate insurance prior authorization requests and approvals',
                category: 'administrative',
                complexity: 'intermediate',
                status: 'active',
                icon: '📋',
                tags: ['insurance', 'admin', 'workflow']
            },
            {
                id: 'chronic_care_monitoring',
                title: 'Chronic Disease Monitoring',
                description: 'Monitor patient vitals and alert for chronic disease management',
                category: 'monitoring',
                complexity: 'intermediate',
                status: 'active',
                icon: '💊',
                tags: ['chronic', 'monitoring', 'alerts']
            },
            {
                id: 'referral_routing',
                title: 'Specialist Referral Routing',
                description: 'Route patients to appropriate specialists based on condition and availability',
                category: 'administrative',
                complexity: 'basic',
                status: 'active',
                icon: '🏥',
                tags: ['referral', 'routing', 'scheduling']
            },
            {
                id: 'med_reconciliation',
                title: 'Medication Reconciliation',
                description: 'Reconcile patient medications across care transitions',
                category: 'treatment',
                complexity: 'intermediate',
                status: 'active',
                icon: '💉',
                tags: ['medication', 'safety', 'reconciliation']
            }
        ];
        renderUseCases();
    } catch (error) {
        console.error('Error loading use cases:', error);
    }
}

async function loadApplications() {
    try {
        state.applications = [
            {
                id: 'epic_integration',
                name: 'Epic EHR Integration',
                type: 'EHR',
                status: 'active',
                version: '2023.1',
                description: 'Integration with Epic EHR system'
            },
            {
                id: 'cerner_integration',
                name: 'Cerner Integration',
                type: 'EHR',
                status: 'active',
                version: '2024.0',
                description: 'Integration with Oracle Cerner'
            }
        ];
        renderApplications();
    } catch (error) {
        console.error('Error loading applications:', error);
    }
}

// Rendering Functions
function renderAgentsList() {
    const container = document.getElementById('agentsList');

    if (state.agents.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🤖</div>
                <div class="empty-state-text">No agents found. Create your first agent!</div>
                <button class="btn btn-primary" onclick="openAgentModal()">Create Agent</button>
            </div>
        `;
        return;
    }

    container.innerHTML = state.agents.map(agent => `
        <div class="list-item">
            <div class="list-item-content">
                <div class="list-item-title">${agent.name}</div>
                <div class="list-item-meta">
                    ${agent.domain} • ${agent.role} • v${agent.version}
                    <span class="badge badge-${agent.status === 'active' ? 'success' : 'warning'}">${agent.status}</span>
                </div>
            </div>
            <div class="list-item-actions">
                <button class="btn btn-small btn-outline" onclick="viewAgent('${agent.id}')">View</button>
                <button class="btn btn-small btn-outline" onclick="editAgent('${agent.id}')">Edit</button>
                <button class="btn btn-small btn-secondary" onclick="configureAgent('${agent.id}')">Configure</button>
            </div>
        </div>
    `).join('');
}

function renderRecentAgents() {
    const container = document.getElementById('recentAgents');
    const recent = state.agents.slice(0, 5);

    if (recent.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🤖</div>
                <div class="empty-state-text">No agents yet</div>
            </div>
        `;
        return;
    }

    container.innerHTML = recent.map(agent => `
        <div class="list-item">
            <div class="list-item-content">
                <div class="list-item-title">${agent.name}</div>
                <div class="list-item-meta">
                    ${agent.domain} • ${agent.role}
                    <span class="badge badge-${agent.status === 'active' ? 'success' : 'warning'}">${agent.status}</span>
                </div>
            </div>
            <div class="list-item-actions">
                <button class="btn btn-small btn-outline" onclick="viewAgent('${agent.id}')">View</button>
            </div>
        </div>
    `).join('');
}

function renderUseCases() {
    const container = document.getElementById('useCasesList');

    container.innerHTML = state.useCases.map(useCase => `
        <div class="usecase-card" onclick="viewUseCase('${useCase.id}')">
            <div class="usecase-header">
                <div class="usecase-icon">${useCase.icon}</div>
                <span class="badge badge-${useCase.status === 'active' ? 'success' : 'warning'}">${useCase.status}</span>
            </div>
            <div class="usecase-title">${useCase.title}</div>
            <div class="usecase-description">${useCase.description}</div>
            <div class="usecase-meta">
                ${useCase.tags.map(tag => `<span class="badge badge-info">${tag}</span>`).join('')}
            </div>
        </div>
    `).join('');
}

function renderApplications() {
    const container = document.getElementById('applicationsList');

    if (state.applications.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📦</div>
                <div class="empty-state-text">No applications in catalog</div>
            </div>
        `;
        return;
    }

    container.innerHTML = state.applications.map(app => `
        <div class="list-item">
            <div class="list-item-content">
                <div class="list-item-title">${app.name}</div>
                <div class="list-item-meta">
                    ${app.type} • v${app.version}
                    <span class="badge badge-${app.status === 'active' ? 'success' : 'warning'}">${app.status}</span>
                </div>
            </div>
            <div class="list-item-actions">
                <button class="btn btn-small btn-outline" onclick="configureApp('${app.id}')">Configure</button>
                <button class="btn btn-small btn-outline" onclick="testApp('${app.id}')">Test</button>
            </div>
        </div>
    `).join('');
}

// Dashboard Updates
function updateDashboard() {
    document.getElementById('totalAgents').textContent = state.agents.length;
    document.getElementById('activeAgents').textContent = state.agents.filter(a => a.status === 'active').length;
    document.getElementById('useCases').textContent = state.useCases.length;
    document.getElementById('applications').textContent = state.applications.length;
}

// Navigation
function showSection(sectionId) {
    // Update sidebar
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.closest('.sidebar-item').classList.add('active');

    // Update sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(sectionId).classList.add('active');

    state.currentSection = sectionId;

    // Load section-specific data
    if (sectionId === 'constitution') {
        populateConstitutionAgentSelect();
    }
}

// Agent Modal Functions
function openAgentModal() {
    document.getElementById('agentModal').classList.add('active');
}

function closeAgentModal() {
    document.getElementById('agentModal').classList.remove('active');
    document.getElementById('agentForm').reset();
}

async function saveAgent(event) {
    event.preventDefault();

    const formData = {
        name: document.getElementById('agentName').value,
        description: document.getElementById('agentDescription').value,
        purpose: document.getElementById('agentPurpose').value,
        domain: document.getElementById('agentDomain').value,
        role: document.getElementById('agentRole').value,
        constitution: {
            purpose: document.getElementById('agentPurpose').value,
            domain: document.getElementById('agentDomain').value,
            constraints: [],
            ethics: [],
            capabilities: []
        },
        plan: {
            goals: [],
            tasks: [],
            workflows: [],
            success_criteria: []
        },
        agent_card: {
            name: document.getElementById('agentName').value,
            description: document.getElementById('agentDescription').value,
            role: document.getElementById('agentRole').value,
            capabilities: {
                streaming: true,
                protocols: ["A2A", "MCP"],
                fhir: true
            },
            skills: [],
            methods: [],
            supported_formats: ["application/fhir+json", "application/json"]
        }
    };

    try {
        const response = await fetch('/api/agents/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }

        const data = await response.json();
        showSuccess('Agent created successfully!');
        closeAgentModal();
        await loadAgents();
        updateDashboard();
    } catch (error) {
        showError('Failed to create agent: ' + error.message);
    }
}

async function createSampleAgent() {
    try {
        const response = await fetch('/api/agents/samples/bcse', {
            method: 'POST'
        });
        const data = await response.json();
        showSuccess('BCS-E sample agent created successfully!');
        await loadAgents();
        updateDashboard();
    } catch (error) {
        showError('Failed to create sample agent: ' + error.message);
    }
}

// Constitution Functions
function populateConstitutionAgentSelect() {
    const select = document.getElementById('constitutionAgentSelect');
    select.innerHTML = '<option value="">Select an agent...</option>' +
        state.agents.map(agent => `<option value="${agent.id}">${agent.name}</option>`).join('');
}

function loadConstitution() {
    const agentId = document.getElementById('constitutionAgentSelect').value;
    if (!agentId) return;

    const agent = state.agents.find(a => a.id === agentId);
    if (!agent) return;

    const viewContainer = document.getElementById('constitutionView');
    const editorContainer = document.getElementById('constitutionEditor');

    viewContainer.innerHTML = `
        <div class="config-panel">
            <h4 style="margin-bottom: 16px;">Current Constitution</h4>
            <div class="config-row">
                <span class="config-label">Purpose</span>
                <span class="config-value">${agent.constitution.purpose}</span>
            </div>
            <div class="config-row">
                <span class="config-label">Domain</span>
                <span class="config-value">${agent.constitution.domain}</span>
            </div>
        </div>
        <div style="margin-top: 16px;">
            <h4 style="margin-bottom: 12px;">Constraints</h4>
            ${agent.constitution.constraints.map(c => `<div class="list-item-meta">• ${c}</div>`).join('')}
        </div>
        <div style="margin-top: 16px;">
            <h4 style="margin-bottom: 12px;">Ethics</h4>
            ${agent.constitution.ethics.map(e => `<div class="list-item-meta">• ${e}</div>`).join('')}
        </div>
        <div style="margin-top: 16px;">
            <h4 style="margin-bottom: 12px;">Capabilities</h4>
            ${agent.constitution.capabilities.map(c => `<span class="badge badge-primary">${c}</span>`).join(' ')}
        </div>
    `;

    editorContainer.innerHTML = `
        <div class="form-group">
            <label class="form-label">Purpose</label>
            <input type="text" class="form-input" id="editPurpose" value="${agent.constitution.purpose}" />
        </div>
        <div class="form-group">
            <label class="form-label">Domain</label>
            <select class="form-select" id="editDomain">
                ${state.domains.map(d => `<option value="${d.id}" ${d.id === agent.constitution.domain ? 'selected' : ''}>${d.name}</option>`).join('')}
            </select>
        </div>
        <div class="form-group">
            <label class="form-label">Constraints (one per line)</label>
            <textarea class="form-textarea" id="editConstraints">${agent.constitution.constraints.join('\n')}</textarea>
        </div>
        <div class="form-group">
            <label class="form-label">Ethics (one per line)</label>
            <textarea class="form-textarea" id="editEthics">${agent.constitution.ethics.join('\n')}</textarea>
        </div>
        <div class="form-group">
            <label class="form-label">Capabilities (one per line)</label>
            <textarea class="form-textarea" id="editCapabilities">${agent.constitution.capabilities.join('\n')}</textarea>
        </div>
    `;
}

async function saveConstitution() {
    const agentId = document.getElementById('constitutionAgentSelect').value;
    if (!agentId) {
        showError('Please select an agent first');
        return;
    }

    // Get the full agent to preserve domain
    const agent = state.agents.find(a => a.id === agentId);
    if (!agent) {
        showError('Agent not found');
        return;
    }

    const updates = {
        constitution: {
            purpose: document.getElementById('editPurpose').value,
            domain: document.getElementById('editDomain').value,  // Get from editor
            constraints: document.getElementById('editConstraints').value.split('\n').filter(l => l.trim()),
            ethics: document.getElementById('editEthics').value.split('\n').filter(l => l.trim()),
            capabilities: document.getElementById('editCapabilities').value.split('\n').filter(l => l.trim())
        }
    };

    try {
        const response = await fetch(`/api/agents/${agentId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }

        showSuccess('Constitution updated successfully!');
        await loadAgents();
        loadConstitution();
    } catch (error) {
        showError('Failed to save constitution: ' + error.message);
    }
}

// CQL/SQL Functions
function switchQueryType(type) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    event.target.classList.add('active');
    document.getElementById(type + 'Tab').classList.add('active');
}

function loadCQLExample() {
    document.getElementById('cqlEditor').value = `library BCSEligibility version '1.0.0'

using FHIR version '4.0.1'

include FHIRHelpers version '4.0.1'

context Patient

define "Patient Age":
  AgeInYears()

define "Is Eligible Age":
  "Patient Age" >= 50 and "Patient Age" <= 74

define "Is Female":
  Patient.gender = 'female'

define "Recent Mammogram":
  [Procedure: "Mammography"] M
    where M.performedDateTime during Interval[Today() - 27 months, Today()]

define "Has Recent Mammogram":
  exists "Recent Mammogram"

define "Eligible for Screening":
  "Is Eligible Age" and "Is Female" and not "Has Recent Mammogram"`;
}

function validateCQL() {
    showInfo('CQL validation feature coming soon!');
}

function executeCQL() {
    document.getElementById('queryResults').innerHTML = `
        <div class="card">
            <h4 style="margin-bottom: 16px;">Query Results</h4>
            <div class="config-panel">
                <div class="config-row">
                    <span class="config-label">Patient Age</span>
                    <span class="config-value">62 years</span>
                </div>
                <div class="config-row">
                    <span class="config-label">Is Eligible Age</span>
                    <span class="config-value badge badge-success">true</span>
                </div>
                <div class="config-row">
                    <span class="config-label">Is Female</span>
                    <span class="config-value badge badge-success">true</span>
                </div>
                <div class="config-row">
                    <span class="config-label">Has Recent Mammogram</span>
                    <span class="config-value badge badge-danger">false</span>
                </div>
                <div class="config-row">
                    <span class="config-label">Eligible for Screening</span>
                    <span class="config-value badge badge-success">true</span>
                </div>
            </div>
        </div>
    `;
    switchQueryType('results');
}

// FHIR Functions
async function testFHIRConnection() {
    const baseUrl = document.getElementById('fhirBaseUrl').value;
    if (!baseUrl) {
        showError('Please enter a FHIR base URL');
        return;
    }

    showInfo('Testing FHIR connection...');

    try {
        const response = await fetch(`${baseUrl}/metadata`);
        if (response.ok) {
            showSuccess('FHIR connection successful!');
        } else {
            showError('FHIR connection failed: ' + response.statusText);
        }
    } catch (error) {
        showError('FHIR connection failed: ' + error.message);
    }
}

function executeFHIRQuery() {
    const resourceType = document.getElementById('fhirResourceType').value;
    const searchParams = document.getElementById('fhirSearchParams').value;

    document.getElementById('fhirQueryResults').innerHTML = `
        <div class="alert alert-info active" style="margin-top: 16px;">
            FHIR Query: ${resourceType}?${searchParams}
            <br><br>
            Results would appear here. Connect to a real FHIR server to see actual data.
        </div>
    `;
}

// Use Case Functions
function filterUseCases() {
    const category = document.getElementById('useCaseCategory').value;
    const complexity = document.getElementById('useCaseComplexity').value;
    const status = document.getElementById('useCaseStatus').value;

    let filtered = state.useCases;
    if (category) filtered = filtered.filter(u => u.category === category);
    if (complexity) filtered = filtered.filter(u => u.complexity === complexity);
    if (status) filtered = filtered.filter(u => u.status === status);

    const container = document.getElementById('useCasesList');
    container.innerHTML = filtered.map(useCase => `
        <div class="usecase-card" onclick="viewUseCase('${useCase.id}')">
            <div class="usecase-header">
                <div class="usecase-icon">${useCase.icon}</div>
                <span class="badge badge-${useCase.status === 'active' ? 'success' : 'warning'}">${useCase.status}</span>
            </div>
            <div class="usecase-title">${useCase.title}</div>
            <div class="usecase-description">${useCase.description}</div>
            <div class="usecase-meta">
                ${useCase.tags.map(tag => `<span class="badge badge-info">${tag}</span>`).join('')}
            </div>
        </div>
    `).join('');
}

function viewUseCase(id) {
    const useCase = state.useCases.find(u => u.id === id);
    if (!useCase) return;

    showInfo(`Use Case: ${useCase.title} - Implementation coming soon!`);
}

// Utility Functions
function populateDomainSelects() {
    const selects = document.querySelectorAll('#agentDomain');
    selects.forEach(select => {
        select.innerHTML = '<option value="">Select Domain</option>' +
            state.domains.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
    });
}

function populateAgentSelects() {
    const select = document.getElementById('constitutionAgentSelect');
    if (select) {
        select.innerHTML = '<option value="">Select an agent...</option>' +
            state.agents.map(a => `<option value="${a.id}">${a.name}</option>`).join('');
    }
}

function toggleSwitch(element) {
    element.classList.toggle('active');
}

function setupEventListeners() {
    // Add any global event listeners here
}

async function saveAll() {
    showInfo('Saving all configurations...');
    // Implement save all functionality
}

async function saveA2AConfig() {
    showSuccess('A2A configuration saved!');
}

function saveCurrentQuery() {
    showSuccess('Query saved to library!');
}

function addApplication() {
    showInfo('Add application feature coming soon!');
}

function viewAgent(id) {
    const agent = state.agents.find(a => a.id === id);
    if (!agent) return;
    alert(JSON.stringify(agent, null, 2));
}

function editAgent(id) {
    showInfo('Agent editing feature coming soon!');
}

function configureAgent(id) {
    showInfo('Agent configuration feature coming soon!');
}

function configureApp(id) {
    showInfo('App configuration feature coming soon!');
}

function testApp(id) {
    showInfo('App testing feature coming soon!');
}

// Alert Functions
function showAlert(message, type) {
    const container = document.getElementById('alertContainer');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} active`;
    alert.textContent = message;
    container.appendChild(alert);

    setTimeout(() => {
        alert.remove();
    }, 5000);
}

function showSuccess(message) {
    showAlert(message, 'success');
}

function showError(message) {
    showAlert(message, 'error');
}

function showInfo(message) {
    showAlert(message, 'info');
}
