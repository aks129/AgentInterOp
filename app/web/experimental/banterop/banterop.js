/**
 * Banterop-style Scenario Runner Frontend
 */

class BanteropRunner {
    constructor() {
        this.currentRun = null;
        this.currentScenario = null;
        this.currentAgentCard = null;
        this.fhirFacts = null;
        this.bcsEvaluation = null;
        
        // Initialize UI
        this.initializeEventListeners();
        this.loadBcsRules();
        
        // Check for URL parameters
        this.checkUrlParameters();
    }

    initializeEventListeners() {
        // Handle Enter key in message input
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
    }

    checkUrlParameters() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // Load preset configurations from URL
        if (urlParams.get('scenario')) {
            document.getElementById('scenario-url').value = urlParams.get('scenario');
        }
        
        if (urlParams.get('agent')) {
            document.getElementById('agent-card-url').value = urlParams.get('agent');
        }
    }

    // Scenario Management
    async loadSampleScenario() {
        try {
            const response = await fetch('/api/experimental/banterop/scenario/sample/bcs');
            const result = await response.json();
            
            if (result.success) {
                this.currentScenario = result.data;
                this.displayScenarioInfo(result.data);
                this.populateAgentRoles(result.data.agents);
                document.getElementById('scenario-url').value = 'sample://bcs';
                this.showInfo('Sample BCS scenario loaded');
            } else {
                throw new Error(result.error || 'Failed to load sample scenario');
            }
        } catch (error) {
            this.showError('Failed to load sample scenario: ' + error.message);
        }
    }

    async loadScenario() {
        const url = document.getElementById('scenario-url').value.trim();
        if (!url) {
            this.showError('Please enter a scenario URL');
            return;
        }

        const btn = document.getElementById('load-scenario-btn');
        const originalText = btn.textContent;
        btn.textContent = 'Loading...';
        btn.disabled = true;

        try {
            const response = await fetch('/api/experimental/banterop/scenario/load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const result = await response.json();

            if (result.success) {
                this.currentScenario = result.data;
                this.displayScenarioInfo(result.data);
                this.populateAgentRoles(result.data.agents);
                this.updateScenarioViewer();
                this.showInfo('Scenario loaded successfully');
            } else {
                throw new Error(result.error || 'Failed to load scenario');
            }
        } catch (error) {
            this.showError('Failed to load scenario: ' + error.message);
        } finally {
            btn.textContent = originalText;
            btn.disabled = false;
        }
    }

    displayScenarioInfo(scenario) {
        const infoDiv = document.getElementById('scenario-info');
        const nameElement = document.getElementById('scenario-name');
        const descElement = document.getElementById('scenario-description');
        const agentsElement = document.getElementById('scenario-agents');

        nameElement.textContent = scenario.metadata.name || scenario.metadata.id;
        descElement.textContent = scenario.metadata.description || '';
        
        const agentList = scenario.agents.map(agent => 
            `${agent.name || agent.agentId} (${agent.role || 'unspecified'})`
        ).join(', ');
        agentsElement.innerHTML = `<small>Agents: ${agentList}</small>`;

        infoDiv.classList.remove('hidden');
    }

    populateAgentRoles(agents) {
        const select = document.getElementById('my-role');
        
        // Clear existing options except first two
        while (select.children.length > 2) {
            select.removeChild(select.lastChild);
        }

        // Add scenario agents
        agents.forEach(agent => {
            const option = document.createElement('option');
            option.value = agent.agentId;
            option.textContent = `${agent.name || agent.agentId} (${agent.role || 'agent'})`;
            select.appendChild(option);
        });
    }

    // Agent Card Management
    setPresetAgent(type) {
        const input = document.getElementById('agent-card-url');
        switch (type) {
            case 'carecommons':
                input.value = 'https://care-commons.meteorapp.com';
                break;
            case 'local':
                input.value = window.location.origin;
                break;
        }
    }

    async loadAgentCard() {
        const url = document.getElementById('agent-card-url').value.trim();
        if (!url) {
            this.showError('Please enter an agent card URL');
            return;
        }

        const btn = document.getElementById('load-agent-card-btn');
        const originalText = btn.textContent;
        btn.textContent = 'Loading...';
        btn.disabled = true;

        try {
            const response = await fetch('/api/experimental/banterop/agentcard/load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const result = await response.json();

            if (result.success) {
                this.currentAgentCard = result.data;
                this.displayAgentCardInfo(result.data);
                
                // Update smoke test URL
                document.getElementById('smoke-test-url').value = result.data.url;
                
                this.showInfo('Agent card loaded successfully');
            } else {
                throw new Error(result.error || 'Failed to load agent card');
            }
        } catch (error) {
            this.showError('Failed to load agent card: ' + error.message);
        } finally {
            btn.textContent = originalText;
            btn.disabled = false;
        }
    }

    displayAgentCardInfo(agentCard) {
        const infoDiv = document.getElementById('agent-card-info');
        const nameElement = document.getElementById('agent-name');
        const detailsElement = document.getElementById('agent-details');

        const details = agentCard.details;
        nameElement.textContent = details.name;
        
        detailsElement.innerHTML = `
            <small>
                Protocol: ${details.protocolVersion || 'Unknown'}<br>
                Transport: ${details.preferredTransport || 'Unknown'}<br>
                Streaming: ${details.streaming ? 'Yes' : 'No'}<br>
                A2A URL: <code>${agentCard.url}</code>
            </small>
        `;

        infoDiv.classList.remove('hidden');
    }

    // FHIR Management
    async fetchFhirData() {
        const base = document.getElementById('fhir-base').value.trim();
        const patientId = document.getElementById('fhir-patient-id').value.trim();
        const token = document.getElementById('fhir-token').value.trim();

        if (!base || !patientId) {
            this.showError('Please enter FHIR base URL and patient ID');
            return;
        }

        try {
            const response = await fetch('/api/experimental/banterop/fhir/everything', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ base, patientId, token: token || null })
            });

            const result = await response.json();

            if (result.success) {
                this.fhirFacts = result.data.facts;
                this.displayFhirFacts(result.data.facts);
                this.updateFactsViewer(result.data);
                
                // Enable BCS evaluation button
                document.getElementById('evaluate-bcs-btn').disabled = false;
                
                this.showInfo('FHIR data fetched successfully');
            } else {
                throw new Error(result.error || 'Failed to fetch FHIR data');
            }
        } catch (error) {
            this.showError('Failed to fetch FHIR data: ' + error.message);
        }
    }

    displayFhirFacts(facts) {
        const factsDiv = document.getElementById('fhir-facts');
        const contentDiv = document.getElementById('fhir-facts-content');

        contentDiv.innerHTML = `
            <small>
                Patient: ${facts.patientId || 'Unknown'}<br>
                Sex: ${facts.sex || 'Unknown'}<br>
                Age: ${facts.age || 'Unknown'}<br>
                Birth Date: ${facts.birthDate || 'Unknown'}<br>
                Last Mammogram: ${facts.last_mammogram_date || 'None on record'}
            </small>
        `;

        factsDiv.classList.remove('hidden');
    }

    // BCS Management
    async loadBcsRules() {
        try {
            const response = await fetch('/api/experimental/banterop/bcs/rules');
            const result = await response.json();

            if (result.success) {
                document.getElementById('bcs-rules').value = JSON.stringify(result.data, null, 2);
            }
        } catch (error) {
            console.error('Failed to load BCS rules:', error);
        }
    }

    async saveBcsRules() {
        const rulesText = document.getElementById('bcs-rules').value.trim();
        if (!rulesText) {
            this.showError('Please enter BCS rules JSON');
            return;
        }

        try {
            const rules = JSON.parse(rulesText);
            
            const response = await fetch('/api/experimental/banterop/bcs/rules', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(rules)
            });

            const result = await response.json();

            if (result.success) {
                this.showInfo('BCS rules saved successfully');
            } else {
                throw new Error(result.error || 'Failed to save BCS rules');
            }
        } catch (error) {
            this.showError('Failed to save BCS rules: ' + error.message);
        }
    }

    async resetBcsRules() {
        try {
            const response = await fetch('/api/experimental/banterop/bcs/rules/reset', {
                method: 'POST'
            });

            const result = await response.json();

            if (result.success) {
                document.getElementById('bcs-rules').value = JSON.stringify(result.data, null, 2);
                this.showInfo('BCS rules reset to defaults');
            } else {
                throw new Error(result.error || 'Failed to reset BCS rules');
            }
        } catch (error) {
            this.showError('Failed to reset BCS rules: ' + error.message);
        }
    }

    async evaluateBcs() {
        if (!this.fhirFacts) {
            this.showError('Please fetch FHIR data first');
            return;
        }

        try {
            const response = await fetch('/api/experimental/banterop/bcs/evaluate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ patientFacts: this.fhirFacts })
            });

            const result = await response.json();

            if (result.success) {
                this.bcsEvaluation = result.data.evaluation;
                this.displayBcsEvaluation(result.data);
                this.showInfo('BCS evaluation completed');
            } else {
                throw new Error(result.error || 'Failed to evaluate BCS');
            }
        } catch (error) {
            this.showError('Failed to evaluate BCS: ' + error.message);
        }
    }

    displayBcsEvaluation(evaluation) {
        const evalDiv = document.getElementById('bcs-evaluation');
        const contentDiv = document.getElementById('bcs-evaluation-content');

        const decision = evaluation.evaluation.decision;
        const emoji = decision === 'eligible' ? '✅' : decision === 'ineligible' ? '❌' : 'ℹ️';
        
        contentDiv.innerHTML = `
            <div>${emoji} <strong>${decision.toUpperCase()}</strong></div>
            <div style="margin-top: 0.5rem; font-size: 0.875rem;">
                ${evaluation.evaluation.rationale}
            </div>
            <details style="margin-top: 0.5rem;">
                <summary style="cursor: pointer; font-size: 0.75rem;">Show details</summary>
                <pre style="font-size: 0.75rem; margin-top: 0.25rem;">${evaluation.summary}</pre>
            </details>
        `;

        evalDiv.classList.remove('hidden');
    }

    // Run Management
    async startRun() {
        if (!this.currentScenario) {
            this.showError('Please load a scenario first');
            return;
        }

        const myAgentId = document.getElementById('my-role').value;
        const agentCardUrl = document.getElementById('agent-card-url').value.trim();
        const conversationMode = document.getElementById('conversation-mode').value;

        if (!myAgentId) {
            this.showError('Please select your role');
            return;
        }

        if (conversationMode === 'remote' && !agentCardUrl) {
            this.showError('Please enter agent card URL for remote mode');
            return;
        }

        const config = {
            scenarioUrl: document.getElementById('scenario-url').value,
            myAgentId,
            remoteAgentCardUrl: agentCardUrl || null,
            conversationMode,
            fhir: this.getFhirConfig(),
            bcse: { enabled: !!this.fhirFacts }
        };

        const btn = document.getElementById('start-run-btn');
        const originalText = btn.textContent;
        btn.textContent = 'Starting...';
        btn.disabled = true;

        try {
            const response = await fetch('/api/experimental/banterop/run/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            const result = await response.json();

            if (result.success) {
                this.currentRun = result.data.runId;
                this.updateRunStatus('ready', 'Run started - ready for messages');
                this.showMessageComposer();
                await this.refreshRunStatus();
                this.showInfo('Run started successfully');
            } else {
                throw new Error(result.error || 'Failed to start run');
            }
        } catch (error) {
            this.showError('Failed to start run: ' + error.message);
        } finally {
            btn.textContent = originalText;
            btn.disabled = false;
        }
    }

    getFhirConfig() {
        const base = document.getElementById('fhir-base').value.trim();
        const patientId = document.getElementById('fhir-patient-id').value.trim();
        const token = document.getElementById('fhir-token').value.trim();

        if (!base || !patientId) return {};

        return {
            base,
            patientId,
            token: token || null
        };
    }

    async sendMessage() {
        if (!this.currentRun) {
            this.showError('No active run');
            return;
        }

        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        
        if (!message) {
            this.showError('Please enter a message');
            return;
        }

        const stream = document.getElementById('stream-mode').checked;
        const sendBtn = document.getElementById('send-btn');
        
        sendBtn.textContent = 'Sending...';
        sendBtn.disabled = true;

        try {
            const messageParts = [{ kind: 'text', text: message }];
            
            const response = await fetch('/api/experimental/banterop/run/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    runId: this.currentRun,
                    parts: messageParts,
                    stream
                })
            });

            const result = await response.json();

            if (result.success) {
                messageInput.value = '';
                await this.refreshRunStatus();
                this.showInfo('Message sent successfully');
            } else {
                throw new Error(result.error || 'Failed to send message');
            }
        } catch (error) {
            this.showError('Failed to send message: ' + error.message);
        } finally {
            sendBtn.textContent = 'Send';
            sendBtn.disabled = false;
        }
    }

    async refreshRunStatus() {
        if (!this.currentRun) return;

        try {
            const response = await fetch(`/api/experimental/banterop/run/status?runId=${this.currentRun}`);
            const result = await response.json();

            if (result.success) {
                this.updateTranscript(result.data.transcript);
                this.updateTraceViewer(result.data);
                this.updateArtifacts(result.data.artifacts);
                this.updateRunStatus(result.data.status, this.getStatusText(result.data.status));
            }
        } catch (error) {
            console.error('Failed to refresh run status:', error);
        }
    }

    getStatusText(status) {
        const statusTexts = {
            'initializing': 'Initializing run...',
            'ready': 'Ready for messages',
            'working': 'Processing message...',
            'waiting': 'Waiting for input',
            'failed': 'Run failed',
            'cancelled': 'Run cancelled'
        };
        return statusTexts[status] || status;
    }

    updateRunStatus(status, text) {
        const statusDiv = document.getElementById('run-status');
        const statusIndicator = statusDiv.querySelector('.status-indicator');
        const statusText = document.getElementById('run-status-text');

        statusText.textContent = text;
        
        // Update status indicator
        statusIndicator.className = 'status-indicator';
        switch (status) {
            case 'ready':
            case 'waiting':
                statusIndicator.classList.add('status-ready');
                break;
            case 'working':
                statusIndicator.classList.add('status-working');
                break;
            case 'failed':
                statusIndicator.classList.add('status-error');
                break;
            default:
                statusIndicator.classList.add('status-offline');
        }

        statusDiv.classList.remove('hidden');
    }

    showMessageComposer() {
        document.getElementById('message-composer').style.display = 'block';
    }

    updateTranscript(transcript) {
        const myMessages = document.getElementById('my-messages');
        const remoteMessages = document.getElementById('remote-messages');

        myMessages.innerHTML = '';
        remoteMessages.innerHTML = '';

        transcript.forEach(msg => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${msg.source === 'remote' ? 'remote' : ''}`;

            const time = new Date(msg.timestamp).toLocaleTimeString();
            messageDiv.innerHTML = `
                <div class="message-meta">${time} - ${msg.role}</div>
                <div class="message-content">${this.escapeHtml(msg.content)}</div>
            `;

            if (msg.source === 'remote') {
                remoteMessages.appendChild(messageDiv);
            } else {
                myMessages.appendChild(messageDiv);
            }
        });
    }

    // Smoke Testing
    async runSmokeTest() {
        const url = document.getElementById('smoke-test-url').value.trim();
        const scriptLength = parseInt(document.getElementById('smoke-test-length').value);

        if (!url) {
            this.showError('Please enter remote A2A URL');
            return;
        }

        try {
            const response = await fetch('/api/experimental/banterop/test/smoke', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    remoteA2aUrl: url,
                    scriptLength
                })
            });

            const result = await response.json();

            if (result.success) {
                this.displaySmokeTestResults(result.data);
            } else {
                throw new Error(result.error || 'Smoke test failed');
            }
        } catch (error) {
            this.showError('Failed to run smoke test: ' + error.message);
        }
    }

    displaySmokeTestResults(results) {
        const resultsDiv = document.getElementById('smoke-test-results');
        resultsDiv.innerHTML = JSON.stringify(results, null, 2);
        resultsDiv.classList.remove('hidden');
    }

    // UI Helpers
    updateScenarioViewer() {
        const viewer = document.getElementById('scenario-viewer');
        viewer.textContent = JSON.stringify(this.currentScenario, null, 2);
    }

    updateFactsViewer(fhirData) {
        const viewer = document.getElementById('facts-viewer');
        viewer.textContent = JSON.stringify(fhirData, null, 2);
    }

    updateTraceViewer(runData) {
        const viewer = document.getElementById('trace-viewer');
        viewer.textContent = JSON.stringify(runData, null, 2);
    }

    updateArtifacts(artifacts) {
        const artifactsList = document.getElementById('artifacts-list');
        
        if (!artifacts || artifacts.length === 0) {
            artifactsList.innerHTML = 'No artifacts yet...';
            return;
        }

        artifactsList.innerHTML = artifacts.map(artifact => `
            <div class="message">
                <div class="message-meta">${artifact.type} - ${artifact.name}</div>
                <div class="message-content">${this.escapeHtml(artifact.content)}</div>
            </div>
        `).join('');
    }

    exportTrace() {
        if (!this.currentRun) {
            this.showError('No active run to export');
            return;
        }

        const traceData = document.getElementById('trace-viewer').textContent;
        this.downloadJson(traceData, `trace-${this.currentRun}.json`);
    }

    downloadJson(data, filename) {
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    showInfo(message) {
        console.log('INFO:', message);
        // Could add toast notifications here
    }

    showError(message) {
        console.error('ERROR:', message);
        alert('Error: ' + message);
        // Could add toast notifications here
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Tab Management
function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab content
    document.getElementById(tabName + '-content').classList.remove('hidden');
    
    // Add active class to selected tab
    event.target.classList.add('active');
}

// Collapsible Management
function toggleCollapsible(header) {
    const collapsible = header.parentElement;
    collapsible.classList.toggle('expanded');
}

// Global instance
let banteropRunner;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    banteropRunner = new BanteropRunner();
});

// Export functions for HTML onclick handlers
window.loadSampleScenario = () => banteropRunner.loadSampleScenario();
window.loadScenario = () => banteropRunner.loadScenario();
window.setPresetAgent = (type) => banteropRunner.setPresetAgent(type);
window.loadAgentCard = () => banteropRunner.loadAgentCard();
window.fetchFhirData = () => banteropRunner.fetchFhirData();
window.loadBcsRules = () => banteropRunner.loadBcsRules();
window.saveBcsRules = () => banteropRunner.saveBcsRules();
window.resetBcsRules = () => banteropRunner.resetBcsRules();
window.evaluateBcs = () => banteropRunner.evaluateBcs();
window.startRun = () => banteropRunner.startRun();
window.sendMessage = () => banteropRunner.sendMessage();
window.runSmokeTest = () => banteropRunner.runSmokeTest();
window.exportTrace = () => banteropRunner.exportTrace();