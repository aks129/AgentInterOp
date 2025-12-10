/**
 * Banterop V2 - Modern Agent Interoperability Platform
 */

class BanteropV2 {
    constructor() {
        this.state = {
            currentRun: null,
            currentScenario: null,
            currentAgentCard: null,
            fhirFacts: null,
            bcsEvaluation: null,
            guidelines: null,
            messages: [],
            runs: [],
            logs: [],
            apiAvailable: false
        };

        this.api = {
            baseUrl: '/api/experimental/banterop',
            headers: { 'Content-Type': 'application/json' }
        };

        this.init();
    }

    async init() {
        try {
            this.addLog('Starting Banterop V2 initialization...', 'info');
            this.setupEventListeners();
            this.setupTabSwitching();

            // Check if API is available
            this.addLog('Checking API availability...', 'info');
            await this.checkApiAvailability();

            if (this.state.apiAvailable) {
                this.addLog('Checking LLM status...', 'info');
                await this.checkLlmStatus();

                this.addLog('Updating statistics...', 'info');
                await this.updateStats();

                this.checkUrlParameters();
                this.addLog('System initialized successfully', 'success');
                this.updateStatus('Ready', 'online');
            } else {
                this.addLog('API not available - running in limited mode', 'warning');
                this.updateStatus('Limited Mode', 'offline');
                this.showApiUnavailableMessage();
            }
        } catch (error) {
            this.addLog(`Initialization failed: ${error.message}`, 'error');
            this.updateStatus('Error', 'error');
            console.error('Banterop V2 initialization error:', error);
        }
    }

    async checkApiAvailability() {
        try {
            // Try a simple API call to check if the backend is available
            const response = await fetch(`${this.api.baseUrl}/llm/status`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            this.state.apiAvailable = response.ok;
            if (this.state.apiAvailable) {
                this.addLog('API is available', 'success');
            } else {
                this.addLog(`API returned status ${response.status}`, 'warning');
            }
        } catch (error) {
            this.state.apiAvailable = false;
            this.addLog(`API unavailable: ${error.message}`, 'warning');
        }
    }

    showApiUnavailableMessage() {
        // Show a message to users about limited functionality
        const container = document.querySelector('.main-grid');
        if (container) {
            const message = document.createElement('div');
            message.className = 'alert alert-warning';
            message.innerHTML = `
                <strong>Limited Mode</strong><br>
                The Banterop API is currently unavailable. Some features may not work correctly.<br>
                <small>This may be due to server startup time or configuration issues.</small><br>
                <button class="btn btn-secondary" onclick="location.reload()">Retry</button>
            `;
            container.insertBefore(message, container.firstChild);
        }
    }

    setupEventListeners() {
        // Tab switching for all panels
        document.querySelectorAll('.tabs').forEach(tabContainer => {
            tabContainer.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', (e) => {
                    const tabName = e.target.dataset.tab;
                    if (!tabName) return;

                    // Update active tab
                    tabContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    e.target.classList.add('active');

                    // Update content
                    const panel = tabContainer.closest('.panel-content');
                    if (panel) {
                        panel.querySelectorAll('.tab-content').forEach(content => {
                            content.classList.remove('active');
                        });
                        const targetContent = panel.querySelector(`#tab-${tabName}`);
                        if (targetContent) {
                            targetContent.classList.add('active');
                        }
                    }
                });
            });
        });

        // Run selector
        const runSelect = document.getElementById('runSelect');
        if (runSelect) {
            runSelect.addEventListener('change', (e) => {
                if (e.target.value) {
                    this.loadRun(e.target.value);
                }
            });
        }

        // Scenario preset selector
        const scenarioPreset = document.getElementById('scenarioPreset');
        if (scenarioPreset) {
            scenarioPreset.addEventListener('change', (e) => {
                if (e.target.value === 'sample-bcs') {
                    this.loadSampleScenario();
                } else if (e.target.value === 'clinical-informaticist') {
                    this.loadClinicalInformaticistScenario();
                }
            });
        }
    }

    setupTabSwitching() {
        // Already handled in setupEventListeners
    }

    checkUrlParameters() {
        const params = new URLSearchParams(window.location.search);

        if (params.get('scenario')) {
            document.getElementById('scenarioUrl').value = params.get('scenario');
            this.loadScenario();
        }

        if (params.get('agent')) {
            document.getElementById('agentCardUrl').value = params.get('agent');
            this.loadAgentCard();
        }
    }

    // UI Helpers
    togglePanel(panelId) {
        const panel = document.getElementById(panelId);
        if (panel) {
            panel.classList.toggle('collapsed');
        }
    }

    toggleHelp() {
        const modal = document.getElementById('helpModal');
        if (modal) {
            modal.classList.toggle('active');
        }
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-content">${message}</div>
        `;

        container.appendChild(toast);

        // Remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // API Methods
    async apiCall(endpoint, method = 'GET', body = null) {
        const fullUrl = `${this.api.baseUrl}${endpoint}`;

        try {
            const options = {
                method,
                headers: { ...this.api.headers }
            };

            if (body) {
                options.body = JSON.stringify(body);
            }

            this.addLog(`API Call: ${method} ${fullUrl}`, 'info');
            const response = await fetch(fullUrl, options);

            if (!response.ok) {
                const errorText = await response.text();
                let errorData;
                try {
                    errorData = JSON.parse(errorText);
                } catch {
                    errorData = { message: errorText };
                }

                const errorMsg = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
                throw new Error(errorMsg);
            }

            const data = await response.json();
            this.addLog(`API Success: ${method} ${endpoint}`, 'success');
            return data;
        } catch (error) {
            const errorMsg = `API Error (${method} ${endpoint}): ${error.message}`;
            this.addLog(errorMsg, 'error');
            console.error('API call details:', { fullUrl, method, body, error });
            throw error;
        }
    }

    // Scenario Management
    async loadScenario() {
        if (!this.state.apiAvailable) {
            this.showAlert('API is not available. Please check your connection and try again.', 'error');
            return;
        }

        const url = document.getElementById('scenarioUrl').value.trim();
        const preset = document.getElementById('scenarioPreset').value;

        if (!url && !preset) {
            this.showAlert('Please enter a scenario URL or select a preset', 'error');
            return;
        }

        this.setLoading('scenarioLoading', true);

        try {
            let result;
            let a2aEndpoint = null;

            // Map presets to their API endpoints and A2A endpoints
            const presetMap = {
                'colonoscopy-scheduling': {
                    endpoint: '/scenario/sample/colonoscopy-scheduling',
                    a2a: '/api/colonoscopy-scheduler/a2a'
                },
                'sample-bcs': {
                    endpoint: '/scenario/sample/bcs',
                    a2a: '/api/bridge/demo/a2a'
                },
                'clinical-informaticist': {
                    endpoint: '/scenario/sample/clinical-informaticist',
                    a2a: '/api/bridge/cql-measure/a2a'
                },
                'clinical-trial': {
                    endpoint: '/scenario/sample/bcs',  // Use BCS as fallback
                    a2a: '/api/bridge/clinical-trial/a2a'
                },
                'prior-auth': {
                    endpoint: '/scenario/sample/bcs',  // Use BCS as fallback
                    a2a: '/api/bridge/prior-auth/a2a'
                }
            };

            if (preset && presetMap[preset]) {
                const presetConfig = presetMap[preset];
                const fullUrl = window.location.origin + this.api.baseUrl + presetConfig.endpoint;
                this.state.scenarioUrl = fullUrl;
                this.state.scenarioPreset = preset;
                a2aEndpoint = presetConfig.a2a;
                result = await this.apiCall(presetConfig.endpoint);
            } else if (url) {
                this.state.scenarioUrl = url;
                this.state.scenarioPreset = null;
                result = await this.apiCall('/scenario/load', 'POST', { url });
            }

            if (result && result.success) {
                this.state.currentScenario = result.data;
                this.showScenarioInfo(result.data);
                await this.updateStats();
                this.addLog('Scenario loaded successfully', 'success');

                // Auto-set the A2A endpoint if we have one
                if (a2aEndpoint) {
                    const smokeTestUrl = window.location.origin + a2aEndpoint;
                    document.getElementById('smokeTestUrl').value = smokeTestUrl;
                    this.state.remoteA2aUrl = smokeTestUrl;
                    this.addLog(`A2A endpoint set to: ${smokeTestUrl}`, 'info');
                }
            }
        } catch (error) {
            this.showAlert(`Failed to load scenario: ${error.message}`, 'error');
        } finally {
            this.setLoading('scenarioLoading', false);
        }
    }

    async loadSampleScenario() {
        document.getElementById('scenarioPreset').value = 'sample-bcs';
        await this.loadScenario();
    }

    async loadClinicalInformaticistScenario() {
        if (!this.state.apiAvailable) {
            this.showAlert('API is not available. Please check your connection and try again.', 'error');
            return;
        }

        this.setLoading('scenarioLoading', true);

        try {
            const result = await this.apiCall('/scenario/sample/clinical-informaticist');

            if (result.success) {
                this.state.currentScenario = result.data;
                // Store the scenario URL for run start
                const fullUrl = window.location.origin + this.api.baseUrl + '/scenario/sample/clinical-informaticist';
                this.state.scenarioUrl = fullUrl;
                this.state.scenarioPreset = 'clinical-informaticist';
                this.showScenarioInfo(result.data);

                // Auto-configure the agent card for Clinical Informaticist
                const agentCardUrl = window.location.origin + '/.well-known/agent-card.json';
                document.getElementById('agentCardUrl').value = agentCardUrl;
                this.state.agentCardUrl = agentCardUrl;

                // Also set the A2A endpoint for smoke testing
                const a2aUrl = window.location.origin + '/api/bridge/cql-measure/a2a';
                document.getElementById('smokeTestUrl').value = a2aUrl;
                this.state.remoteA2aUrl = a2aUrl;

                // Auto-load the agent card
                await this.loadAgentCard();

                await this.updateStats();
                this.addLog('Clinical Informaticist scenario loaded successfully', 'success');
                this.addLog('A2A endpoint: /api/bridge/cql-measure/a2a', 'info');
            }
        } catch (error) {
            this.showAlert(`Failed to load Clinical Informaticist scenario: ${error.message}`, 'error');
        } finally {
            this.setLoading('scenarioLoading', false);
        }
    }

    showScenarioInfo(scenario) {
        const info = document.getElementById('scenarioInfo');
        if (info) {
            const metadata = scenario.metadata || {};
            info.innerHTML = `
                <strong>${metadata.title || 'Unnamed Scenario'}</strong><br>
                ${metadata.description || 'No description'}<br>
                <small>Agents: ${scenario.agents ? scenario.agents.length : 0}</small>
            `;
            info.classList.remove('hidden');
        }
    }

    // Agent Management
    async loadAgentCard() {
        const url = document.getElementById('agentCardUrl').value.trim();
        if (!url) {
            this.showAlert('Please enter an agent card URL', 'error');
            return;
        }

        try {
            const result = await this.apiCall('/agentcard/load', 'POST', { url });

            if (result.success) {
                this.state.currentAgentCard = result.data;
                this.showAgentInfo(result.data);
                await this.updateStats();
                this.addLog('Agent card loaded successfully', 'success');
            }
        } catch (error) {
            this.showAlert(`Failed to load agent card: ${error.message}`, 'error');
        }
    }

    setPresetAgent(preset) {
        const urls = {
            carecommons: 'https://care-commons.meteorapp.com/.well-known/agent-card.json',
            local: 'http://localhost:8000/.well-known/agent-card.json'
        };

        const url = urls[preset];
        if (url) {
            document.getElementById('agentCardUrl').value = url;
            this.loadAgentCard();
        }
    }

    showAgentInfo(agentData) {
        const info = document.getElementById('agentInfo');
        if (info) {
            const details = agentData.details || {};
            info.innerHTML = `
                <div class="alert alert-success">
                    <strong>${details.name || 'Unknown Agent'}</strong><br>
                    Transport: ${details.preferredTransport || 'Unknown'}<br>
                    <small>URL: ${agentData.url || 'N/A'}</small>
                </div>
            `;
            info.classList.remove('hidden');
        }
    }

    // FHIR Management
    async fetchFhirData() {
        const base = document.getElementById('fhirBase').value.trim();
        const patientId = document.getElementById('patientId').value.trim();
        const token = document.getElementById('bearerToken').value.trim();

        if (!base || !patientId) {
            this.showAlert('Please provide FHIR server URL and patient ID', 'error');
            return;
        }

        try {
            const result = await this.apiCall('/fhir/everything', 'POST', {
                base,
                patientId,
                token: token || null
            });

            if (result.success) {
                this.state.fhirFacts = result.data.facts;
                this.showFhirFacts(result.data.facts);
                this.addLog('FHIR data fetched successfully', 'success');
            }
        } catch (error) {
            this.showAlert(`Failed to fetch FHIR data: ${error.message}`, 'error');
        }
    }

    showFhirFacts(facts) {
        const container = document.getElementById('fhirFacts');
        if (container) {
            container.textContent = JSON.stringify(facts, null, 2);
            container.classList.remove('hidden');
        }
    }

    // Guidelines Management
    async loadGuidelines() {
        const guidelinesJson = document.getElementById('guidelinesJson').value.trim();

        if (!guidelinesJson) {
            this.showAlert('Please provide guidelines JSON', 'error');
            return;
        }

        try {
            const guidelines = JSON.parse(guidelinesJson);
            const result = await this.apiCall('/bcs/rules', 'POST', guidelines);

            if (result.success) {
                this.state.guidelines = result.data;
                this.showAlert('Guidelines loaded successfully', 'success', 'guidelinesInfo');
                this.addLog('Guidelines updated', 'success');
            }
        } catch (error) {
            this.showAlert(`Failed to load guidelines: ${error.message}`, 'error');
        }
    }

    async resetGuidelines() {
        try {
            const result = await this.apiCall('/bcs/rules/reset', 'POST');

            if (result.success) {
                this.state.guidelines = result.data;
                document.getElementById('guidelinesJson').value = JSON.stringify(result.data, null, 2);
                this.showAlert('Guidelines reset to defaults', 'success', 'guidelinesInfo');
                this.addLog('Guidelines reset', 'info');
            }
        } catch (error) {
            this.showAlert(`Failed to reset guidelines: ${error.message}`, 'error');
        }
    }

    // Run Management
    async startNewRun() {
        if (!this.state.currentScenario) {
            this.showAlert('Please load a scenario first', 'error');
            return;
        }

        try {
            // Determine the scenario URL - use preset name or actual URL
            const scenarioUrl = this.state.scenarioUrl ||
                this.state.scenarioPreset ||
                document.getElementById('scenarioUrl').value.trim();

            if (!scenarioUrl) {
                this.showAlert('No scenario URL available', 'error');
                return;
            }

            // Determine agent ID from loaded scenario (use first agent or 'requester')
            const myAgentId = this.state.currentScenario.agents?.[0]?.agentId || 'requester';

            // Get remote agent card URL if available
            const remoteAgentCardUrl = this.state.agentCardUrl ||
                document.getElementById('agentCardUrl').value.trim();

            const config = {
                scenarioUrl: scenarioUrl,
                myAgentId: myAgentId,
                remoteAgentCardUrl: remoteAgentCardUrl || null,
                conversationMode: remoteAgentCardUrl ? 'remote' : 'local',
                fhir: this.state.fhirFacts ? { facts: this.state.fhirFacts } : {},
                bcse: this.state.guidelines ? { enabled: true, guidelines: this.state.guidelines } : {}
            };

            this.addLog(`Starting run with scenario: ${scenarioUrl}`, 'info');
            const result = await this.apiCall('/run/start', 'POST', config);

            if (result.success) {
                this.state.currentRun = result.data.runId;
                this.state.messages = [];
                this.updateConversationDisplay();
                this.updateRunSelector();
                await this.updateStats();
                this.addLog(`Run started: ${result.data.runId}`, 'success');

                // Show initial message if available
                if (this.state.currentScenario.agents?.[0]?.messageToUseWhenInitiatingConversation) {
                    this.addMessage('assistant', this.state.currentScenario.agents[0].messageToUseWhenInitiatingConversation);
                }
            }
        } catch (error) {
            this.showAlert(`Failed to start run: ${error.message}`, 'error');
        }
    }

    async sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();

        if (!message) {
            return;
        }

        // If no run started but we have a direct A2A URL, use direct mode
        if (!this.state.currentRun && this.state.remoteA2aUrl) {
            await this.sendDirectA2AMessage(message);
            return;
        }

        if (!this.state.currentRun) {
            this.showAlert('Please start a conversation first', 'error');
            return;
        }

        const sendBtn = document.getElementById('sendBtn');
        sendBtn.disabled = true;
        input.disabled = true;

        try {
            const result = await this.apiCall('/run/send', 'POST', {
                runId: this.state.currentRun,
                parts: [{ kind: 'text', text: message }],
                stream: false
            });

            if (result) {
                this.addMessage('user', message);
                // Extract response from various possible locations
                let responseText = null;
                if (result.data?.response) {
                    responseText = result.data.response;
                } else if (result.data?.result?.message?.parts) {
                    responseText = result.data.result.message.parts
                        .filter(p => p.kind === 'text')
                        .map(p => p.text)
                        .join('\n');
                }
                if (responseText) {
                    this.addMessage('assistant', responseText);
                }
                input.value = '';
                await this.updateStats();
            }
        } catch (error) {
            this.showAlert(`Failed to send message: ${error.message}`, 'error');
        } finally {
            sendBtn.disabled = false;
            input.disabled = false;
            input.focus();
        }
    }

    async sendDirectA2AMessage(message) {
        const sendBtn = document.getElementById('sendBtn');
        const input = document.getElementById('messageInput');
        sendBtn.disabled = true;
        input.disabled = true;

        try {
            this.addMessage('user', message);

            // Build A2A JSON-RPC payload
            const payload = {
                jsonrpc: '2.0',
                id: Date.now().toString(),
                method: 'message/send',
                params: {
                    message: {
                        parts: [{ kind: 'text', text: message }]
                    },
                    taskId: this.state.currentTaskId || null
                }
            };

            const result = await this.apiCall('/a2a/proxy', 'POST', {
                url: this.state.remoteA2aUrl,
                rpc: payload,
                stream: false
            });

            if (result.success && result.data) {
                const resultData = result.data.result || result.data;

                // Extract task ID for continuation
                if (resultData.id) {
                    this.state.currentTaskId = resultData.id;
                } else if (resultData.taskId) {
                    this.state.currentTaskId = resultData.taskId;
                }

                // Extract response text from various possible locations
                let responseText = null;
                let responses = [];

                // Check for history array (A2A format)
                if (resultData.history && Array.isArray(resultData.history)) {
                    const agentMessages = resultData.history.filter(h => h.role === 'agent');
                    for (const msg of agentMessages) {
                        if (msg.parts) {
                            const text = msg.parts
                                .filter(p => p.kind === 'text')
                                .map(p => p.text)
                                .join('\n');
                            if (text) responses.push(text);
                        }
                    }
                }

                // Check for direct message.parts
                if (resultData.message?.parts) {
                    const text = resultData.message.parts
                        .filter(p => p.kind === 'text')
                        .map(p => p.text)
                        .join('\n');
                    if (text) responses.push(text);
                }

                // Handle artifacts (CQL code, etc.)
                if (resultData.artifacts && Array.isArray(resultData.artifacts)) {
                    for (const artifact of resultData.artifacts) {
                        if (artifact.kind === 'file' && artifact.file) {
                            // Decode base64 content
                            let content = artifact.file.bytes;
                            try {
                                content = atob(artifact.file.bytes);
                            } catch (e) {
                                // Not base64, use as-is
                            }
                            responses.push(`**${artifact.file.name}**:\n\`\`\`cql\n${content}\n\`\`\``);
                        } else if (artifact.content) {
                            responses.push(`**${artifact.name || 'Artifact'}**:\n\`\`\`\n${artifact.content}\n\`\`\``);
                        }
                    }
                }

                responseText = responses.join('\n\n');

                if (responseText) {
                    this.addMessage('assistant', responseText);
                } else {
                    this.addMessage('assistant', 'Response received but no text content found.');
                    console.log('A2A Response:', result.data);
                }

                input.value = '';
                this.addLog('Direct A2A message sent successfully', 'success');
            }
        } catch (error) {
            this.showAlert(`Failed to send message: ${error.message}`, 'error');
        } finally {
            sendBtn.disabled = false;
            input.disabled = false;
            input.focus();
        }
    }

    addMessage(role, content) {
        const message = {
            role,
            content,
            timestamp: new Date().toLocaleTimeString()
        };

        this.state.messages.push(message);
        this.updateConversationDisplay();
    }

    updateConversationDisplay() {
        const container = document.getElementById('conversationContainer');
        if (!container) return;

        if (this.state.messages.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-text">No conversation started</div>
                    <button class="btn" onclick="banteropApp.startNewRun()">
                        Start New Conversation
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = this.state.messages.map(msg => `
            <div class="message ${msg.role}">
                <div class="message-header">
                    <span class="message-role">${msg.role}</span>
                    <span class="message-timestamp">${msg.timestamp}</span>
                </div>
                <div class="message-content">${this.formatMessageContent(msg.content)}</div>
            </div>
        `).join('');

        container.scrollTop = container.scrollHeight;
    }

    formatMessageContent(content) {
        // Basic markdown-like formatting
        let formatted = this.escapeHtml(content);
        formatted = formatted.replace(/\n/g, '<br>');
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        return formatted;
    }

    async loadRun(runId) {
        try {
            const result = await this.apiCall(`/run/status?runId=${runId}`);

            if (result.success) {
                this.state.currentRun = runId;
                this.state.messages = result.data.transcript || [];
                this.updateConversationDisplay();
                this.addLog(`Loaded run: ${runId}`, 'info');
            }
        } catch (error) {
            this.showAlert(`Failed to load run: ${error.message}`, 'error');
        }
    }

    async updateRunSelector() {
        try {
            const result = await this.apiCall('/run/list');

            if (result.success) {
                const select = document.getElementById('runSelect');
                if (select) {
                    const currentValue = select.value;
                    select.innerHTML = '<option value="">New Run</option>';

                    result.data.runs.forEach(run => {
                        const option = document.createElement('option');
                        option.value = run.runId;
                        option.textContent = `${run.runId} (${run.status})`;
                        select.appendChild(option);
                    });

                    if (currentValue) {
                        select.value = currentValue;
                    }
                }
            }
        } catch (error) {
            console.error('Failed to update run selector:', error);
        }
    }

    // Testing Methods
    async runSmokeTest() {
        const url = document.getElementById('smokeTestUrl').value.trim();
        const scriptLength = parseInt(document.getElementById('scriptLength').value);

        if (!url) {
            this.showAlert('Please provide remote A2A URL', 'error');
            return;
        }

        try {
            const result = await this.apiCall('/test/smoke', 'POST', {
                remoteA2aUrl: url,
                scriptLength
            });

            if (result.success) {
                this.showSmokeTestResults(result.data);
                this.addLog(`Smoke test ${result.data.passed ? 'PASSED' : 'FAILED'}`,
                    result.data.passed ? 'success' : 'error');
            }
        } catch (error) {
            this.showAlert(`Smoke test failed: ${error.message}`, 'error');
        }
    }

    showSmokeTestResults(data) {
        const container = document.getElementById('smokeTestResults');
        if (container) {
            container.textContent = JSON.stringify(data, null, 2);
            container.classList.remove('hidden');
        }
    }

    async evaluateGuidelines() {
        const factsJson = document.getElementById('patientFactsJson').value.trim();

        if (!factsJson) {
            this.showAlert('Please provide patient facts JSON', 'error');
            return;
        }

        try {
            const patientFacts = JSON.parse(factsJson);
            const result = await this.apiCall('/bcs/evaluate', 'POST', { patientFacts });

            if (result.success) {
                this.state.bcsEvaluation = result.data.evaluation;
                this.showEvaluationResults(result.data);
                this.addLog('BCS evaluation completed', 'success');
            }
        } catch (error) {
            this.showAlert(`Evaluation failed: ${error.message}`, 'error');
        }
    }

    showEvaluationResults(data) {
        const container = document.getElementById('evaluationResults');
        if (container) {
            container.textContent = JSON.stringify(data, null, 2);
            container.classList.remove('hidden');
        }
    }

    // LLM Methods
    async checkLlmStatus() {
        try {
            const result = await this.apiCall('/llm/status');

            if (result.success && result.data.enabled) {
                this.updateLlmStatus(true);
            } else {
                this.updateLlmStatus(false);
            }
        } catch (error) {
            this.addLog(`LLM status check failed: ${error.message}`, 'warning');
            this.updateLlmStatus(false);
        }
    }

    updateLlmStatus(enabled) {
        const status = document.getElementById('llmStatus');
        if (status) {
            status.className = enabled ? 'alert alert-success' : 'alert alert-error';
            status.textContent = enabled ?
                'LLM integration enabled (Claude available)' :
                'LLM integration disabled (API key not configured)';
        }

        ['narrativeApplicantBtn', 'narrativeAdminBtn', 'rationaleBtn'].forEach(id => {
            const btn = document.getElementById(id);
            if (btn) btn.disabled = !enabled;
        });
    }

    async generateNarrative(role) {
        if (this.state.messages.length === 0) {
            this.showAlert('No conversation to summarize', 'error');
            return;
        }

        try {
            const result = await this.apiCall('/llm/narrative', 'POST', {
                role,
                transcript: this.state.messages,
                patient_facts: this.state.fhirFacts,
                guidelines: this.state.guidelines
            });

            if (result.success) {
                this.showLlmResults(result.data);
                this.addLog(`Generated ${role} narrative`, 'success');
            }
        } catch (error) {
            this.showAlert(`Failed to generate narrative: ${error.message}`, 'error');
        }
    }

    async generateRationale() {
        if (!this.state.bcsEvaluation) {
            this.showAlert('Please run evaluation first', 'error');
            return;
        }

        try {
            const result = await this.apiCall('/llm/rationale', 'POST', {
                patient_facts: this.state.fhirFacts || {},
                evaluation: this.state.bcsEvaluation,
                guidelines: this.state.guidelines || {}
            });

            if (result.success) {
                this.showLlmResults(result.data);
                this.addLog('Generated guideline rationale', 'success');
            }
        } catch (error) {
            this.showAlert(`Failed to generate rationale: ${error.message}`, 'error');
        }
    }

    showLlmResults(data) {
        const container = document.getElementById('llmResults');
        if (container) {
            container.textContent = JSON.stringify(data, null, 2);
            container.classList.remove('hidden');
        }
    }

    // Stats & UI Updates
    async updateStats() {
        try {
            // Update active runs
            try {
                const runsResult = await this.apiCall('/run/list');
                if (runsResult.success) {
                    document.getElementById('activeRuns').textContent = runsResult.data.count || 0;
                    this.state.runs = runsResult.data.runs || [];
                }
            } catch (error) {
                this.addLog(`Failed to load runs: ${error.message}`, 'warning');
                document.getElementById('activeRuns').textContent = '?';
            }

            // Update messages count
            document.getElementById('messagesCount').textContent = this.state.messages.length;

            // Update scenarios loaded
            try {
                const scenariosResult = await this.apiCall('/scenario/cached');
                if (scenariosResult.success) {
                    document.getElementById('scenariosLoaded').textContent = scenariosResult.data.count || 0;
                }
            } catch (error) {
                this.addLog(`Failed to load scenarios: ${error.message}`, 'warning');
                document.getElementById('scenariosLoaded').textContent = '?';
            }

            // Update agents connected
            try {
                const agentsResult = await this.apiCall('/agentcard/cached');
                if (agentsResult.success) {
                    document.getElementById('agentsConnected').textContent = agentsResult.data.count || 0;
                }
            } catch (error) {
                this.addLog(`Failed to load agent cards: ${error.message}`, 'warning');
                document.getElementById('agentsConnected').textContent = '?';
            }
        } catch (error) {
            this.addLog(`Stats update failed: ${error.message}`, 'error');
            console.error('Failed to update stats:', error);
        }
    }

    async cleanup() {
        try {
            const result = await this.apiCall('/cleanup', 'POST', { maxAgeHours: 24 });

            if (result.success) {
                this.showAlert('Old runs cleaned up successfully', 'success');
                await this.updateStats();
                this.addLog('Cleanup completed', 'info');
            }
        } catch (error) {
            this.showAlert(`Cleanup failed: ${error.message}`, 'error');
        }
    }

    // Logging
    addLog(message, type = 'info') {
        const log = {
            timestamp: new Date().toLocaleTimeString(),
            message,
            type
        };

        this.state.logs.push(log);
        this.updateLogsDisplay();

        // Show toast for important messages
        if (type === 'error' || type === 'success' || type === 'warning') {
            this.showToast(message, type);
        }
    }

    updateLogsDisplay() {
        const container = document.getElementById('logsContainer');
        if (container) {
            const logs = this.state.logs.slice(-100); // Keep last 100 logs
            container.innerHTML = logs.map(log => {
                const color = {
                    'success': '#22c55e',
                    'error': '#ef4444',
                    'warning': '#f59e0b',
                    'info': '#6b7280'
                }[log.type] || '#6b7280';

                return `<div style="color: ${color}">[${log.timestamp}] ${log.message}</div>`;
            }).join('');

            container.scrollTop = container.scrollHeight;
        }
    }

    clearLogs() {
        this.state.logs = [];
        this.updateLogsDisplay();
        this.addLog('Logs cleared', 'info');
    }

    // Utility Methods
    setLoading(elementId, loading) {
        const element = document.getElementById(elementId);
        if (element) {
            if (loading) {
                element.classList.remove('hidden');
            } else {
                element.classList.add('hidden');
            }
        }
    }

    showAlert(message, type = 'info', containerId = null) {
        if (containerId) {
            const container = document.getElementById(containerId);
            if (container) {
                container.className = `alert alert-${type}`;
                container.textContent = message;
                container.classList.remove('hidden');
            }
        } else {
            // Show toast if no container specified
            this.showToast(message, type);
        }
    }

    escapeHtml(text) {
        if (typeof text !== 'string') return String(text);
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    updateStatus(text, type = 'online') {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');

        if (statusDot) {
            statusDot.className = `status-dot ${type}`;
        }

        if (statusText) {
            statusText.textContent = text;
        }
    }
}

// Initialize on page load
let banteropInstance;
document.addEventListener('DOMContentLoaded', () => {
    banteropInstance = new BanteropV2();

    // Make instance globally available for onclick handlers
    window.banteropApp = banteropInstance;
    // Backwards compatibility for cached HTML or legacy references
    window.BanteropV2 = banteropInstance;
    console.log('BanteropV2 initialized as window.banteropApp and window.BanteropV2');
});