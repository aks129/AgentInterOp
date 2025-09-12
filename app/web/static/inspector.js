// A2A Inspector - Simplified JavaScript version
console.log("A2A Inspector initialized");

class A2AInspector {
    constructor() {
        this.baseUrl = window.location.origin;
        this.ws = null;
        this.clientId = this.generateUUID();
        this.connected = false;
    }

    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    init() {
        this.setupEventListeners();
        this.setupWebSocket();
        this.setDefaultUrl();
    }

    setDefaultUrl() {
        const urlInput = document.getElementById('agent-card-url');
        if (urlInput) {
            urlInput.value = this.baseUrl;
        }
    }

    setupEventListeners() {
        const connectBtn = document.getElementById('connect-btn');
        const clearConsoleBtn = document.getElementById('clear-console-btn');
        const toggleConsoleBtn = document.getElementById('toggle-console-btn');
        const sendBtn = document.getElementById('send-btn');
        const messageInput = document.getElementById('message-input');

        if (connectBtn) {
            connectBtn.addEventListener('click', () => this.connectToAgent());
        }

        if (clearConsoleBtn) {
            clearConsoleBtn.addEventListener('click', () => this.clearConsole());
        }

        if (toggleConsoleBtn) {
            toggleConsoleBtn.addEventListener('click', () => this.toggleConsole());
        }

        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }

        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });
        }

        // Setup collapsible headers
        this.setupCollapsibleHeaders();
    }

    setupCollapsibleHeaders() {
        const headers = document.querySelectorAll('.collapsible-header');
        headers.forEach(header => {
            header.addEventListener('click', () => {
                const content = header.nextElementSibling;
                const icon = header.querySelector('.toggle-icon');
                
                if (content.style.display === 'none') {
                    content.style.display = 'block';
                    icon.textContent = '▼';
                } else {
                    content.style.display = 'none';
                    icon.textContent = '►';
                }
            });
        });
    }

    setupWebSocket() {
        try {
            const wsUrl = `ws://${window.location.host}/inspectortest/ws/${this.clientId}`;
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.connected = true;
            };

            this.ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleWebSocketMessage(message);
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.connected = false;
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.logDebug('WebSocket Error', { error: error.toString() });
            };
        } catch (error) {
            console.error('Failed to setup WebSocket:', error);
            this.logDebug('WebSocket Setup Error', { error: error.toString() });
        }
    }

    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'agent_card_response':
                this.handleAgentCardResponse(message);
                break;
            case 'validation_result':
                this.handleValidationResult(message);
                break;
            case 'message_response':
                this.handleMessageResponse(message);
                break;
            default:
                console.log('Unknown message type:', message.type);
        }
    }

    connectToAgent() {
        const urlInput = document.getElementById('agent-card-url');
        const connectBtn = document.getElementById('connect-btn');
        
        if (!urlInput || !connectBtn) return;
        
        const baseUrl = urlInput.value.trim();
        if (!baseUrl) {
            this.showError('Please enter a valid base URL');
            return;
        }

        connectBtn.textContent = 'Connecting...';
        connectBtn.disabled = true;

        // Send fetch agent card request
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'fetch_agent_card',
                base_url: baseUrl
            }));
        } else {
            // Fallback to HTTP request
            this.fetchAgentCardHTTP(baseUrl);
        }
    }

    async fetchAgentCardHTTP(baseUrl) {
        try {
            const cardUrl = `${baseUrl}/.well-known/agent-card.json`;
            const response = await fetch(cardUrl);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const agentCard = await response.json();
            
            this.handleAgentCardResponse({
                success: true,
                data: agentCard,
                debug: {
                    type: 'agent_card_fetch',
                    request: { method: 'GET', url: cardUrl },
                    response: { status_code: response.status, body: agentCard }
                }
            });
            
            // Perform validation
            const validation = this.validateAgentCard(agentCard);
            this.handleValidationResult({
                success: true,
                data: validation
            });
            
        } catch (error) {
            this.handleAgentCardResponse({
                success: false,
                error: error.toString()
            });
        } finally {
            const connectBtn = document.getElementById('connect-btn');
            if (connectBtn) {
                connectBtn.textContent = 'Connect';
                connectBtn.disabled = false;
            }
        }
    }

    handleAgentCardResponse(message) {
        const connectBtn = document.getElementById('connect-btn');
        if (connectBtn) {
            connectBtn.textContent = 'Connect';
            connectBtn.disabled = false;
        }

        if (message.success) {
            this.displayAgentCard(message.data);
            if (message.debug) {
                this.logDebug('Agent Card Fetch', message.debug);
            }
        } else {
            this.showError(`Failed to fetch agent card: ${message.error}`);
        }
    }

    displayAgentCard(card) {
        const cardContent = document.getElementById('agent-card-content');
        if (cardContent) {
            cardContent.textContent = JSON.stringify(card, null, 2);
            // Apply syntax highlighting if available
            if (typeof hljs !== 'undefined') {
                hljs.highlightElement(cardContent);
            }
        }
    }

    handleValidationResult(message) {
        if (!message.success) return;

        const validation = message.data;
        const errorsDiv = document.getElementById('validation-errors');
        
        if (!errorsDiv) return;

        let html = `<div class="validation-summary ${validation.valid ? 'valid' : 'invalid'}">`;
        html += `<h3>${validation.valid ? '✅' : '❌'} Validation ${validation.valid ? 'Passed' : 'Failed'}</h3>`;
        html += `<p>Score: ${validation.score}/100</p>`;
        
        if (validation.issues.length > 0) {
            html += '<h4>Issues:</h4><ul>';
            validation.issues.forEach(issue => {
                html += `<li class="error">❌ ${issue}</li>`;
            });
            html += '</ul>';
        }
        
        if (validation.warnings.length > 0) {
            html += '<h4>Warnings:</h4><ul>';
            validation.warnings.forEach(warning => {
                html += `<li class="warning">⚠️ ${warning}</li>`;
            });
            html += '</ul>';
        }
        
        html += '</div>';
        errorsDiv.innerHTML = html;
    }

    sendMessage() {
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        
        if (!messageInput || !sendBtn) return;
        
        const message = messageInput.value.trim();
        if (!message) return;

        const urlInput = document.getElementById('agent-card-url');
        const baseUrl = urlInput ? urlInput.value.trim() : this.baseUrl;

        // Add message to chat
        this.addChatMessage('user', message);
        
        // Clear input and disable send button
        messageInput.value = '';
        sendBtn.disabled = true;
        sendBtn.textContent = 'Sending...';

        // Send via WebSocket if available, otherwise use HTTP
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'send_message',
                base_url: baseUrl,
                message: message
            }));
        } else {
            this.sendMessageHTTP(baseUrl, message);
        }
    }

    async sendMessageHTTP(baseUrl, message) {
        try {
            const a2aUrl = `${baseUrl}/api/bridge/demo/a2a`;
            const payload = {
                jsonrpc: '2.0',
                id: this.generateUUID(),
                method: 'message/send',
                params: {
                    content: message,
                    metadata: { inspector: true }
                }
            };

            const response = await fetch(a2aUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const responseData = await response.json();

            this.handleMessageResponse({
                success: true,
                data: responseData,
                debug: {
                    type: 'message_send',
                    request: { method: 'POST', url: a2aUrl, body: payload },
                    response: { status_code: response.status, body: responseData }
                }
            });

        } catch (error) {
            this.handleMessageResponse({
                success: false,
                error: error.toString()
            });
        } finally {
            const sendBtn = document.getElementById('send-btn');
            if (sendBtn) {
                sendBtn.textContent = 'Send';
                sendBtn.disabled = false;
            }
        }
    }

    handleMessageResponse(message) {
        const sendBtn = document.getElementById('send-btn');
        if (sendBtn) {
            sendBtn.textContent = 'Send';
            sendBtn.disabled = false;
        }

        if (message.success) {
            // Extract and display agent response
            const responseData = message.data;
            if (responseData.result) {
                const agentMessage = this.extractMessageFromResult(responseData.result);
                this.addChatMessage('agent', agentMessage, true);
            }
            
            if (message.debug) {
                this.logDebug('Message Send', message.debug);
            }
        } else {
            this.addChatMessage('system', `Error: ${message.error}`, false);
            this.showError(`Failed to send message: ${message.error}`);
        }
    }

    extractMessageFromResult(result) {
        if (result.history && result.history.length > 0) {
            const lastMessage = result.history[result.history.length - 1];
            if (lastMessage.parts && lastMessage.parts.length > 0) {
                return lastMessage.parts[0].text || 'Message received';
            }
        }
        return 'Task created successfully';
    }

    addChatMessage(sender, content, compliant = null) {
        const messagesDiv = document.getElementById('messages');
        if (!messagesDiv) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const icon = sender === 'user' ? '👤' : sender === 'agent' ? (compliant ? '✅' : '⚠️') : '🔧';
        const timestamp = new Date().toLocaleTimeString();
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="message-icon">${icon}</span>
                <span class="message-sender">${sender}</span>
                <span class="message-time">${timestamp}</span>
            </div>
            <div class="message-content">${content}</div>
        `;
        
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    validateAgentCard(card) {
        const issues = [];
        const warnings = [];

        // Required fields
        const requiredFields = ['name', 'description', 'version', 'capabilities'];
        requiredFields.forEach(field => {
            if (!card[field]) {
                issues.push(`Missing required field: ${field}`);
            }
        });

        // Endpoints validation
        if (!card.endpoints) {
            issues.push('Missing endpoints field');
        } else if (!card.endpoints.jsonrpc) {
            warnings.push('Missing jsonrpc endpoint - required for A2A protocol');
        }

        // Skills validation
        if (card.skills) {
            if (!Array.isArray(card.skills)) {
                issues.push('Skills must be an array');
            } else {
                card.skills.forEach((skill, i) => {
                    if (!skill.id) {
                        issues.push(`Skill ${i} missing required id field`);
                    }
                });
            }
        }

        return {
            valid: issues.length === 0,
            issues: issues,
            warnings: warnings,
            score: Math.max(0, 100 - issues.length * 20 - warnings.length * 5)
        };
    }

    logDebug(type, data) {
        const debugContent = document.getElementById('debug-content');
        if (!debugContent) return;

        const logEntry = document.createElement('div');
        logEntry.className = 'debug-entry';
        logEntry.innerHTML = `
            <div class="debug-header">
                <span class="debug-type">${type}</span>
                <span class="debug-time">${new Date().toLocaleTimeString()}</span>
            </div>
            <pre class="debug-data">${JSON.stringify(data, null, 2)}</pre>
        `;
        
        debugContent.appendChild(logEntry);
        debugContent.scrollTop = debugContent.scrollHeight;
    }

    clearConsole() {
        const debugContent = document.getElementById('debug-content');
        if (debugContent) {
            debugContent.innerHTML = '';
        }
    }

    toggleConsole() {
        const debugContent = document.getElementById('debug-content');
        const toggleBtn = document.getElementById('toggle-console-btn');
        
        if (!debugContent || !toggleBtn) return;

        if (debugContent.style.display === 'none') {
            debugContent.style.display = 'block';
            toggleBtn.textContent = 'Hide';
        } else {
            debugContent.style.display = 'none';
            toggleBtn.textContent = 'Show';
        }
    }

    showError(message) {
        console.error(message);
        // You could add a toast notification here
        alert(message);
    }
}

// Initialize the inspector when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const inspector = new A2AInspector();
    inspector.init();
    window.inspector = inspector; // Make it globally accessible for debugging
});