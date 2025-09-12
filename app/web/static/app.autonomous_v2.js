// Autonomous BCS v2 Controller
console.log("Autonomous BCS v2 Controller initialized");

class AutonomousV2Controller {
    constructor() {
        this.currentRunId = null;
        this.eventSource = null;
        this.isRunning = false;
        this.guidelines = null;
        this.facts = null;
    }

    init() {
        this.setupEventListeners();
        this.loadDefaultGuidelines();
    }

    setupEventListeners() {
        // Endpoint testing
        document.getElementById('test-applicant-btn')?.addEventListener('click', () => {
            this.testEndpoint('applicant', document.getElementById('applicant-endpoint').value);
        });
        
        document.getElementById('test-administrator-btn')?.addEventListener('click', () => {
            this.testEndpoint('administrator', document.getElementById('administrator-endpoint').value);
        });

        // FHIR operations
        document.getElementById('fetch-everything-btn')?.addEventListener('click', () => {
            this.fetchFHIRData();
        });

        // Guidelines operations
        document.getElementById('load-guidelines-btn')?.addEventListener('click', () => {
            this.loadCurrentGuidelines();
        });
        
        document.getElementById('restore-guidelines-btn')?.addEventListener('click', () => {
            this.loadDefaultGuidelines();
        });

        // Autonomous run controls
        document.getElementById('start-autonomous-btn')?.addEventListener('click', () => {
            this.startAutonomousRun();
        });
        
        document.getElementById('cancel-autonomous-btn')?.addEventListener('click', () => {
            this.cancelAutonomousRun();
        });

        // Quick tests
        document.getElementById('test-eligible-btn')?.addEventListener('click', () => {
            this.runQuickTest('eligible');
        });
        
        document.getElementById('test-needs-info-btn')?.addEventListener('click', () => {
            this.runQuickTest('needs-info');
        });
        
        document.getElementById('test-ineligible-btn')?.addEventListener('click', () => {
            this.runQuickTest('ineligible');
        });
        
        // Auto test with provided endpoints
        document.getElementById('auto-test-btn')?.addEventListener('click', () => {
            this.runAutomaticTest();
        });

        // Export
        document.getElementById('export-transcript-btn')?.addEventListener('click', () => {
            this.exportTranscript();
        });
    }

    async testEndpoint(type, url) {
        if (!url) {
            alert('Please enter an endpoint URL');
            return;
        }

        const button = document.getElementById(`test-${type}-btn`);
        const originalText = button.textContent;
        button.textContent = 'Testing...';
        button.disabled = true;

        try {
            // Test basic connectivity
            const response = await fetch(url, { 
                method: 'HEAD',
                mode: 'cors'
            });
            
            if (response.ok) {
                this.showStatus(`${type} endpoint: ✅ Reachable`);
            } else {
                this.showStatus(`${type} endpoint: ⚠️ Status ${response.status}`);
            }
        } catch (error) {
            this.showStatus(`${type} endpoint: ❌ ${error.message}`);
        } finally {
            button.textContent = originalText;
            button.disabled = false;
        }
    }

    async fetchFHIRData() {
        const patientId = document.getElementById('patient-id').value;
        const fhirBaseUrl = document.getElementById('fhir-base-url').value;
        const fhirToken = document.getElementById('fhir-token').value;

        if (!patientId) {
            alert('Please enter a Patient ID');
            return;
        }

        const button = document.getElementById('fetch-everything-btn');
        button.textContent = 'Fetching...';
        button.disabled = true;

        try {
            const payload = {
                patientId: patientId,
                fhir_base_url: fhirBaseUrl || 'https://hapi.fhir.org/baseR4'
            };

            if (fhirToken) {
                payload.bearer_token = fhirToken;
            }

            const response = await fetch('/api/experimental/v2/fhir/everything', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            
            if (result.ok) {
                this.facts = result.facts;
                this.displayMinimalFacts(result.facts);
                this.showValidationResults(result.validation);
                this.showStatus('✅ FHIR data fetched successfully');
            } else {
                throw new Error(result.error || 'Unknown error');
            }

        } catch (error) {
            alert(`Failed to fetch FHIR data: ${error.message}`);
            this.showStatus(`❌ FHIR fetch failed: ${error.message}`);
        } finally {
            button.textContent = 'Fetch $everything';
            button.disabled = false;
        }
    }

    displayMinimalFacts(facts) {
        document.getElementById('fact-sex').value = facts.sex || '';
        document.getElementById('fact-birth-date').value = facts.birthDate || '';
        document.getElementById('fact-last-mammogram').value = facts.last_mammogram || '';
        
        document.getElementById('minimal-facts-preview').style.display = 'block';
    }

    showValidationResults(validation) {
        if (validation.errors.length > 0) {
            alert(`FHIR validation errors: ${validation.errors.join(', ')}`);
        }
        if (validation.warnings.length > 0) {
            console.warn('FHIR validation warnings:', validation.warnings);
        }
    }

    async loadCurrentGuidelines() {
        try {
            const response = await fetch('/api/experimental/v2/guidelines/bcse');
            const result = await response.json();
            
            if (result.ok) {
                this.guidelines = result.guidelines;
                document.getElementById('guidelines-editor').value = JSON.stringify(result.guidelines, null, 2);
                this.showStatus('✅ Guidelines loaded');
            }
        } catch (error) {
            alert(`Failed to load guidelines: ${error.message}`);
        }
    }

    async loadDefaultGuidelines() {
        try {
            const response = await fetch('/api/experimental/v2/guidelines/bcse?version=default');
            const result = await response.json();
            
            if (result.ok) {
                this.guidelines = result.guidelines;
                document.getElementById('guidelines-editor').value = JSON.stringify(result.guidelines, null, 2);
                this.showStatus('✅ Default guidelines loaded');
            }
        } catch (error) {
            alert(`Failed to load default guidelines: ${error.message}`);
        }
    }

    async runAutomaticTest() {
        console.log('Starting automatic test with provided endpoints');
        
        try {
            // Use quick test endpoint with default configuration
            const response = await fetch('/api/experimental/v2/test/autonomous-quick', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    api_key: this.getApiKey()
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            this.currentRunId = result.run_id;
            this.showStatus(`🚀 Automatic test completed: ${result.status}`);
            
            // Display results
            this.displayAutomaticTestResults(result);
            
        } catch (error) {
            console.error('Automatic test failed:', error);
            this.showStatus(`❌ Automatic test failed: ${error.message}`);
        }
    }
    
    displayAutomaticTestResults(result) {
        const container = document.getElementById('autonomous-applicant-messages');
        if (!container) return;
        
        container.innerHTML = '<h6>Automatic Test Results</h6>';
        
        // Show frames
        result.frames?.forEach((frame, index) => {
            const frameDiv = document.createElement('div');
            frameDiv.className = 'autonomous-message mb-2';
            frameDiv.innerHTML = `
                <div class="message-header">
                    <small>Frame ${index + 1}: ${frame.type}</small>
                    <small class="text-muted">${new Date(frame.timestamp).toLocaleTimeString()}</small>
                </div>
                <div class="message-content">
                    <pre>${JSON.stringify(frame, null, 2)}</pre>
                </div>
            `;
            container.appendChild(frameDiv);
        });
        
        // Show final outcome
        if (result.final_state?.final_outcome) {
            const outcomeDiv = document.createElement('div');
            outcomeDiv.className = 'autonomous-message mb-2';
            outcomeDiv.style.borderLeftColor = '#28a745';
            outcomeDiv.innerHTML = `
                <div class="message-header">
                    <strong>Final Outcome</strong>
                </div>
                <div class="message-content">
                    <pre>${JSON.stringify(result.final_state.final_outcome, null, 2)}</pre>
                </div>
            `;
            container.appendChild(outcomeDiv);
        }
    }

    async startAutonomousRun() {
        // Try to get facts or use defaults
        let facts = this.getCurrentFacts();
        if (!facts || (!facts.sex && !facts.birthDate)) {
            // Use default facts for testing
            facts = {
                sex: 'female',
                birthDate: '1970-01-01',
                last_mammogram: '2022-01-01'
            };
        }

        // Prepare guidelines
        const guidelinesText = document.getElementById('guidelines-editor')?.value;
        let guidelines;
        try {
            guidelines = guidelinesText ? JSON.parse(guidelinesText) : null;
        } catch (error) {
            console.warn('Invalid guidelines JSON, will use defaults:', error);
            guidelines = null;
        }

        // Prepare configuration with defaults
        const config = {
            scenario: 'bcse',
            facts: facts,
            a2a: {
                applicant_endpoint: document.getElementById('applicant-endpoint')?.value || 'https://care-commons.meteorapp.com/mcp',
                administrator_endpoint: document.getElementById('administrator-endpoint')?.value || 'https://care-commons.meteorapp.com/mcp'
            },
            options: {
                max_turns: parseInt(document.getElementById('max-turns')?.value || '6'),
                sse_timeout_ms: parseInt(document.getElementById('sse-timeout')?.value || '8000'),
                poll_interval_ms: parseInt(document.getElementById('poll-interval')?.value || '1200'),
                dry_run: document.getElementById('dry-run')?.checked || false
            },
            guidelines: guidelines || {
                name: "BCS Eligibility Guidelines",
                version: "1.0",
                rules: [
                    {"field": "sex", "operator": "equals", "value": "female", "required": true},
                    {"field": "age", "operator": "between", "min": 50, "max": 74, "required": true},
                    {"field": "months_since_last_mammogram", "operator": "greater_than", "value": 24, "required": false}
                ]
            }
        };

        // Add API key if available
        if (window.claudeUX && window.claudeUX.sessionApiKey) {
            config.api_key = window.claudeUX.sessionApiKey;
        }

        try {
            // Start autonomous run
            const response = await fetch('/api/experimental/v2/autonomy/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            
            if (result.ok) {
                this.currentRunId = result.run_id;
                this.isRunning = true;
                this.updateRunControls();
                this.showAutonomousView();
                this.startEventStream();
                this.showStatus(`🚀 Autonomous run started (${result.run_id})`);
            } else {
                throw new Error(result.error || 'Failed to start run');
            }

        } catch (error) {
            alert(`Failed to start autonomous run: ${error.message}`);
            this.showStatus(`❌ Start failed: ${error.message}`);
        }
    }

    startEventStream() {
        if (!this.currentRunId) return;

        const url = `/api/experimental/v2/autonomy/run/${this.currentRunId}/stream`;
        this.eventSource = new EventSource(url);

        this.eventSource.onmessage = (event) => {
            try {
                const frame = JSON.parse(event.data);
                this.handleDialogFrame(frame);
            } catch (error) {
                console.error('Failed to parse SSE frame:', error);
            }
        };

        this.eventSource.onerror = (event) => {
            console.error('SSE error:', event);
            this.showStatus('❌ Connection error - falling back to polling');
            this.eventSource.close();
            this.startPolling();
        };
    }

    async startPolling() {
        if (!this.currentRunId || !this.isRunning) return;

        try {
            const response = await fetch(`/api/experimental/v2/autonomy/status?run_id=${this.currentRunId}`);
            const result = await response.json();
            
            if (result.ok) {
                this.updateDialogStatus(result.status);
                
                if (result.status.state === 'completed' || result.status.state === 'cancelled' || result.status.state === 'error') {
                    this.isRunning = false;
                    this.updateRunControls();
                    return;
                }
            }
        } catch (error) {
            console.error('Polling error:', error);
        }

        // Continue polling
        setTimeout(() => this.startPolling(), 2000);
    }

    handleDialogFrame(frame) {
        console.log('Dialog frame:', frame);

        switch (frame.type) {
            case 'start':
                this.clearDialogMessages();
                this.showStatus('📍 Dialog started');
                break;
                
            case 'turn_start':
                this.addDialogMessage(frame.agent, `Starting turn ${frame.turn}...`, 'working', frame.source);
                break;
                
            case 'turn_complete':
                this.updateDialogMessage(frame.agent, frame.response, 'completed');
                this.updateProgress(frame.turn);
                break;
                
            case 'turn_error':
                this.addDialogMessage(frame.agent, `Error: ${frame.error}`, 'error');
                break;
                
            case 'completion':
                this.handleDialogCompletion(frame);
                break;
                
            case 'error':
                this.showStatus(`❌ Dialog error: ${frame.error}`);
                this.isRunning = false;
                this.updateRunControls();
                break;
        }
    }

    handleDialogCompletion(frame) {
        this.isRunning = false;
        this.updateRunControls();
        
        if (frame.outcome) {
            this.showArbiterDecision(frame.outcome);
        }
        
        this.showStatus(`✅ Dialog completed in ${frame.total_turns} turns`);
    }

    showArbiterDecision(outcome) {
        const decisionBar = document.getElementById('arbiter-decision-bar');
        const decisionSpan = document.getElementById('arbiter-decision');
        const rationaleSpan = document.getElementById('arbiter-rationale');
        
        decisionSpan.textContent = outcome.chosen;
        rationaleSpan.textContent = outcome.reason;
        
        // Color code the decision
        decisionBar.className = 'alert';
        if (outcome.chosen === 'eligible') {
            decisionBar.classList.add('alert-success');
        } else if (outcome.chosen === 'ineligible') {
            decisionBar.classList.add('alert-danger');
        } else {
            decisionBar.classList.add('alert-warning');
        }
        
        decisionBar.style.display = 'block';
    }

    addDialogMessage(agent, content, state, source = 'claude') {
        const container = document.getElementById(`autonomous-${agent}-messages`);
        const messageDiv = document.createElement('div');
        messageDiv.className = 'autonomous-message mb-2';
        messageDiv.dataset.agent = agent;
        messageDiv.dataset.state = state;
        
        const stateClass = state === 'completed' ? 'success' : 
                          state === 'working' ? 'warning' : 
                          state === 'error' ? 'danger' : 'secondary';
        
        messageDiv.innerHTML = `
            <div class="message-header d-flex justify-content-between align-items-center">
                <span class="timestamp">${new Date().toLocaleTimeString()}</span>
                <div>
                    <span class="badge bg-${stateClass}">${state}</span>
                    <span class="badge bg-outline-secondary ms-1">${source}</span>
                </div>
            </div>
            <div class="message-content">
                ${this.formatMessageContent(content)}
            </div>
        `;
        
        container.appendChild(messageDiv);
        container.scrollTop = container.scrollHeight;
    }

    updateDialogMessage(agent, response, state) {
        const container = document.getElementById(`autonomous-${agent}-messages`);
        const messages = container.querySelectorAll('.autonomous-message');
        const lastMessage = messages[messages.length - 1];
        
        if (lastMessage && lastMessage.dataset.agent === agent) {
            lastMessage.dataset.state = state;
            const badge = lastMessage.querySelector('.badge');
            badge.className = `badge bg-${state === 'completed' ? 'success' : 'warning'}`;
            badge.textContent = state;
            
            const content = lastMessage.querySelector('.message-content');
            content.innerHTML = this.formatMessageContent(response);
        }
    }

    formatMessageContent(content) {
        if (typeof content === 'string') {
            return content;
        }
        
        if (content && typeof content === 'object') {
            if (content.message) {
                let html = `<div class="response-message">${content.message}</div>`;
                
                if (content.actions && content.actions.length > 0) {
                    html += '<div class="response-actions mt-2">';
                    content.actions.forEach(action => {
                        html += this.renderActionSummary(action);
                    });
                    html += '</div>';
                }
                
                return html;
            }
            
            return `<pre class="small">${JSON.stringify(content, null, 2)}</pre>`;
        }
        
        return String(content);
    }

    renderActionSummary(action) {
        const kind = action.kind;
        
        switch (kind) {
            case 'propose_decision':
                const decisionClass = action.decision === 'eligible' ? 'success' :
                                    action.decision === 'ineligible' ? 'danger' : 'warning';
                return `<div class="action-summary">
                    <span class="badge bg-${decisionClass}">${action.decision}</span>
                    <small class="ms-2">${action.rationale || ''}</small>
                </div>`;
                
            case 'request_info':
                return `<div class="action-summary">
                    <span class="badge bg-info">Info Requested</span>
                    <small class="ms-2">${(action.fields || []).join(', ')}</small>
                </div>`;
                
            case 'request_docs':
                return `<div class="action-summary">
                    <span class="badge bg-secondary">Docs Requested</span>
                    <small class="ms-2">${(action.items || []).join(', ')}</small>
                </div>`;
                
            default:
                return `<div class="action-summary">
                    <span class="badge bg-light text-dark">${kind}</span>
                </div>`;
        }
    }

    clearDialogMessages() {
        document.getElementById('autonomous-applicant-messages').innerHTML = '';
        document.getElementById('autonomous-administrator-messages').innerHTML = '';
        document.getElementById('arbiter-decision-bar').style.display = 'none';
    }

    updateProgress(turn) {
        const maxTurns = parseInt(document.getElementById('max-turns').value);
        const progress = document.getElementById('dialog-progress');
        progress.textContent = `Turn ${turn} of ${maxTurns}`;
    }

    async cancelAutonomousRun() {
        if (!this.currentRunId) return;

        try {
            const response = await fetch('/api/experimental/v2/autonomy/cancel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.currentRunId)
            });

            if (response.ok) {
                this.isRunning = false;
                this.updateRunControls();
                this.showStatus('🛑 Run cancelled');
                
                if (this.eventSource) {
                    this.eventSource.close();
                }
            }
        } catch (error) {
            alert(`Failed to cancel run: ${error.message}`);
        }
    }

    async runQuickTest(testType) {
        const button = document.getElementById(`test-${testType}-btn`);
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Running...';

        try {
            const apiKey = window.claudeUX?.sessionApiKey;
            const url = `/api/experimental/v2/test/quick-run?test_case=${testType}&dry_run=true${apiKey ? `&api_key=${encodeURIComponent(apiKey)}` : ''}`;
            
            const response = await fetch(url, { method: 'POST' });
            const result = await response.json();
            
            if (result.ok) {
                this.displayQuickTestResult(result);
            } else {
                throw new Error(result.error || 'Test failed');
            }
        } catch (error) {
            alert(`Quick test failed: ${error.message}`);
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    }

    displayQuickTestResult(result) {
        const resultsDiv = document.getElementById('quick-test-results');
        
        const badgeClass = result.passed ? 'success' : 'danger';
        const badgeText = result.passed ? 'PASS' : 'FAIL';
        
        resultsDiv.innerHTML = `
            <div class="test-result">
                <span class="badge bg-${badgeClass}">${badgeText}</span>
                <strong>${result.test_case}</strong><br>
                <small>Expected: ${result.expected_outcome} | Actual: ${result.actual_outcome || 'N/A'}</small>
            </div>
        `;
        
        resultsDiv.style.display = 'block';
    }

    getCurrentFacts() {
        // Try to get facts from FHIR first, then manual inputs
        if (this.facts) {
            return this.facts;
        }
        
        // Manual override
        const sex = document.getElementById('fact-sex').value;
        const birthDate = document.getElementById('fact-birth-date').value;
        const lastMammogram = document.getElementById('fact-last-mammogram').value;
        
        if (sex || birthDate || lastMammogram) {
            return {
                sex: sex || null,
                birthDate: birthDate || null,
                last_mammogram: lastMammogram || null,
                source: 'manual_override'
            };
        }
        
        return null;
    }

    showAutonomousView() {
        document.getElementById('artifacts').style.display = 'none';
        document.getElementById('autonomous-live-view').style.display = 'block';
    }

    hideAutonomousView() {
        document.getElementById('artifacts').style.display = 'block';
        document.getElementById('autonomous-live-view').style.display = 'none';
    }

    updateRunControls() {
        const startBtn = document.getElementById('start-autonomous-btn');
        const cancelBtn = document.getElementById('cancel-autonomous-btn');
        
        startBtn.disabled = this.isRunning;
        cancelBtn.disabled = !this.isRunning;
        
        if (this.isRunning) {
            startBtn.textContent = 'Running...';
        } else {
            startBtn.textContent = 'Start Autonomous Run';
        }
    }

    async exportTranscript() {
        if (!this.currentRunId) {
            alert('No active dialog to export');
            return;
        }

        try {
            const response = await fetch(`/api/experimental/v2/autonomy/status?run_id=${this.currentRunId}`);
            const result = await response.json();
            
            if (result.ok) {
                const transcript = result.status;
                const blob = new Blob([JSON.stringify(transcript, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                
                const a = document.createElement('a');
                a.href = url;
                a.download = `autonomous_dialog_${this.currentRunId}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                this.showStatus('📥 Transcript exported');
            }
        } catch (error) {
            alert(`Failed to export transcript: ${error.message}`);
        }
    }

    showStatus(message) {
        const statusElement = document.getElementById('autonomous-status');
        if (statusElement) {
            statusElement.textContent = message;
        }
        console.log('Autonomous V2:', message);
    }
}

// Global autonomous v2 instance
let autonomousV2 = null;

// Initialize when DOM is ready and experimental mode is enabled
document.addEventListener('DOMContentLoaded', function() {
    // Wait for claudeUX to be available
    setTimeout(() => {
        if (window.claudeUX && window.claudeUX.isExperimentalEnabled) {
            autonomousV2 = new AutonomousV2Controller();
            autonomousV2.init();
            console.log('Autonomous V2 Controller initialized');
        }
    }, 500);
});

// Export for global access
window.autonomousV2 = autonomousV2;