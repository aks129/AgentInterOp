// Experimental UI Controller for Connectathon Settings & Agent UX
// Non-breaking controller that extends the main app functionality
console.log("Experimental UI Controller initialized");

// Claude Agent UX functionality
class ClaudeAgentUX {
    constructor() {
        this.claudeStatus = { ready: false, latency: null };
        this.conversationTrace = [];
        this.isExperimentalEnabled = false;
        this.lastGeneratedResponse = null;
    }

    async init() {
        this.setupClaudeEventListeners();
        this.checkURLParams();
        await this.checkClaudeStatus();
    }

    setupClaudeEventListeners() {
        // Experimental Agent UX toggle
        const experimentalToggle = document.getElementById('experimental-agent-ux');
        if (experimentalToggle) {
            experimentalToggle.addEventListener('change', (e) => {
                this.toggleExperimentalUI(e.target.checked);
            });
        }

        // BCS test harness
        const runTestsBtn = document.getElementById('run-bcs-tests-btn');
        if (runTestsBtn) {
            runTestsBtn.addEventListener('click', () => this.runBCSTests());
        }

        // Claude response generation
        const generateBtn = document.getElementById('generate-response-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generateClaudeResponse());
        }

        // Use response button
        const useResponseBtn = document.getElementById('use-response-btn');
        if (useResponseBtn) {
            useResponseBtn.addEventListener('click', () => this.useGeneratedResponse());
        }
    }

    checkURLParams() {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('experimental') === '1') {
            const toggle = document.getElementById('experimental-agent-ux');
            if (toggle) {
                toggle.checked = true;
                this.toggleExperimentalUI(true);
            }
        }
    }

    async checkClaudeStatus() {
        const statusIndicator = document.getElementById('claude-status-indicator');
        const statusText = document.getElementById('claude-status-text');
        const claudeStatusDiv = document.getElementById('claude-status');

        try {
            const start = Date.now();
            const response = await fetch('/api/experimental/agent/status');
            const latency = Date.now() - start;
            
            if (response.ok) {
                const status = await response.json();
                this.claudeStatus = { ...status, latency };
                
                if (statusIndicator && statusText) {
                    if (status.ready) {
                        statusIndicator.className = 'badge bg-success';
                        statusIndicator.textContent = 'Ready';
                        statusText.textContent = `Claude API available (${latency}ms)`;
                    } else {
                        statusIndicator.className = 'badge bg-warning';
                        statusIndicator.textContent = 'Not Ready';
                        statusText.textContent = 'ANTHROPIC_API_KEY not configured';
                    }
                }
            } else {
                throw new Error('Status check failed');
            }
        } catch (error) {
            console.error('Claude status check failed:', error);
            if (statusIndicator && statusText) {
                statusIndicator.className = 'badge bg-danger';
                statusIndicator.textContent = 'Error';
                statusText.textContent = 'Status check failed';
            }
        }

        if (claudeStatusDiv) {
            claudeStatusDiv.style.display = 'block';
        }
    }

    toggleExperimentalUI(enabled) {
        this.isExperimentalEnabled = enabled;
        
        // Show/hide experimental panels
        const agentUXPanel = document.getElementById('experimental-agent-ux-panel');
        const rightRail = document.getElementById('experimental-right-rail');
        const claudeStatus = document.getElementById('claude-status');
        
        if (agentUXPanel) {
            agentUXPanel.style.display = enabled ? 'block' : 'none';
        }
        if (rightRail) {
            rightRail.style.display = enabled ? 'block' : 'none';
        }
        if (claudeStatus) {
            claudeStatus.style.display = enabled ? 'block' : 'none';
        }

        // Initialize experimental features if enabled
        if (enabled) {
            this.initializeExperimentalFeatures();
        }
    }

    initializeExperimentalFeatures() {
        // Initialize Bootstrap tabs if available
        if (typeof bootstrap !== 'undefined') {
            const tabTriggerList = [].slice.call(document.querySelectorAll('#right-rail-tabs button'));
            tabTriggerList.map(function (tabTriggerEl) {
                return new bootstrap.Tab(tabTriggerEl);
            });
        }
    }

    async runBCSTests() {
        const resultsDiv = document.getElementById('bcs-test-results');
        const testList = document.getElementById('bcs-test-list');
        
        if (!resultsDiv || !testList) return;

        // Show loading state
        resultsDiv.style.display = 'block';
        testList.innerHTML = '<div class="spinner-border spinner-border-sm me-2"></div>Running BCS tests...';

        try {
            // Get test cases
            const testsResponse = await fetch('/api/experimental/tests/bcse');
            if (!testsResponse.ok) throw new Error('Failed to get test cases');
            
            const testsData = await testsResponse.json();
            const testCases = testsData.tests || [];

            testList.innerHTML = '<h6>Running Tests:</h6>';

            // Run each test case
            const results = [];
            for (const testCase of testCases) {
                const resultElement = document.createElement('div');
                resultElement.className = 'test-case mb-2';
                resultElement.innerHTML = `
                    <div class="d-flex align-items-center">
                        <span class="badge bg-secondary me-2">Running</span>
                        <span>${testCase.name}</span>
                        <div class="spinner-border spinner-border-sm ms-2" style="width: 1rem; height: 1rem;"></div>
                    </div>
                `;
                testList.appendChild(resultElement);

                try {
                    const testResponse = await fetch('/api/experimental/tests/bcse/run', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(testCase)
                    });

                    if (testResponse.ok) {
                        const result = await testResponse.json();
                        results.push(result);
                        
                        // Update the test result display
                        const badge = result.passed ? 
                            '<span class="badge bg-success me-2">PASS</span>' :
                            '<span class="badge bg-danger me-2">FAIL</span>';
                        
                        resultElement.innerHTML = `
                            <div class="test-result">
                                ${badge}
                                <strong>${result.test_name}</strong>
                                <div class="small text-muted mt-1">
                                    Expected: ${result.expected} | Actual: ${result.actual || 'N/A'}
                                </div>
                                ${result.error ? `<div class="small text-danger">Error: ${result.error}</div>` : ''}
                            </div>
                        `;
                    } else {
                        resultElement.innerHTML = `
                            <span class="badge bg-danger me-2">ERROR</span>
                            <span>${testCase.name} - Test failed</span>
                        `;
                    }
                } catch (error) {
                    resultElement.innerHTML = `
                        <span class="badge bg-danger me-2">ERROR</span>
                        <span>${testCase.name} - ${error.message}</span>
                    `;
                }
            }

            // Update trace
            this.updateTrace('BCS Tests', { action: 'run_tests', results });

        } catch (error) {
            testList.innerHTML = `<div class="alert alert-danger">Failed to run tests: ${error.message}</div>`;
        }
    }

    async generateClaudeResponse() {
        if (!this.claudeStatus.ready) {
            alert('Claude API is not available. Please configure ANTHROPIC_API_KEY.');
            return;
        }

        const role = document.getElementById('response-role')?.value || 'applicant';
        const hint = document.getElementById('response-hint')?.value || 'free';
        const generateBtn = document.getElementById('generate-response-btn');
        const responseCard = document.getElementById('generated-response-card');
        const responseContent = document.getElementById('response-content');

        if (!generateBtn || !responseCard || !responseContent) return;

        // Show loading state
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Generating...';
        responseCard.style.display = 'none';

        try {
            // Build context from conversation trace
            const context = this.conversationTrace.map(entry => ({
                role: entry.role === 'user' ? 'user' : 'assistant',
                content: entry.message || entry.content || JSON.stringify(entry)
            }));

            // Build facts (this would normally come from the current scenario state)
            const facts = {
                scenario: 'bcse',
                applicant_payload: this.getCurrentApplicantPayload(),
                ingested: {}
            };

            const payload = { role, context, facts, hint };

            const response = await fetch('/api/experimental/agent/respond', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            
            if (!result.ok) {
                throw new Error(result.error || 'Unknown error');
            }

            // Display the generated response
            this.displayGeneratedResponse(result.result);
            responseCard.style.display = 'block';

            // Update trace
            this.updateTrace('Claude Response', { role, hint, response: result.result });

        } catch (error) {
            alert(`Failed to generate response: ${error.message}`);
            console.error('Claude response generation failed:', error);
        } finally {
            generateBtn.disabled = false;
            generateBtn.innerHTML = 'Generate Response';
        }
    }

    displayGeneratedResponse(claudeResult) {
        const responseContent = document.getElementById('response-content');
        if (!responseContent) return;

        let html = '';

        // Display message
        if (claudeResult.message) {
            html += `<div class="response-message mb-3">
                <h6>Message:</h6>
                <div class="message-content">${this.markdownToHtml(claudeResult.message)}</div>
            </div>`;
        }

        // Display state
        if (claudeResult.state) {
            const stateClass = claudeResult.state === 'completed' ? 'success' : 
                             claudeResult.state === 'working' ? 'warning' : 'secondary';
            html += `<div class="response-state mb-3">
                <span class="badge bg-${stateClass}">${claudeResult.state}</span>
            </div>`;
        }

        // Display actions
        if (claudeResult.actions && claudeResult.actions.length > 0) {
            html += '<div class="response-actions mb-3"><h6>Actions:</h6>';
            claudeResult.actions.forEach(action => {
                html += this.renderActionCard(action);
            });
            html += '</div>';
        }

        // Display artifacts
        if (claudeResult.artifacts && claudeResult.artifacts.length > 0) {
            html += '<div class="response-artifacts mb-3"><h6>Artifacts:</h6>';
            claudeResult.artifacts.forEach(artifact => {
                html += `<div class="artifact-item">${JSON.stringify(artifact, null, 2)}</div>`;
            });
            html += '</div>';
        }

        responseContent.innerHTML = html;
        this.lastGeneratedResponse = claudeResult;
    }

    renderActionCard(action) {
        const kind = action.kind || 'unknown';
        
        switch (kind) {
            case 'request_info':
                return `<div class="action-card request-info mb-2">
                    <div class="card card-sm">
                        <div class="card-body">
                            <h6 class="card-title">Information Request</h6>
                            <p>Requesting: ${(action.fields || []).join(', ')}</p>
                        </div>
                    </div>
                </div>`;

            case 'propose_decision':
                const decisionClass = action.decision === 'eligible' ? 'success' :
                                    action.decision === 'ineligible' ? 'danger' : 'warning';
                return `<div class="action-card propose-decision mb-2">
                    <div class="card card-sm border-${decisionClass}">
                        <div class="card-body">
                            <h6 class="card-title">
                                Decision: <span class="badge bg-${decisionClass}">${action.decision}</span>
                            </h6>
                            <p>${action.rationale || 'No rationale provided'}</p>
                        </div>
                    </div>
                </div>`;

            case 'request_docs':
                return `<div class="action-card request-docs mb-2">
                    <div class="card card-sm">
                        <div class="card-body">
                            <h6 class="card-title">Documentation Request</h6>
                            <ul class="mb-0">
                                ${(action.items || []).map(item => `<li>${item}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                </div>`;

            case 'propose_slots':
                return `<div class="action-card propose-slots mb-2">
                    <div class="card card-sm">
                        <div class="card-body">
                            <h6 class="card-title">Scheduling Slots</h6>
                            ${(action.slots || []).map(slot => `
                                <div class="slot-item mb-2">
                                    <strong>${slot.org || 'Unknown'}</strong><br>
                                    <small>${slot.start} - ${slot.end}</small><br>
                                    <small>${slot.location || 'Location TBD'}</small>
                                    ${slot.bookingLink ? `<br><a href="${slot.bookingLink}" class="btn btn-sm btn-outline-primary mt-1">Book</a>` : ''}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>`;

            default:
                return `<div class="action-card unknown mb-2">
                    <div class="card card-sm">
                        <div class="card-body">
                            <h6 class="card-title">Unknown Action: ${kind}</h6>
                            <pre><code>${JSON.stringify(action, null, 2)}</code></pre>
                        </div>
                    </div>
                </div>`;
        }
    }

    markdownToHtml(markdown) {
        // Simple markdown conversion
        return markdown
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    useGeneratedResponse() {
        if (!this.lastGeneratedResponse) return;

        // Add the response to the appropriate lane
        const role = this.lastGeneratedResponse.role || 'applicant';
        this.addMessageToLane(role, this.lastGeneratedResponse);

        // Hide the response card
        const responseCard = document.getElementById('generated-response-card');
        if (responseCard) {
            responseCard.style.display = 'none';
        }

        // Update trace
        this.updateTrace('Used Response', { role, response: this.lastGeneratedResponse });
    }

    addMessageToLane(role, message) {
        const laneId = role === 'applicant' ? 'applicant-messages' : 'administrator-messages';
        const lane = document.getElementById(laneId);
        
        if (!lane) return;

        const messageElement = document.createElement('div');
        messageElement.className = 'agent-message mb-3';
        
        const stateClass = message.state === 'completed' ? 'success' : 
                          message.state === 'working' ? 'warning' : 'secondary';
        
        messageElement.innerHTML = `
            <div class="message-header d-flex justify-content-between align-items-center">
                <span class="timestamp">${new Date().toLocaleTimeString()}</span>
                <span class="badge bg-${stateClass}">${message.state || 'unknown'}</span>
            </div>
            <div class="message-body">
                ${message.message ? this.markdownToHtml(message.message) : 'No message'}
            </div>
            ${message.actions && message.actions.length > 0 ? 
                `<div class="message-actions mt-2">
                    ${message.actions.map(action => this.renderActionCard(action)).join('')}
                </div>` : ''
            }
        `;

        lane.appendChild(messageElement);
        lane.scrollTop = lane.scrollHeight;
    }

    getCurrentApplicantPayload() {
        // Try to get from the applicant payload textarea
        const payloadTextarea = document.getElementById('applicant-payload');
        if (payloadTextarea && payloadTextarea.value.trim()) {
            try {
                return JSON.parse(payloadTextarea.value);
            } catch (e) {
                console.warn('Invalid JSON in applicant payload textarea');
            }
        }

        // Fallback to demo data
        return {
            sex: 'female',
            birthDate: '1969-08-10',
            last_mammogram: '2024-05-01'
        };
    }

    updateTrace(action, data) {
        this.conversationTrace.push({
            timestamp: new Date().toISOString(),
            action,
            data,
            role: 'system'
        });

        // Update trace panel
        const tracePanel = document.getElementById('conversation-trace');
        if (tracePanel) {
            const traceElement = document.createElement('div');
            traceElement.className = 'trace-entry mb-2';
            traceElement.innerHTML = `
                <div class="trace-header">
                    <strong>${action}</strong>
                    <small class="text-muted">${new Date().toLocaleTimeString()}</small>
                </div>
                <div class="trace-data small">
                    <pre><code>${JSON.stringify(data, null, 2)}</code></pre>
                </div>
            `;
            tracePanel.appendChild(traceElement);
            tracePanel.scrollTop = tracePanel.scrollHeight;
        }

        // Update raw JSON panel
        const rawPanel = document.getElementById('raw-json');
        if (rawPanel) {
            rawPanel.innerHTML = `<code>${JSON.stringify(this.conversationTrace, null, 2)}</code>`;
        }
    }
}

// Global Claude UX instance
let claudeUX = null;

// Initialize experimental features when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if UI_EXPERIMENTAL flag is enabled by looking for settings panel
    const settingsPanel = document.querySelector('.settings-panel');
    if (!settingsPanel || settingsPanel.hasAttribute('hidden')) {
        console.log('Experimental UI not enabled - skipping initialization');
        return;
    }
    
    console.log('Experimental UI enabled - initializing features');
    initializeExperimentalFeatures();
    
    // Initialize Claude Agent UX
    claudeUX = new ClaudeAgentUX();
    claudeUX.init().then(() => {
        console.log('Claude Agent UX initialized');
    }).catch(error => {
        console.error('Failed to initialize Claude Agent UX:', error);
    });
});

function initializeExperimentalFeatures() {
    // Initialize selftest status on load
    runSelftestCheck();
    
    // Load current settings
    loadCurrentSettings();
    
    // Set up event listeners for experimental controls
    setupExperimentalEventListeners();
}

function setupExperimentalEventListeners() {
    // Settings panel event listeners (already handled in main app.js)
    // These are supplemental handlers for experimental-specific functionality
    
    // Enhanced payload examples with scenario-specific data
    const examplesBtn = document.getElementById('examples-btn');
    if (examplesBtn) {
        // Override the existing examples handler with enhanced functionality
        examplesBtn.removeEventListener('click', fillExamples); // Remove default handler
        examplesBtn.addEventListener('click', fillEnhancedExamples);
    }
    
    // Real-time settings validation
    const settingsInputs = document.querySelectorAll('#scenario-select, input[name="mode"], #admin-processing-ms, #error-injection-rate, #capacity-limit, input[name="protocol-default"]');
    settingsInputs.forEach(input => {
        input.addEventListener('change', validateSettingsRealTime);
    });
    
    // Enhanced save settings with validation
    const saveBtn = document.getElementById('save-settings-btn');
    if (saveBtn) {
        // Add enhanced validation before saving
        saveBtn.addEventListener('click', function(e) {
            if (!validateAllSettings()) {
                e.preventDefault();
                e.stopImmediatePropagation();
            }
        }, true); // Use capture phase to intercept before main handler
    }
    
    // Scheduling Links functionality
    setupSchedulingEventListeners();
}

async function runSelftestCheck() {
    const selftestStatus = document.getElementById('selftest-status');
    if (!selftestStatus) return;
    
    try {
        selftestStatus.className = 'badge bg-secondary';
        selftestStatus.textContent = 'Checking...';
        
        const response = await fetch('/api/selftest');
        const data = await response.json();
        
        if (data.ok) {
            selftestStatus.className = 'badge bg-success';
            selftestStatus.textContent = '✓ All Systems';
            
            // Show additional status info in title
            const statusDetails = [
                `A2A: ${data.a2a.length} methods`,
                `MCP: ${data.mcp.length} methods`,
                `Scenario: ${data.scenario}`
            ];
            selftestStatus.title = statusDetails.join('\n');
        } else {
            selftestStatus.className = 'badge bg-danger';
            selftestStatus.textContent = '✗ Failed';
        }
    } catch (error) {
        selftestStatus.className = 'badge bg-warning';
        selftestStatus.textContent = '? Unknown';
        console.warn('Selftest check failed:', error);
    }
}

async function loadCurrentSettings() {
    try {
        // Load configuration to populate current values
        const configResponse = await fetch('/api/config');
        if (configResponse.ok) {
            const config = await configResponse.json();
            populateSettingsFromConfig(config);
        }
        
        // Load current requirements
        await loadRequirementsText();
        
    } catch (error) {
        console.warn('Failed to load current settings:', error);
    }
}

function populateSettingsFromConfig(config) {
    // Scenario
    const scenarioSelect = document.getElementById('scenario-select');
    if (scenarioSelect && config.scenario?.active) {
        scenarioSelect.value = config.scenario.active;
    }
    
    // Mode
    const mode = config.mode?.role || 'full_stack';
    const modeRadio = document.querySelector(`input[name="mode"][value="${mode}"]`);
    if (modeRadio) {
        modeRadio.checked = true;
    }
    
    // Simulation settings
    const adminMs = document.getElementById('admin-processing-ms');
    const errorRate = document.getElementById('error-injection-rate');
    const capacity = document.getElementById('capacity-limit');
    
    if (adminMs) adminMs.value = config.simulation?.admin_processing_ms || 1200;
    if (errorRate) errorRate.value = config.simulation?.error_injection_rate || 0.0;
    if (capacity) capacity.value = config.simulation?.capacity_limit || '';
    
    // Protocol default
    const protocolDefault = config.protocol?.default_transport || 'a2a';
    const protocolRadio = document.querySelector(`input[name="protocol-default"][value="${protocolDefault}"]`);
    if (protocolRadio) {
        protocolRadio.checked = true;
    }
}

async function loadRequirementsText() {
    const requirementsDiv = document.getElementById('requirements-text');
    if (!requirementsDiv) return;
    
    try {
        const response = await fetch('/api/requirements');
        if (response.ok) {
            const data = await response.json();
            requirementsDiv.textContent = data.requirements || 'No requirements available';
        } else {
            requirementsDiv.textContent = 'Error loading requirements';
        }
    } catch (error) {
        requirementsDiv.textContent = 'Failed to load requirements';
    }
}

async function fillEnhancedExamples() {
    const scenarioSelect = document.getElementById('scenario-select');
    const applicantPayload = document.getElementById('applicant-payload');
    const payloadError = document.getElementById('payload-error');
    
    if (!scenarioSelect || !applicantPayload) return;
    
    const scenario = scenarioSelect.value;
    
    try {
        // Get scenario-specific examples
        const response = await fetch(`/api/scenarios/${scenario}/examples`);
        let examplePayload = {};
        
        if (response.ok) {
            const data = await response.json();
            if (data.examples && data.examples.length > 0) {
                examplePayload = data.examples[0];
            }
        } else {
            // Fallback to default examples by scenario
            examplePayload = getDefaultExampleForScenario(scenario);
        }
        
        applicantPayload.value = JSON.stringify(examplePayload, null, 2);
        
        // Validate the payload
        if (payloadError) {
            payloadError.style.display = 'none';
        }
        
        // Show success feedback
        showTemporaryFeedback('Examples loaded successfully', 'success');
        
    } catch (error) {
        console.error('Failed to load enhanced examples:', error);
        
        // Fallback to default behavior
        const defaultExample = getDefaultExampleForScenario(scenario);
        applicantPayload.value = JSON.stringify(defaultExample, null, 2);
    }
}

function getDefaultExampleForScenario(scenario) {
    const examples = {
        bcse: {
            age: 56,
            sex: "female",
            birthDate: "1968-01-15",
            last_mammogram: "2024-12-01"
        },
        clinical_trial: {
            age: 45,
            sex: "female",
            condition: "breast_cancer",
            stage: "II",
            prior_treatments: ["chemotherapy"]
        },
        referral_specialist: {
            age: 42,
            sex: "male",
            symptoms: "chest pain",
            duration_days: 3,
            referral_type: "cardiology"
        },
        prior_auth: {
            age: 60,
            procedure_code: "77067",
            diagnosis_code: "Z12.31",
            prior_authorization_required: true
        },
        custom: {
            age: 35,
            sex: "female"
        }
    };
    
    return examples[scenario] || examples.bcse;
}

function validateSettingsRealTime() {
    // Real-time validation of settings as user types/changes
    const adminMs = document.getElementById('admin-processing-ms');
    const errorRate = document.getElementById('error-injection-rate');
    const capacity = document.getElementById('capacity-limit');
    
    let isValid = true;
    
    // Validate admin processing time
    if (adminMs) {
        const ms = parseInt(adminMs.value);
        if (isNaN(ms) || ms < 0 || ms > 30000) {
            markFieldInvalid(adminMs, 'Must be 0-30000 ms');
            isValid = false;
        } else {
            markFieldValid(adminMs);
        }
    }
    
    // Validate error injection rate
    if (errorRate) {
        const rate = parseFloat(errorRate.value);
        if (isNaN(rate) || rate < 0 || rate > 1) {
            markFieldInvalid(errorRate, 'Must be 0.0-1.0');
            isValid = false;
        } else {
            markFieldValid(errorRate);
        }
    }
    
    // Validate capacity limit
    if (capacity && capacity.value) {
        const cap = parseInt(capacity.value);
        if (isNaN(cap) || cap < 1) {
            markFieldInvalid(capacity, 'Must be positive integer or blank');
            isValid = false;
        } else {
            markFieldValid(capacity);
        }
    } else if (capacity) {
        markFieldValid(capacity); // Blank is valid
    }
    
    return isValid;
}

function validateAllSettings() {
    const isValid = validateSettingsRealTime();
    
    if (!isValid) {
        showTemporaryFeedback('Please correct validation errors before saving', 'danger');
        return false;
    }
    
    return true;
}

function markFieldInvalid(field, message) {
    field.classList.add('is-invalid');
    field.classList.remove('is-valid');
    
    // Add or update invalid feedback
    let feedback = field.nextElementSibling;
    if (!feedback || !feedback.classList.contains('invalid-feedback')) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.parentNode.insertBefore(feedback, field.nextSibling);
    }
    feedback.textContent = message;
}

function markFieldValid(field) {
    field.classList.remove('is-invalid');
    field.classList.add('is-valid');
    
    // Remove invalid feedback
    const feedback = field.nextElementSibling;
    if (feedback && feedback.classList.contains('invalid-feedback')) {
        feedback.remove();
    }
}

function showTemporaryFeedback(message, type = 'info') {
    // Create a temporary alert that auto-dismisses
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-2`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert after the save button
    const saveBtn = document.getElementById('save-settings-btn');
    if (saveBtn && saveBtn.parentNode) {
        saveBtn.parentNode.insertBefore(alertDiv, saveBtn.nextSibling);
        
        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    }
}

// Enhanced payload validation with scenario-specific checks
function validatePayloadEnhanced() {
    const applicantPayload = document.getElementById('applicant-payload');
    const payloadError = document.getElementById('payload-error');
    const scenarioSelect = document.getElementById('scenario-select');
    
    if (!applicantPayload || !payloadError) return true;
    
    const value = applicantPayload.value.trim();
    if (!value) {
        payloadError.style.display = 'none';
        return true;
    }
    
    try {
        const payload = JSON.parse(value);
        
        // Basic JSON validation passed, now do scenario-specific validation
        if (scenarioSelect) {
            const scenario = scenarioSelect.value;
            const validationResult = validatePayloadForScenario(payload, scenario);
            
            if (validationResult.isValid) {
                payloadError.style.display = 'none';
                return true;
            } else {
                payloadError.textContent = validationResult.error;
                payloadError.style.display = 'block';
                return false;
            }
        }
        
        payloadError.style.display = 'none';
        return true;
        
    } catch (error) {
        payloadError.textContent = `Invalid JSON: ${error.message}`;
        payloadError.style.display = 'block';
        return false;
    }
}

function validatePayloadForScenario(payload, scenario) {
    const validators = {
        bcse: (p) => {
            if (!p.age || !p.sex) return { isValid: false, error: 'BCSE requires age and sex' };
            if (p.sex !== 'female' && p.sex !== 'male') return { isValid: false, error: 'Sex must be "female" or "male"' };
            if (typeof p.age !== 'number' || p.age < 1 || p.age > 120) return { isValid: false, error: 'Age must be 1-120' };
            return { isValid: true };
        },
        clinical_trial: (p) => {
            if (!p.age || !p.condition) return { isValid: false, error: 'Clinical trial requires age and condition' };
            return { isValid: true };
        },
        referral_specialist: (p) => {
            if (!p.symptoms || !p.referral_type) return { isValid: false, error: 'Referral requires symptoms and referral_type' };
            return { isValid: true };
        },
        prior_auth: (p) => {
            if (!p.procedure_code) return { isValid: false, error: 'Prior auth requires procedure_code' };
            return { isValid: true };
        }
    };
    
    const validator = validators[scenario];
    if (validator) {
        return validator(payload);
    }
    
    // No specific validation for this scenario
    return { isValid: true };
}

// Scheduling Links functionality
function setupSchedulingEventListeners() {
    // Load scheduling config on init
    loadSchedulingConfig();
    
    // Save scheduling config
    const saveSchedulingBtn = document.getElementById('save-scheduling-btn');
    if (saveSchedulingBtn) {
        saveSchedulingBtn.addEventListener('click', saveSchedulingConfig);
    }
    
    // Test publishers
    const testPublishersBtn = document.getElementById('test-publishers-btn');
    if (testPublishersBtn) {
        testPublishersBtn.addEventListener('click', testPublishers);
    }
    
    // Schedule screening search
    const searchSlotsBtn = document.getElementById('search-slots-btn');
    if (searchSlotsBtn) {
        searchSlotsBtn.addEventListener('click', searchSlots);
    }
    
    // Try scheduling button
    const trySchedulingBtn = document.getElementById('try-scheduling-btn');
    if (trySchedulingBtn) {
        trySchedulingBtn.addEventListener('click', showScheduleScreeningPanel);
    }
    
    // Initialize date inputs with default range (next 14 days)
    initializeDateInputs();
    
    // Monitor for BCS eligibility to auto-show scheduling
    monitorBCSEligibility();
}

async function loadSchedulingConfig() {
    try {
        const response = await fetch('/api/scheduling/config');
        if (response.ok) {
            const config = await response.json();
            populateSchedulingConfig(config);
        }
    } catch (error) {
        console.warn('Failed to load scheduling config:', error);
    }
}

function populateSchedulingConfig(config) {
    const publishersTextarea = document.getElementById('scheduling-publishers');
    const cacheTtlInput = document.getElementById('scheduling-cache-ttl');
    const specialtyInput = document.getElementById('scheduling-specialty');
    const radiusInput = document.getElementById('scheduling-radius');
    const timezoneInput = document.getElementById('scheduling-timezone');
    
    if (publishersTextarea) {
        publishersTextarea.value = config.publishers ? config.publishers.join('\n') : '';
    }
    if (cacheTtlInput) {
        cacheTtlInput.value = config.cache_ttl_seconds || 300;
    }
    if (specialtyInput) {
        specialtyInput.value = config.default_specialty || 'mammography';
    }
    if (radiusInput) {
        radiusInput.value = config.default_radius_km || 50;
    }
    if (timezoneInput) {
        timezoneInput.value = config.default_timezone || 'America/New_York';
    }
}

async function saveSchedulingConfig() {
    const publishersTextarea = document.getElementById('scheduling-publishers');
    const cacheTtlInput = document.getElementById('scheduling-cache-ttl');
    const specialtyInput = document.getElementById('scheduling-specialty');
    const radiusInput = document.getElementById('scheduling-radius');
    const timezoneInput = document.getElementById('scheduling-timezone');
    
    const config = {
        publishers: publishersTextarea.value.split('\n').filter(url => url.trim()),
        cache_ttl_seconds: parseInt(cacheTtlInput.value) || 300,
        default_specialty: specialtyInput.value.trim() || null,
        default_radius_km: parseInt(radiusInput.value) || null,
        default_timezone: timezoneInput.value.trim() || null
    };
    
    try {
        const response = await fetch('/api/scheduling/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            showTemporaryFeedback('Scheduling configuration saved successfully', 'success');
        } else {
            const error = await response.json();
            showTemporaryFeedback(`Failed to save config: ${error.detail}`, 'danger');
        }
    } catch (error) {
        showTemporaryFeedback(`Save failed: ${error.message}`, 'danger');
    }
}

async function testPublishers() {
    const testBtn = document.getElementById('test-publishers-btn');
    const resultsDiv = document.getElementById('publisher-test-results');
    const resultsContent = document.getElementById('publisher-results-content');
    
    if (testBtn) {
        testBtn.disabled = true;
        testBtn.textContent = 'Testing...';
    }
    
    try {
        const response = await fetch('/api/scheduling/publishers/test', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (resultsDiv && resultsContent) {
            resultsDiv.style.display = 'block';
            
            if (response.ok && data.success) {
                let html = '<div class="text-success mb-2">✓ Test completed</div>';
                
                Object.entries(data.publishers).forEach(([url, result]) => {
                    if (result.status === 'success') {
                        html += `<div class="border-start border-success ps-2 mb-2">
                            <strong class="text-success">${url}</strong><br>
                            <small>Response: ${result.elapsed_ms}ms | Slots: ${result.counts.slots} | Cache age: ${result.cache_age_seconds}s</small>
                        </div>`;
                    } else {
                        html += `<div class="border-start border-danger ps-2 mb-2">
                            <strong class="text-danger">${url}</strong><br>
                            <small class="text-danger">Error: ${result.error}</small>
                        </div>`;
                    }
                });
                
                resultsContent.innerHTML = html;
            } else {
                resultsContent.innerHTML = '<div class="text-danger">Test failed</div>';
            }
        }
        
    } catch (error) {
        if (resultsContent) {
            resultsContent.innerHTML = `<div class="text-danger">Test failed: ${error.message}</div>`;
        }
    } finally {
        if (testBtn) {
            testBtn.disabled = false;
            testBtn.textContent = 'Test Publishers';
        }
    }
}

function initializeDateInputs() {
    const startDateInput = document.getElementById('search-start-date');
    const endDateInput = document.getElementById('search-end-date');
    
    if (startDateInput && endDateInput) {
        const today = new Date();
        const twoWeeksLater = new Date(today.getTime() + 14 * 24 * 60 * 60 * 1000);
        
        startDateInput.value = today.toISOString().split('T')[0];
        endDateInput.value = twoWeeksLater.toISOString().split('T')[0];
    }
}

function showScheduleScreeningPanel() {
    const panel = document.getElementById('schedule-screening-panel');
    if (panel) {
        panel.style.display = 'block';
        panel.scrollIntoView({ behavior: 'smooth' });
    }
}

function monitorBCSEligibility() {
    // Monitor transcript for BCS eligibility results
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE && 
                        node.textContent && 
                        node.textContent.toLowerCase().includes('eligible')) {
                        
                        // Check if this is a BCS eligibility result
                        const isEligible = node.textContent.toLowerCase().includes('eligible') && 
                                         !node.textContent.toLowerCase().includes('not eligible');
                        
                        if (isEligible) {
                            setTimeout(() => {
                                showScheduleScreeningPanel();
                                showTemporaryFeedback('Patient is eligible! Schedule screening now.', 'info');
                            }, 1000);
                        }
                    }
                });
            }
        });
    });
    
    const transcript = document.getElementById('transcript');
    if (transcript) {
        observer.observe(transcript, { childList: true, subtree: true });
    }
}

async function searchSlots() {
    const statusDiv = document.getElementById('slot-search-status');
    const resultsDiv = document.getElementById('slot-search-results');
    const emptyDiv = document.getElementById('slot-empty-results');
    const errorDiv = document.getElementById('slot-error-results');
    const resultsListDiv = document.getElementById('slot-results-list');
    
    // Hide all result states
    [resultsDiv, emptyDiv, errorDiv].forEach(div => {
        if (div) div.style.display = 'none';
    });
    
    // Show loading status
    if (statusDiv) statusDiv.style.display = 'block';
    
    // Collect search parameters
    const specialty = document.getElementById('search-specialty')?.value.trim();
    const radius = document.getElementById('search-radius')?.value;
    const startDate = document.getElementById('search-start-date')?.value;
    const endDate = document.getElementById('search-end-date')?.value;
    const org = document.getElementById('search-org')?.value.trim();
    const location = document.getElementById('search-location')?.value.trim();
    
    const searchQuery = {
        specialty: specialty || null,
        radius_km: radius ? parseInt(radius) : null,
        start: startDate ? `${startDate}T00:00:00Z` : null,
        end: endDate ? `${endDate}T23:59:59Z` : null,
        org: org || null,
        location_text: location || null,
        limit: 50
    };
    
    try {
        const response = await fetch('/api/scheduling/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(searchQuery)
        });
        
        const data = await response.json();
        
        // Hide loading status
        if (statusDiv) statusDiv.style.display = 'none';
        
        if (response.ok && data.success) {
            if (data.slots && data.slots.length > 0) {
                displaySlotResults(data.slots);
                if (resultsDiv) resultsDiv.style.display = 'block';
            } else {
                if (emptyDiv) emptyDiv.style.display = 'block';
            }
        } else {
            if (errorDiv) {
                errorDiv.style.display = 'block';
                const errorMsg = document.getElementById('slot-error-message');
                if (errorMsg) {
                    errorMsg.textContent = data.detail || 'Search failed';
                }
            }
        }
        
    } catch (error) {
        // Hide loading status
        if (statusDiv) statusDiv.style.display = 'none';
        
        if (errorDiv) {
            errorDiv.style.display = 'block';
            const errorMsg = document.getElementById('slot-error-message');
            if (errorMsg) {
                errorMsg.textContent = error.message;
            }
        }
    }
}

function displaySlotResults(slots) {
    const resultsListDiv = document.getElementById('slot-results-list');
    if (!resultsListDiv) return;
    
    resultsListDiv.innerHTML = '';
    
    slots.forEach((slot, index) => {
        const slotCard = document.createElement('div');
        slotCard.className = 'card mb-2';
        slotCard.innerHTML = `
            <div class="card-body p-3">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <h6 class="card-title mb-1">${formatSlotDateTime(slot.start)} - ${formatSlotTime(slot.end)}</h6>
                        <p class="card-text mb-1">
                            <strong>${slot.org}</strong><br>
                            <small class="text-muted">${slot.service}</small>
                        </p>
                        <p class="card-text">
                            <small class="text-muted">
                                ${slot.location.name}${slot.location.address ? ', ' + slot.location.address : ''}
                                ${slot.distance_km ? ` (${slot.distance_km.toFixed(1)} km away)` : ''}
                            </small>
                        </p>
                    </div>
                    <div class="col-md-4 text-end">
                        <button class="btn btn-success btn-sm book-slot-btn" 
                                data-slot-id="${slot.slot_id}" 
                                data-publisher="${slot.source_publisher}"
                                data-slot-info="${encodeURIComponent(JSON.stringify(slot))}">
                            Book
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        resultsListDiv.appendChild(slotCard);
    });
    
    // Add click handlers for booking buttons
    resultsListDiv.querySelectorAll('.book-slot-btn').forEach(btn => {
        btn.addEventListener('click', bookSlot);
    });
}

function formatSlotDateTime(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    } catch (error) {
        return isoString;
    }
}

function formatSlotTime(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    } catch (error) {
        return isoString;
    }
}

async function bookSlot(event) {
    const btn = event.target;
    const slotId = btn.dataset.slotId;
    const publisher = btn.dataset.publisher;
    const slotInfo = JSON.parse(decodeURIComponent(btn.dataset.slotInfo));
    
    btn.disabled = true;
    btn.textContent = 'Booking...';
    
    try {
        const response = await fetch('/api/scheduling/choose', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                slot_id: slotId,
                publisher_url: publisher,
                note: 'Booked from web UI'
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Show confirmation
            showTemporaryFeedback(data.confirmation, 'success');
            
            // Open booking link if available
            if (data.booking_link) {
                if (data.is_simulation) {
                    showTemporaryFeedback('Opening simulated booking portal...', 'info');
                }
                window.open(data.booking_link, '_blank');
            }
            
            // Log to trace
            logSchedulingTrace('slot_chosen', data.trace_data);
            
        } else {
            showTemporaryFeedback(`Booking failed: ${data.error || 'Unknown error'}`, 'danger');
        }
        
    } catch (error) {
        showTemporaryFeedback(`Booking failed: ${error.message}`, 'danger');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Book';
    }
}

function logSchedulingTrace(event, data) {
    // Add scheduling events to the transcript for traceability
    const transcript = document.getElementById('transcript');
    if (transcript) {
        const traceEntry = document.createElement('div');
        traceEntry.className = 'trace-entry scheduling-trace p-2 mb-2 border-start border-info';
        traceEntry.innerHTML = `
            <small class="text-muted">[SCHEDULING TRACE]</small><br>
            <strong>${event}:</strong> ${JSON.stringify(data, null, 2)}
        `;
        transcript.appendChild(traceEntry);
        transcript.scrollTop = transcript.scrollHeight;
    }
}

// Export functions for use by main app if needed
window.ExperimentalUI = {
    validatePayloadEnhanced,
    fillEnhancedExamples,
    validateAllSettings,
    showTemporaryFeedback,
    showScheduleScreeningPanel,
    searchSlots,
    loadSchedulingConfig
};