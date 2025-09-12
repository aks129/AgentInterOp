// A2A Inspector - Simplified JavaScript version
console.log("A2A Inspector initialized");

class A2AInspector {
    constructor() {
        this.baseUrl = window.location.origin;
        this.ws = null;
        this.clientId = this.generateUUID();
        this.connected = false;
        this.currentTaskId = null; // Track current conversation task ID
        this.currentAgentCard = null; // Store fetched agent card
        this.currentA2aEndpoint = null; // Store A2A endpoint from agent card
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
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/inspectortest/ws/${this.clientId}`;
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
            // Handle case where user enters full agent card URL instead of base URL
            let cleanBaseUrl = baseUrl;
            if (baseUrl.includes('/.well-known/agent-card.json')) {
                cleanBaseUrl = baseUrl.split('/.well-known/agent-card.json')[0];
                console.log(`Detected full agent card URL, using base: ${cleanBaseUrl}`);
            }
            
            const cardUrl = `${cleanBaseUrl}/.well-known/agent-card.json`;
            console.log(`Attempting to fetch agent card from: ${cardUrl}`);
            
            const response = await fetch(cardUrl, {
                method: 'GET',
                mode: 'cors',  // Explicitly set CORS mode
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            console.log(`Response status: ${response.status} ${response.statusText}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const agentCard = await response.json();
            console.log('Successfully fetched agent card:', agentCard);
            
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
            console.error('Direct agent card fetch failed:', error);
            
            // Try proxy fallback for CORS issues
            if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                console.log('Attempting proxy fallback for CORS issue...');
                try {
                    await this.fetchAgentCardViaProxy(baseUrl);  // Pass baseUrl, not cardUrl
                    return; // Success via proxy, exit here
                } catch (proxyError) {
                    console.error('Proxy fallback also failed:', proxyError);
                }
            }
            
            // Provide more specific error messages
            let errorMessage = error.toString();
            if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                errorMessage = `CORS Error: Unable to fetch from ${baseUrl}. Both direct fetch and proxy fallback failed.\n\nThis usually means:\n1. The server doesn't allow cross-origin requests\n2. Network connectivity issues\n3. SSL certificate problems\n\nTry:\n- Checking if the URL is correct\n- Testing in a different browser`;
            } else if (error.message.includes('HTTP 404')) {
                errorMessage = `Not Found: The agent card endpoint ${baseUrl}/.well-known/agent-card.json doesn't exist.`;
            } else if (error.message.includes('HTTP 403')) {
                errorMessage = `Forbidden: Access denied to ${baseUrl}/.well-known/agent-card.json`;
            } else if (error.message.includes('HTTP 500')) {
                errorMessage = `Server Error: The target server returned an error. Try again later.`;
            }
            
            this.handleAgentCardResponse({
                success: false,
                error: errorMessage
            });
        } finally {
            const connectBtn = document.getElementById('connect-btn');
            if (connectBtn) {
                connectBtn.textContent = 'Connect';
                connectBtn.disabled = false;
            }
        }
    }

    async fetchAgentCardViaProxy(baseUrl) {
        const proxyUrl = `${window.location.origin}/api/proxy/agent-card?url=${encodeURIComponent(baseUrl)}`;
        console.log(`Fetching via proxy: ${proxyUrl}`);
        
        const response = await fetch(proxyUrl);
        const result = await response.json();
        
        if (result.success) {
            console.log('Successfully fetched agent card via proxy:', result.data);
            
            this.handleAgentCardResponse({
                success: true,
                data: result.data,
                debug: {
                    type: 'agent_card_fetch_proxy',
                    request: { method: 'GET', url: result.url, via_proxy: true },
                    response: { status_code: result.status_code, body: result.data }
                }
            });
            
            // Perform validation
            const validation = this.validateAgentCard(result.data);
            this.handleValidationResult({
                success: true,
                data: validation
            });
        } else {
            throw new Error(result.error || 'Proxy request failed');
        }
    }

    handleAgentCardResponse(message) {
        const connectBtn = document.getElementById('connect-btn');
        if (connectBtn) {
            connectBtn.textContent = 'Connect';
            connectBtn.disabled = false;
        }

        if (message.success) {
            // Store the agent card and extract A2A endpoint
            this.currentAgentCard = message.data;
            this.currentA2aEndpoint = this.extractA2aEndpoint(message.data);
            
            console.log(`🎯 Successfully fetched agent card`);
            console.log(`🔗 Extracted A2A endpoint: "${this.currentA2aEndpoint}"`);
            console.log(`🏷️ Agent name: "${message.data.name}"`);
            
            this.displayAgentCard(message.data);
            
            // Enable chat interface
            this.enableChatInterface();
            
            if (message.debug) {
                this.logDebug('Agent Card Fetch', message.debug);
            }
        } else {
            this.showError(`Failed to fetch agent card: ${message.error}`);
        }
    }
    
    extractA2aEndpoint(agentCard) {
        // Try different ways to get the A2A endpoint from the agent card
        console.log('🔍 Extracting A2A endpoint from agent card...');
        
        // Method 1: Direct url field (common in newer specs)
        if (agentCard.url) {
            console.log(`✅ Found A2A endpoint via url field: ${agentCard.url}`);
            return agentCard.url;
        }
        
        // Method 2: endpoints.jsonrpc (older spec format)
        if (agentCard.endpoints && agentCard.endpoints.jsonrpc) {
            console.log(`✅ Found A2A endpoint via endpoints.jsonrpc: ${agentCard.endpoints.jsonrpc}`);
            return agentCard.endpoints.jsonrpc;
        }
        
        // Method 3: skills discovery URL (newer spec format)
        if (agentCard.skills && Array.isArray(agentCard.skills)) {
            for (const skill of agentCard.skills) {
                if (skill.discovery && skill.discovery.url) {
                    console.log(`✅ Found A2A endpoint via skills discovery: ${skill.discovery.url}`);
                    return skill.discovery.url;
                }
            }
        }
        
        // Method 4: additionalInterfaces
        if (agentCard.additionalInterfaces && Array.isArray(agentCard.additionalInterfaces)) {
            const jsonrpcInterface = agentCard.additionalInterfaces.find(
                iface => iface.transport === 'JSONRPC' || iface.transport === 'jsonrpc'
            );
            if (jsonrpcInterface && jsonrpcInterface.url) {
                console.log(`✅ Found A2A endpoint via additionalInterfaces: ${jsonrpcInterface.url}`);
                return jsonrpcInterface.url;
            }
        }
        
        // Fallback: return null to indicate no endpoint found
        console.log('❌ No A2A endpoint found in agent card');
        return null;
    }

    enableChatInterface() {
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        
        // Reset conversation state when enabling chat
        this.currentTaskId = null;
        this.clearMessages();
        
        if (messageInput) {
            messageInput.disabled = false;
            messageInput.placeholder = 'Type a message to send to the agent...';
        }
        
        if (sendBtn) {
            sendBtn.disabled = false;
        }
    }

    clearMessages() {
        const messagesDiv = document.getElementById('messages');
        if (messagesDiv) {
            messagesDiv.innerHTML = '';
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
            // Determine the A2A endpoint to use
            let a2aUrl;
            
            if (this.currentA2aEndpoint) {
                // Use the endpoint from the agent card
                a2aUrl = this.currentA2aEndpoint;
                console.log(`Using agent card endpoint: ${a2aUrl}`);
            } else {
                // Fallback to our local demo endpoint
                a2aUrl = `${baseUrl}/api/bridge/demo/a2a`;
                console.log(`Using local demo endpoint: ${a2aUrl}`);
            }
            
            const payload = {
                jsonrpc: '2.0',
                id: this.generateUUID(),
                method: 'message/send',
                params: {
                    message: {
                        parts: [{ kind: 'text', text: message }]
                    }
                }
            };

            // Add taskId if we have a current conversation
            if (this.currentTaskId) {
                payload.params.message.taskId = this.currentTaskId;
            }

            console.log(`Sending message to: ${a2aUrl}`);
            console.log('Payload:', payload);

            const response = await fetch(a2aUrl, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                mode: 'cors',
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const responseData = await response.json();
            console.log('Response received:', responseData);

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
            console.error('Direct message send failed:', error);
            console.log(`Error type: ${error.name}, message: ${error.message}`);
            console.log(`Current A2A endpoint: ${this.currentA2aEndpoint}`);
            console.log(`Target URL was: ${a2aUrl}`);
            console.log(`Full error object:`, error);
            
            // Try proxy fallback for CORS issues with external agents
            if (error.name === 'TypeError' && error.message.includes('Failed to fetch') && this.currentA2aEndpoint) {
                console.log('✅ CORS detected - attempting message proxy fallback...');
                console.log(`📤 Proxy fallback: sending to ${a2aUrl} via proxy`);
                try {
                    await this.sendMessageViaProxy(a2aUrl, payload);
                    console.log('🎉 Proxy fallback succeeded! Message sent successfully.');
                    return; // Success via proxy, exit here
                } catch (proxyError) {
                    console.error('❌ Proxy message fallback also failed:', proxyError);
                    console.error('Proxy error details:', proxyError.message);
                    console.error('Full proxy error object:', proxyError);
                    console.error('Proxy error stack:', proxyError.stack);
                }
            } else {
                console.log('❌ Proxy fallback conditions not met:');
                console.log(`- Is TypeError? ${error.name === 'TypeError'}`);
                console.log(`- Contains "Failed to fetch"? ${error.message.includes('Failed to fetch')}`);
                console.log(`- Has currentA2aEndpoint? ${!!this.currentA2aEndpoint}`);
                console.log(`- Current A2A endpoint value: "${this.currentA2aEndpoint}"`);
                console.log(`- Full condition check: ${error.name === 'TypeError' && error.message.includes('Failed to fetch') && this.currentA2aEndpoint}`);
            }
            
            // Provide more specific error messages
            let errorMessage = error.toString();
            if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                if (this.currentA2aEndpoint) {
                    errorMessage = `CORS Error: Unable to send message to external agent. Both direct fetch and proxy fallback failed.`;
                } else {
                    errorMessage = `Network Error: Unable to send message to the agent endpoint.`;
                }
            } else if (error.message.includes('HTTP 404')) {
                errorMessage = `Not Found: The agent endpoint doesn't exist or is not configured correctly.`;
            } else if (error.message.includes('HTTP 403')) {
                errorMessage = `Forbidden: Access denied to the agent endpoint.`;
            } else if (error.message.includes('HTTP 500')) {
                errorMessage = `Server Error: The agent returned an error. Try again later.`;
            }
            
            this.handleMessageResponse({
                success: false,
                error: errorMessage
            });
        } finally {
            const sendBtn = document.getElementById('send-btn');
            if (sendBtn) {
                sendBtn.textContent = 'Send';
                sendBtn.disabled = false;
            }
        }
    }

    async sendMessageViaProxy(targetUrl, payload) {
        const proxyUrl = `${window.location.origin}/api/proxy/a2a-message`;
        console.log(`Sending message via proxy:`);
        console.log(`- Proxy URL: ${proxyUrl}`);
        console.log(`- Target URL: ${targetUrl}`);
        console.log(`- Payload:`, payload);
        
        const requestBody = {
            target_url: targetUrl,
            payload: payload
        };
        
        console.log('Full proxy request body:', requestBody);
        
        const response = await fetch(proxyUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        console.log(`📡 Proxy response status: ${response.status}`);
        console.log(`📡 Proxy response ok: ${response.ok}`);

        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch (jsonError) {
                console.error('Failed to parse proxy error response as JSON:', jsonError);
                const errorText = await response.text();
                console.error('Proxy error response text:', errorText);
                throw new Error(`Proxy error: ${response.status} - ${errorText}`);
            }
            console.error('🔥 Proxy error response:', errorData);
            throw new Error(errorData.detail || `Proxy error: ${response.status}`);
        }

        let result;
        try {
            result = await response.json();
        } catch (jsonError) {
            console.error('Failed to parse proxy success response as JSON:', jsonError);
            const responseText = await response.text();
            console.error('Proxy response text:', responseText);
            throw new Error('Invalid JSON response from proxy');
        }
        
        console.log('📦 Proxy response result:', result);
        console.log(`📦 Proxy success status: ${result.success}`);
        
        if (result.success) {
            console.log('🎉 Successfully sent message via proxy!');
            console.log('📨 Response data:', result.data);
            
            this.handleMessageResponse({
                success: true,
                data: result.data,
                debug: {
                    type: 'message_send_proxy',
                    request: { method: 'POST', url: targetUrl, body: payload, via_proxy: true },
                    response: { status_code: result.status_code, body: result.data }
                }
            });
        } else {
            console.error('❌ Proxy returned unsuccessful result:');
            console.error('❌ Result object:', result);
            throw new Error(result.error || result.data || 'Proxy request failed');
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
                // Store the task ID for subsequent messages
                if (responseData.result.id) {
                    this.currentTaskId = responseData.result.id;
                }
                
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

        // Endpoints validation - check both standard endpoints field and skills discovery
        let hasJsonrpcEndpoint = false;
        
        if (card.endpoints && card.endpoints.jsonrpc) {
            hasJsonrpcEndpoint = true;
        }
        
        // Also check skills for discovery URLs (newer spec format)
        if (card.skills && Array.isArray(card.skills)) {
            for (const skill of card.skills) {
                if (skill.discovery && skill.discovery.url) {
                    hasJsonrpcEndpoint = true;
                    break;
                }
            }
        }
        
        if (!hasJsonrpcEndpoint) {
            if (!card.endpoints) {
                issues.push('Missing endpoints field or skills with discovery URLs');
            } else if (!card.endpoints.jsonrpc) {
                warnings.push('Missing jsonrpc endpoint - required for A2A protocol');
            }
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