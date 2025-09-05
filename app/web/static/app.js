// Multi-Agent Demo JavaScript
console.log("Multi-Agent Demo initialized");

// Global state
let currentProtocol = 'A2A';
let conversationId = null;
let eventSource = null;
let artifacts = [];
let currentConfig = {};
let scenarios = {};

// DOM elements
const transcriptElement = document.getElementById('transcript');
const artifactsElement = document.getElementById('artifacts');
const startDemoBtn = document.getElementById('start-demo-btn');
const sendApplicantInfoBtn = document.getElementById('send-applicant-info-btn');
const resetBtn = document.getElementById('reset-btn');

// Settings panel elements
const scenarioSelect = document.getElementById('scenario-select');
const modeRadios = document.querySelectorAll('input[name="mode"]');
const adminProcessingMs = document.getElementById('admin-processing-ms');
const errorInjectionRate = document.getElementById('error-injection-rate');
const capacityLimit = document.getElementById('capacity-limit');
const protocolDefaultRadios = document.querySelectorAll('input[name="protocol-default"]');
const saveSettingsBtn = document.getElementById('save-settings-btn');
const resetConfigBtn = document.getElementById('reset-config-btn');
const examplesBtn = document.getElementById('examples-btn');
const requirementsText = document.getElementById('requirements-text');
const applicantPayload = document.getElementById('applicant-payload');
const payloadError = document.getElementById('payload-error');
const selftestStatus = document.getElementById('selftest-status');
const exportTranscriptBtn = document.getElementById('export-transcript-btn');

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    initializeInterface();
    loadConfig();
    loadScenarios();
    runSelftest();
    loadRequirements();
    
    // Event listeners
    startDemoBtn.addEventListener('click', startDemo);
    sendApplicantInfoBtn.addEventListener('click', sendApplicantInfo);
    resetBtn.addEventListener('click', resetDemo);
    
    // Settings panel listeners
    saveSettingsBtn.addEventListener('click', saveSettings);
    resetConfigBtn.addEventListener('click', resetConfig);
    examplesBtn.addEventListener('click', fillExamples);
    exportTranscriptBtn.addEventListener('click', exportTranscript);
    scenarioSelect.addEventListener('change', onScenarioChange);
    
    // Payload validation
    applicantPayload.addEventListener('input', validatePayload);
    
    // Protocol selection
    document.querySelectorAll('input[name="protocol"]').forEach(radio => {
        radio.addEventListener('change', function() {
            currentProtocol = this.value;
            console.log(`Protocol switched to: ${currentProtocol}`);
        });
    });
    
    // FHIR UI event listeners - with delay to ensure DOM is ready
    setTimeout(function() {
        const saveFhirBtn = document.getElementById('save-fhir-config-btn');
        const testCapabilitiesBtn = document.getElementById('test-capabilities-btn');
        const searchPatientBtn = document.getElementById('search-patient-btn');
        const patientSearchInput = document.getElementById('patient-search');
        
        console.log('FHIR: Looking for buttons...');
        console.log('Save button:', saveFhirBtn);
        console.log('Test button:', testCapabilitiesBtn);
        console.log('Search button:', searchPatientBtn);
        
        if (saveFhirBtn) {
            console.log('FHIR: Attaching save config listener');
            saveFhirBtn.addEventListener('click', function(e) {
                e.preventDefault();
                saveFhirConfig();
            });
        } else {
            console.log('FHIR: Save config button not found');
        }
        if (testCapabilitiesBtn) {
            console.log('FHIR: Attaching test capabilities listener');
            testCapabilitiesBtn.addEventListener('click', function(e) {
                e.preventDefault();
                testCapabilities();
            });
        } else {
            console.log('FHIR: Test capabilities button not found');
        }
        if (searchPatientBtn) {
            console.log('FHIR: Attaching search patient listener');
            searchPatientBtn.addEventListener('click', function(e) {
                e.preventDefault();
                searchPatient();
            });
        } else {
            console.log('FHIR: Search patient button not found');
        }
        if (patientSearchInput) {
            patientSearchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    searchPatient();
                }
            });
        }
        
        // FHIR Payload Integration event listeners
        const useFhirToggle = document.getElementById('use-ingested-fhir');
        const applicantPayload = document.getElementById('applicant-payload');
        const payloadError = document.getElementById('payload-error');
        
        if (useFhirToggle) {
            useFhirToggle.addEventListener('change', handleFhirToggleChange);
        }
        if (applicantPayload) {
            applicantPayload.addEventListener('input', validatePayload);
        }
        
        // Check for existing ingested data on load
        updateFhirToggleState();
        
        // Narrative to JSON event listeners
        const convertNarrativeBtn = document.getElementById('convert-narrative-btn');
        const applySchemaBtn = document.getElementById('apply-schema-btn');
        
        if (convertNarrativeBtn) {
            convertNarrativeBtn.addEventListener('click', convertNarrativeToJson);
        }
        if (applySchemaBtn) {
            applySchemaBtn.addEventListener('click', applyGeneratedSchema);
        }
    }, 100);
});

function initializeInterface() {
    console.log("Initializing interface");
    clearTranscript();
    clearArtifacts();
}

async function startDemo() {
    clearTranscript();
    clearArtifacts();
    
    addMessage('system', 'Starting BCS-E eligibility demo...');
    
    if (currentProtocol === 'A2A') {
        await startA2ADemo();
    } else {
        await startMCPDemo();
    }
}

async function startA2ADemo() {
    try {
        addMessage('system', 'Using A2A Protocol (JSON-RPC + SSE)');
        
        const response = await fetch('/api/bridge/demo/a2a', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                method: 'message/stream',
                parts: [{
                    kind: 'text',
                    text: 'Begin demo'
                }]
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Start SSE connection for real-time updates
        if (data.stream_url) {
            startSSEConnection(data.stream_url);
        }
        
        // Display initial response
        if (data.result) {
            addMessage('applicant', JSON.stringify(data.result, null, 2));
        }
        
        startDemoBtn.disabled = true;
        sendApplicantInfoBtn.disabled = false;
        
    } catch (error) {
        console.error('A2A demo error:', error);
        addMessage('error', `A2A error: ${error.message}`);
    }
}

async function startMCPDemo() {
    try {
        addMessage('system', 'Using MCP Protocol (Streamable HTTP)');
        
        // Begin chat thread
        const response = await fetch('/api/mcp/begin_chat_thread', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                scenario: 'bcse_eligibility',
                agent: 'applicant'
            })
        });
        
        const data = await response.json();
        conversationId = data.conversationId;
        
        addMessage('system', `MCP conversation started (ID: ${conversationId})`);
        
        // Send initial message
        await sendMCPMessage('Begin BCS-E eligibility demo');
        
        startDemoBtn.disabled = true;
        sendApplicantInfoBtn.disabled = false;
        
    } catch (error) {
        console.error('MCP demo error:', error);
        addMessage('error', `MCP error: ${error.message}`);
    }
}

function startSSEConnection(streamUrl) {
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource(streamUrl);
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            displaySSEMessage(data);
        } catch (error) {
            console.error('SSE message parsing error:', error);
            addMessage('system', event.data);
        }
    };
    
    eventSource.onerror = function(error) {
        console.error('SSE connection error:', error);
        addMessage('error', 'SSE connection error');
    };
}

function displaySSEMessage(data) {
    if (data.role && data.content) {
        addMessage(data.role, data.content);
    } else if (data.artifacts) {
        handleArtifacts(data.artifacts);
    } else {
        addMessage('system', JSON.stringify(data, null, 2));
    }
}

async function sendApplicantInfo() {
    addMessage('user', 'Sending applicant information...');
    
    if (currentProtocol === 'A2A') {
        await sendA2AApplicantInfo();
    } else {
        await sendMCPApplicantInfo();
    }
}

async function sendA2AApplicantInfo() {
    try {
        const response = await fetch('/api/bridge/demo/a2a', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                method: 'message/send',
                content: 'Process patient data for BCS-E eligibility'
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to send applicant info');
        }
        
        if (data.result) {
            addMessage('administrator', JSON.stringify(data.result, null, 2));
        }
        
        // Check for artifacts
        if (data.artifacts) {
            handleArtifacts(data.artifacts);
        }
        
    } catch (error) {
        console.error('A2A applicant info error:', error);
        addMessage('error', `A2A error: ${error.message}`);
    }
}

async function sendMCPApplicantInfo() {
    try {
        await sendMCPMessage('Process patient data for BCS-E eligibility');
        
    } catch (error) {
        console.error('MCP applicant info error:', error);
        addMessage('error', `MCP error: ${error.message}`);
    }
}

async function sendMCPMessage(message) {
    try {
        // Send message
        const sendResponse = await fetch('/api/mcp/send_message_to_chat_thread', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                conversationId: conversationId,
                message: message
            })
        });
        
        if (!sendResponse.ok) {
            throw new Error(`Failed to send MCP message: ${sendResponse.statusText}`);
        }
        
        // Poll for replies
        pollMCPReplies();
        
    } catch (error) {
        console.error('MCP send message error:', error);
        addMessage('error', `MCP send error: ${error.message}`);
    }
}

async function pollMCPReplies() {
    if (!conversationId) return;
    
    try {
        const response = await fetch('/api/mcp/check_replies', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                conversationId: conversationId,
                waitMs: 2000
            })
        });
        
        const data = await response.json();
        
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                addMessage(msg.role || 'agent', msg.content || msg.message);
            });
        }
        
        // Handle artifacts
        if (data.artifacts) {
            handleArtifacts(data.artifacts);
        }
        
        // Continue polling if status indicates more messages might come
        if (data.status === 'active' || data.status === 'pending') {
            setTimeout(() => pollMCPReplies(), 2000);
        }
        
    } catch (error) {
        console.error('MCP polling error:', error);
        addMessage('error', `MCP polling error: ${error.message}`);
    }
}

function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    const timestamp = new Date().toLocaleTimeString();
    
    // Create message header
    const messageHeader = document.createElement('div');
    messageHeader.className = 'message-header';
    
    // Create role badge
    const roleBadge = document.createElement('span');
    roleBadge.className = `role-badge role-${CSS.escape(role)}`;
    roleBadge.textContent = role.toUpperCase();
    
    // Create timestamp span
    const timestampSpan = document.createElement('span');
    timestampSpan.className = 'timestamp';
    timestampSpan.textContent = timestamp;
    
    // Create message content
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = content;
    
    // Assemble the message
    messageHeader.appendChild(roleBadge);
    messageHeader.appendChild(timestampSpan);
    messageDiv.appendChild(messageHeader);
    messageDiv.appendChild(messageContent);
    
    transcriptElement.appendChild(messageDiv);
    transcriptElement.scrollTop = transcriptElement.scrollHeight;
}

function handleArtifacts(artifactList) {
    artifacts = artifacts.concat(artifactList);
    displayArtifacts();
}

function displayArtifacts() {
    if (artifacts.length === 0) {
        artifactsElement.textContent = '';
        const noArtifactsP = document.createElement('p');
        noArtifactsP.className = 'no-artifacts';
        noArtifactsP.textContent = 'No artifacts available';
        artifactsElement.appendChild(noArtifactsP);
        return;
    }
    
    // Clear existing content
    artifactsElement.textContent = '';
    
    // Create heading
    const heading = document.createElement('h3');
    heading.textContent = 'Available Downloads:';
    artifactsElement.appendChild(heading);
    
    // Create list
    const list = document.createElement('ul');
    list.className = 'artifact-list';
    
    artifacts.forEach((artifact, index) => {
        const fileName = artifact.file?.name || `artifact-${index}.json`;
        const taskId = 'demo-task'; // Simple task ID for demo
        
        // Create list item
        const listItem = document.createElement('li');
        listItem.className = 'artifact-item';
        
        // Create download link
        const link = document.createElement('a');
        link.href = `/artifacts/${taskId}/${fileName}`;
        link.download = fileName;
        link.className = 'artifact-link';
        link.textContent = `📄 ${fileName}`;
        
        // Create type info
        const typeInfo = document.createElement('small');
        typeInfo.className = 'artifact-type';
        typeInfo.textContent = `(${artifact.file?.mimeType || 'application/json'})`;
        
        // Assemble list item
        listItem.appendChild(link);
        listItem.appendChild(typeInfo);
        list.appendChild(listItem);
    });
    
    artifactsElement.appendChild(list);
}

function resetDemo() {
    // Close SSE connection
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
    
    // Reset state
    conversationId = null;
    artifacts = [];
    
    // Reset UI
    clearTranscript();
    clearArtifacts();
    
    startDemoBtn.disabled = false;
    sendApplicantInfoBtn.disabled = true;
    
    addMessage('system', 'Demo reset');
}

function clearTranscript() {
    transcriptElement.textContent = '';
    const noMessagesP = document.createElement('p');
    noMessagesP.className = 'no-messages';
    noMessagesP.textContent = 'No messages yet. Click "Start Demo" to begin.';
    transcriptElement.appendChild(noMessagesP);
}

function clearArtifacts() {
    artifacts = [];
    artifactsElement.textContent = '';
    const noArtifactsP = document.createElement('p');
    noArtifactsP.className = 'no-artifacts';
    noArtifactsP.textContent = 'No artifacts available';
    artifactsElement.appendChild(noArtifactsP);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// New functions for connectathon features

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        currentConfig = await response.json();
        populateConfigControls();
    } catch (error) {
        console.error('Error loading config:', error);
    }
}

async function loadScenarios() {
    try {
        const response = await fetch('/api/scenarios');
        const data = await response.json();
        scenarios = data.scenarios;
        populateScenarioSelect(data.active);
    } catch (error) {
        console.error('Error loading scenarios:', error);
    }
}

async function runSelftest() {
    try {
        const response = await fetch('/api/selftest');
        const data = await response.json();
        updateSelftestBadge(data.ok);
    } catch (error) {
        updateSelftestBadge(false);
    }
}

async function loadRequirements() {
    try {
        const response = await fetch('/api/requirements');
        const data = await response.json();
        requirementsText.textContent = data.requirements;
    } catch (error) {
        requirementsText.textContent = 'Error loading requirements';
    }
}

function populateConfigControls() {
    // Set scenario
    scenarioSelect.value = currentConfig.scenario?.active || 'bcse';
    
    // Set mode
    const mode = currentConfig.mode?.role || 'full_stack';
    modeRadios.forEach(radio => {
        radio.checked = radio.value === mode;
    });
    
    // Set simulation
    adminProcessingMs.value = currentConfig.simulation?.admin_processing_ms || 1200;
    errorInjectionRate.value = currentConfig.simulation?.error_injection_rate || 0;
    capacityLimit.value = currentConfig.simulation?.capacity_limit || '';
    
    // Set protocol default
    const protocolDefault = currentConfig.protocol?.default_transport || 'a2a';
    protocolDefaultRadios.forEach(radio => {
        radio.checked = radio.value === protocolDefault;
    });
}

function populateScenarioSelect(activeScenario) {
    scenarioSelect.innerHTML = '';
    Object.entries(scenarios).forEach(([key, scenario]) => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = scenario.label;
        option.selected = key === activeScenario;
        scenarioSelect.appendChild(option);
    });
}

function updateSelftestBadge(success) {
    selftestStatus.className = `badge ${success ? 'bg-success' : 'bg-danger'}`;
    selftestStatus.textContent = success ? '✓ OK' : '✗ Failed';
}

async function saveSettings() {
    try {
        saveSettingsBtn.disabled = true;
        saveSettingsBtn.textContent = 'Saving...';
        
        // Get values
        const scenario = scenarioSelect.value;
        const mode = document.querySelector('input[name="mode"]:checked').value;
        const adminMs = parseInt(adminProcessingMs.value) || 1200;
        const errorRate = parseFloat(errorInjectionRate.value) || 0;
        const capacity = capacityLimit.value ? parseInt(capacityLimit.value) : null;
        const protocolDefault = document.querySelector('input[name="protocol-default"]:checked').value;
        
        // Save all settings
        await Promise.all([
            fetch('/api/scenarios/activate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: scenario})
            }),
            fetch('/api/mode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({role: mode})
            }),
            fetch('/api/simulation', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    admin_processing_ms: adminMs,
                    error_injection_rate: errorRate,
                    capacity_limit: capacity
                })
            }),
            fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    protocol: {default_transport: protocolDefault}
                })
            })
        ]);
        
        // Reload config and requirements
        await loadConfig();
        await loadRequirements();
        
        // Reload transcript if conversation is active
        if (conversationId) {
            addMessage('system', 'Settings saved. Configuration updated.');
        }
        
    } catch (error) {
        console.error('Error saving settings:', error);
        addMessage('system', `Error saving settings: ${error.message}`);
    } finally {
        saveSettingsBtn.disabled = false;
        saveSettingsBtn.textContent = 'Save Settings';
    }
}

async function resetConfig() {
    try {
        resetConfigBtn.disabled = true;
        resetConfigBtn.textContent = 'Resetting...';
        
        await fetch('/api/config/reset', {method: 'POST'});
        await fetch('/api/admin/reset', {method: 'POST'});
        
        await loadConfig();
        await loadRequirements();
        
        // Clear UI
        clearTranscript();
        clearArtifacts();
        conversationId = null;
        
        addMessage('system', 'Configuration and stores reset to defaults.');
    } catch (error) {
        console.error('Error resetting config:', error);
        addMessage('system', `Error resetting config: ${error.message}`);
    } finally {
        resetConfigBtn.disabled = false;
        resetConfigBtn.textContent = 'Reset Config';
    }
}

async function fillExamples() {
    try {
        const activeScenario = scenarioSelect.value;
        const scenario = scenarios[activeScenario];
        if (scenario && scenario.examples && scenario.examples.length > 0) {
            applicantPayload.value = JSON.stringify(scenario.examples[0], null, 2);
            validatePayload();
        }
    } catch (error) {
        console.error('Error filling examples:', error);
    }
}

function validatePayload() {
    const value = applicantPayload.value.trim();
    if (!value) {
        payloadError.style.display = 'none';
        return true;
    }
    
    try {
        JSON.parse(value);
        payloadError.style.display = 'none';
        return true;
    } catch (error) {
        payloadError.textContent = `Invalid JSON: ${error.message}`;
        payloadError.style.display = 'block';
        return false;
    }
}

async function onScenarioChange() {
    await loadRequirements();
}

async function exportTranscript() {
    if (!conversationId) {
        addMessage('system', 'No active conversation to export');
        return;
    }
    
    try {
        exportTranscriptBtn.disabled = true;
        exportTranscriptBtn.textContent = 'Exporting...';
        
        const [transcriptResponse, artifactsResponse] = await Promise.all([
            fetch(`/api/admin/transcript/${conversationId}`),
            fetch(`/api/admin/artifacts/${conversationId}`)
        ]);
        
        const transcript = await transcriptResponse.json();
        const artifactsList = await artifactsResponse.json();
        
        // Download transcript
        downloadJson(transcript, `transcript_${conversationId}.json`);
        
        // Show artifact info
        addMessage('system', `Transcript exported. Available artifacts: ${artifactsList.artifacts.map(a => a.name).join(', ')}`);
        
    } catch (error) {
        console.error('Error exporting:', error);
        addMessage('system', `Error exporting: ${error.message}`);
    } finally {
        exportTranscriptBtn.disabled = false;
        exportTranscriptBtn.textContent = 'Export Transcript & Artifacts';
    }
}

function downloadJson(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// FHIR Connection Functionality
let currentPatientData = null;

function saveFhirConfig() {
    console.log('FHIR Config: Save button clicked');
    const baseUrl = document.getElementById('fhir-base-url').value;
    const token = document.getElementById('fhir-token').value;
    const statusDiv = document.getElementById('fhir-status');
    
    console.log('FHIR Config: Base URL =', baseUrl);
    
    if (!baseUrl) {
        showFhirStatus('Please enter a FHIR base URL', 'danger');
        return;
    }
    
    const config = { base: baseUrl };
    if (token) config.token = token;
    
    fetch('/api/fhir/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            showFhirStatus('FHIR configuration saved successfully', 'success');
        } else {
            showFhirStatus('Error: ' + data.error, 'danger');
        }
    })
    .catch(error => showFhirStatus('Network error: ' + error.message, 'danger'));
}

function testCapabilities() {
    console.log('FHIR Config: Test capabilities button clicked');
    const capabilitiesDiv = document.getElementById('capabilities-display');
    showFhirStatus('Testing FHIR server capabilities...', 'info');
    
    fetch('/api/fhir/capabilities')
    .then(response => response.json())
    .then(data => {
        if (data.fhirVersion) {
            const mode = data.rest && data.rest[0] ? data.rest[0].mode : 'unknown';
            capabilitiesDiv.innerHTML = `✅ FHIR ${data.fhirVersion} (${mode} mode)`;
            capabilitiesDiv.classList.remove('d-none');
            showFhirStatus('FHIR server capabilities verified', 'success');
        } else if (data.ok === false) {
            showFhirStatus('Error: ' + data.error, 'danger');
        } else {
            showFhirStatus('Capabilities received but version unclear', 'warning');
        }
    })
    .catch(error => showFhirStatus('Error testing capabilities: ' + error.message, 'danger'));
}

function searchPatient() {
    console.log('FHIR Config: Search patient button clicked');
    const searchTerm = document.getElementById('patient-search').value;
    const resultsDiv = document.getElementById('patient-results');
    console.log('FHIR Config: Search term =', searchTerm);
    
    if (!searchTerm) {
        showFhirStatus('Please enter a name or identifier to search', 'warning');
        return;
    }
    
    showFhirStatus('Searching for patients...', 'info');
    
    // Determine if search term looks like an identifier or name
    const isIdentifier = /^[a-zA-Z0-9_-]+$/.test(searchTerm) && !/ /.test(searchTerm);
    const searchParam = isIdentifier ? `identifier=${searchTerm}` : `name=${searchTerm}`;
    
    fetch(`/api/fhir/patients?${searchParam}`)
    .then(response => response.json())
    .then(data => {
        if (data.ok === false) {
            showFhirStatus('Error: ' + data.error, 'danger');
            return;
        }
        
        if (data.entry && data.entry.length > 0) {
            displayPatientResults(data.entry);
            showFhirStatus(`Found ${data.entry.length} patient(s)`, 'success');
        } else {
            resultsDiv.innerHTML = '<small class="text-muted">No patients found</small>';
            showFhirStatus('No patients found', 'warning');
        }
    })
    .catch(error => showFhirStatus('Error searching patients: ' + error.message, 'danger'));
}

function displayPatientResults(patients) {
    const resultsDiv = document.getElementById('patient-results');
    
    let html = '<div class="table-responsive"><table class="table table-sm"><thead><tr>';
    html += '<th>ID</th><th>Display</th><th>Action</th></tr></thead><tbody>';
    
    patients.forEach(entry => {
        const patient = entry.resource;
        const id = patient.id;
        const name = patient.name && patient.name[0] ? 
            `${patient.name[0].given ? patient.name[0].given.join(' ') : ''} ${patient.name[0].family || ''}`.trim() :
            'No name';
        const birthDate = patient.birthDate || 'Unknown';
        const display = `${name} (${birthDate})`;
        
        html += `<tr>
            <td><code>${id}</code></td>
            <td>${display}</td>
            <td>
                <button class="btn btn-outline-primary btn-xs" onclick="ingestPatientData('${id}')">
                    <i data-feather="download" width="14" height="14"></i> Ingest $everything
                </button>
            </td>
        </tr>`;
    });
    
    html += '</tbody></table></div>';
    resultsDiv.innerHTML = html;
    feather.replace(); // Re-initialize feather icons
}

function ingestPatientData(patientId) {
    showFhirStatus(`Ingesting patient data for ${patientId}...`, 'info');
    
    fetch(`/api/fhir/patient/${patientId}/everything`)
    .then(response => response.json())
    .then(data => {
        if (data.ok === false) {
            showFhirStatus('Error: ' + data.error, 'danger');
            return;
        }
        
        // Store patient data in client variable
        currentPatientData = data;
        
        // Also send to ingest endpoint
        return fetch('/api/ingest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ patientData: data, patientId: patientId })
        });
    })
    .then(response => response.json())
    .then(ingestResult => {
        if (ingestResult && ingestResult.ok !== false) {
            showFhirStatus(`✅ Patient ${patientId} data ingested successfully`, 'success');
        } else {
            showFhirStatus(`Patient data retrieved but ingest failed: ${ingestResult ? ingestResult.error : 'Unknown error'}`, 'warning');
        }
    })
    .catch(error => showFhirStatus('Error ingesting patient data: ' + error.message, 'danger'));
}

function showFhirStatus(message, type) {
    const statusDiv = document.getElementById('fhir-status');
    statusDiv.className = `alert alert-${type}`;
    statusDiv.textContent = message;
    statusDiv.classList.remove('d-none');
    
    // Auto-hide success/info messages after 5 seconds
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            statusDiv.classList.add('d-none');
        }, 5000);
    }
}

// FHIR Payload Integration Functions
let ingestedFhirData = null;

function handleFhirToggleChange() {
    const useFhirToggle = document.getElementById('use-ingested-fhir');
    const applicantPayload = document.getElementById('applicant-payload');
    
    if (useFhirToggle.checked && ingestedFhirData) {
        // Populate textarea with ingested payload
        applicantPayload.value = JSON.stringify(ingestedFhirData.applicant_payload, null, 2);
        applicantPayload.placeholder = 'Ingested FHIR data (editable)';
        showFhirSourceChip(ingestedFhirData);
    } else {
        // Clear or reset to default
        applicantPayload.value = '';
        applicantPayload.placeholder = '{"age": 56, "sex": "female", "birthDate": "1968-01-15"}';
        hideFhirSourceChip();
    }
    validatePayload();
}

function showFhirSourceChip(data) {
    const chip = document.getElementById('fhir-source-chip');
    const text = document.getElementById('fhir-source-text');
    
    if (chip && text && data.ingested_at) {
        const timestamp = new Date(data.ingested_at).toLocaleString();
        text.textContent = `Source: FHIR $everything @ ${timestamp}`;
        chip.classList.remove('d-none');
        
        // Re-initialize feather icons for the chip
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
}

function hideFhirSourceChip() {
    const chip = document.getElementById('fhir-source-chip');
    if (chip) {
        chip.classList.add('d-none');
    }
}

function updateFhirToggleState() {
    // Check if there's any ingested FHIR data available
    fetch('/api/ingested/latest')
    .then(response => response.json())
    .then(data => {
        if (data.ok && data.data) {
            ingestedFhirData = data.data;
            const useFhirToggle = document.getElementById('use-ingested-fhir');
            if (useFhirToggle) {
                useFhirToggle.disabled = false;
                // Show source chip if toggle is already checked
                if (useFhirToggle.checked) {
                    showFhirSourceChip(ingestedFhirData);
                }
            }
        } else {
            // No ingested data available
            const useFhirToggle = document.getElementById('use-ingested-fhir');
            if (useFhirToggle) {
                useFhirToggle.disabled = true;
                useFhirToggle.checked = false;
                hideFhirSourceChip();
            }
        }
    })
    .catch(error => {
        console.log('No ingested FHIR data available');
        const useFhirToggle = document.getElementById('use-ingested-fhir');
        if (useFhirToggle) {
            useFhirToggle.disabled = true;
            useFhirToggle.checked = false;
            hideFhirSourceChip();
        }
    });
}

function validatePayload() {
    const applicantPayload = document.getElementById('applicant-payload');
    const payloadError = document.getElementById('payload-error');
    
    if (!applicantPayload || !payloadError) return true;
    
    const value = applicantPayload.value.trim();
    if (!value) {
        payloadError.style.display = 'none';
        return true;
    }
    
    try {
        JSON.parse(value);
        payloadError.style.display = 'none';
        return true;
    } catch (error) {
        payloadError.textContent = `Invalid JSON: ${error.message}`;
        payloadError.style.display = 'block';
        return false;
    }
}

// Update ingest patient function to refresh toggle state
function ingestPatientData(patientId) {
    showFhirStatus(`Ingesting patient data for ${patientId}...`, 'info');
    
    fetch(`/api/fhir/patient/${patientId}/everything`)
    .then(response => response.json())
    .then(data => {
        if (data.ok === false) {
            showFhirStatus('Error: ' + data.error, 'danger');
            return;
        }
        
        // Store patient data in client variable
        currentPatientData = data;
        
        // Also send to ingest endpoint
        return fetch('/api/ingest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ patientData: data, patientId: patientId })
        });
    })
    .then(response => response.json())
    .then(ingestResult => {
        if (ingestResult && ingestResult.ok !== false) {
            showFhirStatus(`✅ Patient ${patientId} data ingested successfully`, 'success');
            // Store the ingested data for the toggle
            ingestedFhirData = ingestResult;
            // Update toggle state
            updateFhirToggleState();
        } else {
            showFhirStatus(`Patient data retrieved but ingest failed: ${ingestResult ? ingestResult.error : 'Unknown error'}`, 'warning');
        }
    })
    .catch(error => showFhirStatus('Error ingesting patient data: ' + error.message, 'danger'));
}

// Narrative to JSON Functions
let generatedSchema = null;

function convertNarrativeToJson() {
    const narrativeText = document.getElementById('narrative-text').value.trim();
    const convertBtn = document.getElementById('convert-narrative-btn');
    const generatedJsonTextarea = document.getElementById('generated-json');
    const applyBtn = document.getElementById('apply-schema-btn');
    
    if (!narrativeText) {
        showNarrativeStatus('Please enter a scenario narrative to convert', 'warning');
        return;
    }
    
    // Disable button and show loading
    convertBtn.disabled = true;
    convertBtn.innerHTML = '<i data-feather="loader" class="me-2 spinning"></i> Converting...';
    showNarrativeStatus('Converting narrative with Claude...', 'info');
    
    fetch('/api/scenarios/narrative', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: narrativeText })
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            generatedSchema = data.generated_schema;
            generatedJsonTextarea.value = JSON.stringify(generatedSchema, null, 2);
            applyBtn.disabled = false;
            showNarrativeStatus('✅ Narrative converted successfully! Review the schema and apply to scenario.', 'success');
        } else {
            if (data.requires_key) {
                showNarrativeStatus('⚠️ ' + data.error + '. Please set the ANTHROPIC_API_KEY environment variable.', 'danger');
            } else {
                showNarrativeStatus('Error: ' + data.error, 'danger');
            }
            generatedJsonTextarea.value = '';
            applyBtn.disabled = true;
            generatedSchema = null;
        }
    })
    .catch(error => {
        showNarrativeStatus('Network error: ' + error.message, 'danger');
        generatedJsonTextarea.value = '';
        applyBtn.disabled = true;
        generatedSchema = null;
    })
    .finally(() => {
        // Re-enable button and reset text
        convertBtn.disabled = false;
        convertBtn.innerHTML = '<i data-feather="cpu" class="me-2"></i> Convert with Claude';
        
        // Re-initialize feather icons
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    });
}

function applyGeneratedSchema() {
    if (!generatedSchema) {
        showNarrativeStatus('No schema to apply', 'warning');
        return;
    }
    
    const applyBtn = document.getElementById('apply-schema-btn');
    applyBtn.disabled = true;
    applyBtn.innerHTML = '<i data-feather="loader" class="me-2 spinning"></i> Applying...';
    showNarrativeStatus('Applying schema to active scenario...', 'info');
    
    fetch('/api/scenarios/options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(generatedSchema)
    })
    .then(response => response.json())
    .then(data => {
        if (data.ok) {
            showNarrativeStatus('✅ Schema applied to active scenario successfully!', 'success');
        } else {
            showNarrativeStatus('Error applying schema: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        showNarrativeStatus('Network error: ' + error.message, 'danger');
    })
    .finally(() => {
        // Re-enable button and reset text
        applyBtn.disabled = false;
        applyBtn.innerHTML = '<i data-feather="check" class="me-2"></i> Apply to Active Scenario';
        
        // Re-initialize feather icons
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    });
}

function showNarrativeStatus(message, type) {
    const statusDiv = document.getElementById('narrative-status');
    if (statusDiv) {
        statusDiv.className = `alert alert-${type}`;
        statusDiv.textContent = message;
        statusDiv.classList.remove('d-none');
        
        // Auto-hide success/info messages after 5 seconds
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                statusDiv.classList.add('d-none');
            }, 5000);
        }
    }
}