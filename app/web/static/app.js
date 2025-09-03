// Multi-Agent Interoperability Demo - Frontend Application
class MultiAgentDemo {
    constructor() {
        this.socket = null;
        this.currentProtocol = 'a2a';
        this.activeSession = null;
        this.conversations = [];
        
        this.init();
    }
    
    init() {
        this.initializeSocket();
        this.bindEventListeners();
        this.loadConversations();
        
        console.log('Multi-Agent Demo initialized');
    }
    
    initializeSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.updateStatus('Connected to server', 'success');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.updateStatus('Disconnected from server', 'warning');
        });
        
        this.socket.on('connected', (data) => {
            this.currentProtocol = data.protocol;
            this.updateProtocolDisplay();
        });
        
        this.socket.on('protocol_changed', (data) => {
            this.currentProtocol = data.protocol;
            this.updateProtocolDisplay();
            this.updateStatus(`Protocol switched to ${data.protocol.toUpperCase()}`, 'info');
        });
        
        this.socket.on('conversation_started', (data) => {
            this.handleConversationStarted(data);
        });
        
        this.socket.on('message_response', (data) => {
            this.handleMessageResponse(data);
        });
        
        this.socket.on('error', (data) => {
            console.error('Socket error:', data);
            this.updateStatus(`Error: ${data.message}`, 'error');
        });
    }
    
    bindEventListeners() {
        // Protocol switching
        document.getElementById('switch-protocol-btn').addEventListener('click', () => {
            this.switchProtocol();
        });
        
        // Start conversation
        document.getElementById('start-conversation-btn').addEventListener('click', () => {
            this.startConversation();
        });
        
        // Send message
        document.getElementById('send-message-btn').addEventListener('click', () => {
            this.sendMessage();
        });
        
        // Enter key for message input
        document.getElementById('message-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
        
        // Protocol radio buttons
        document.querySelectorAll('input[name="protocol"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.currentProtocol = e.target.value;
                }
            });
        });
    }
    
    switchProtocol() {
        const selectedProtocol = document.querySelector('input[name="protocol"]:checked').value;
        
        fetch('/api/protocol', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                protocol: selectedProtocol
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.currentProtocol = data.protocol;
                this.updateProtocolDisplay();
                this.updateStatus(`Switched to ${data.protocol.toUpperCase()} protocol`, 'success');
            } else {
                this.updateStatus(`Failed to switch protocol: ${data.error}`, 'error');
            }
        })
        .catch(error => {
            console.error('Error switching protocol:', error);
            this.updateStatus('Error switching protocol', 'error');
        });
    }
    
    startConversation() {
        const scenario = document.getElementById('scenario-select').value;
        const startBtn = document.getElementById('start-conversation-btn');
        
        startBtn.disabled = true;
        startBtn.innerHTML = '<i data-feather="loader" class="me-2"></i>Starting...';
        feather.replace();
        
        fetch('/api/start_conversation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                scenario: scenario
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.updateStatus('Conversation started successfully', 'success');
                this.enableMessageInput();
            } else {
                this.updateStatus(`Failed to start conversation: ${data.error}`, 'error');
            }
        })
        .catch(error => {
            console.error('Error starting conversation:', error);
            this.updateStatus('Error starting conversation', 'error');
        })
        .finally(() => {
            startBtn.disabled = false;
            startBtn.innerHTML = '<i data-feather="play" class="me-2"></i>Start Conversation';
            feather.replace();
        });
    }
    
    sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        
        if (!message) return;
        
        this.socket.emit('send_message', {
            message: message,
            sender: 'user'
        });
        
        // Add user message to display immediately
        this.addMessageToDisplay('user', message, 'user_message');
        
        messageInput.value = '';
    }
    
    handleConversationStarted(data) {
        this.activeSession = data.result.session_id;
        this.clearConversationDisplay();
        
        // Display initial exchange based on protocol
        if (data.protocol === 'a2a') {
            this.displayA2AExchange(data.result.initial_exchange);
        } else {
            this.displayMCPExchange(data.result.initial_exchange);
        }
        
        this.enableMessageInput();
        this.loadArtifacts();
    }
    
    handleMessageResponse(data) {
        if (data.protocol === 'a2a') {
            this.displayA2AMessage(data);
        } else {
            this.displayMCPMessage(data);
        }
        
        this.loadArtifacts();
    }
    
    displayA2AExchange(exchange) {
        // Display applicant request
        this.addMessageToDisplay('applicant', JSON.stringify(exchange.applicant_request, null, 2), 'json_message');
        
        // Display applicant response
        this.addMessageToDisplay('applicant', JSON.stringify(exchange.applicant_response, null, 2), 'json_message');
        
        // Display admin response
        this.addMessageToDisplay('administrator', JSON.stringify(exchange.admin_response, null, 2), 'json_message');
    }
    
    displayMCPExchange(exchange) {
        // Display eligibility call
        this.addMessageToDisplay('applicant', JSON.stringify(exchange.eligibility_call, null, 2), 'tool_call');
        
        // Display applicant response
        this.addMessageToDisplay('applicant', JSON.stringify(exchange.applicant_response, null, 2), 'tool_response');
        
        // Display process call
        this.addMessageToDisplay('administrator', JSON.stringify(exchange.process_call, null, 2), 'tool_call');
        
        // Display admin response
        this.addMessageToDisplay('administrator', JSON.stringify(exchange.admin_response, null, 2), 'tool_response');
    }
    
    displayA2AMessage(data) {
        // Display the JSON-RPC request
        this.addMessageToDisplay(data.agent, JSON.stringify(data.request, null, 2), 'json_message');
        
        // Display the JSON-RPC response
        this.addMessageToDisplay(data.agent, JSON.stringify(data.response, null, 2), 'json_message');
    }
    
    displayMCPMessage(data) {
        if (data.tool_call) {
            this.addMessageToDisplay(data.agent, JSON.stringify(data.tool_call, null, 2), 'tool_call');
        }
        
        if (data.response) {
            this.addMessageToDisplay(data.agent, JSON.stringify(data.response, null, 2), 'tool_response');
        }
    }
    
    addMessageToDisplay(agent, content, type) {
        const conversationDisplay = document.getElementById('conversation-display');
        
        // Remove empty state if present
        const emptyState = conversationDisplay.querySelector('.text-center.text-muted');
        if (emptyState) {
            emptyState.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${agent}-message mb-3`;
        
        const timestamp = new Date().toLocaleTimeString();
        
        let icon = 'user';
        let badgeClass = 'bg-secondary';
        
        if (agent === 'applicant') {
            icon = 'user-check';
            badgeClass = 'bg-primary';
        } else if (agent === 'administrator') {
            icon = 'shield-check';
            badgeClass = 'bg-success';
        }
        
        let contentHTML = '';
        if (type === 'json_message' || type === 'tool_call' || type === 'tool_response') {
            contentHTML = `<pre class="bg-dark p-2 rounded"><code>${this.escapeHtml(content)}</code></pre>`;
        } else {
            contentHTML = `<p class="mb-0">${this.escapeHtml(content)}</p>`;
        }
        
        messageDiv.innerHTML = `
            <div class="d-flex align-items-start">
                <div class="me-3">
                    <i data-feather="${icon}" class="text-muted"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center mb-2">
                        <span class="badge ${badgeClass} me-2">${agent.charAt(0).toUpperCase() + agent.slice(1)}</span>
                        <small class="text-muted">${timestamp}</small>
                        ${type !== 'user_message' ? `<span class="badge bg-info ms-2">${this.currentProtocol.toUpperCase()}</span>` : ''}
                    </div>
                    ${contentHTML}
                </div>
            </div>
        `;
        
        conversationDisplay.appendChild(messageDiv);
        conversationDisplay.scrollTop = conversationDisplay.scrollHeight;
        
        // Re-initialize Feather icons
        feather.replace();
    }
    
    clearConversationDisplay() {
        const conversationDisplay = document.getElementById('conversation-display');
        conversationDisplay.innerHTML = '';
    }
    
    enableMessageInput() {
        document.getElementById('message-input').disabled = false;
        document.getElementById('send-message-btn').disabled = false;
    }
    
    disableMessageInput() {
        document.getElementById('message-input').disabled = true;
        document.getElementById('send-message-btn').disabled = true;
    }
    
    loadConversations() {
        fetch('/api/conversations')
        .then(response => response.json())
        .then(data => {
            this.conversations = data;
            this.updateConversationsList();
        })
        .catch(error => {
            console.error('Error loading conversations:', error);
        });
    }
    
    loadArtifacts() {
        // Mock artifacts for demonstration
        const artifactsDisplay = document.getElementById('artifacts-display');
        
        if (this.activeSession) {
            artifactsDisplay.innerHTML = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-header">
                                <h6 class="card-title mb-0">
                                    <i data-feather="file-text" class="me-2"></i>
                                    Patient Data
                                </h6>
                            </div>
                            <div class="card-body">
                                <p class="card-text">Patient ID: 001</p>
                                <p class="card-text">Name: Sarah Johnson</p>
                                <p class="card-text">Status: Active Application</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="card">
                            <div class="card-header">
                                <h6 class="card-title mb-0">
                                    <i data-feather="check-circle" class="me-2"></i>
                                    Eligibility Result
                                </h6>
                            </div>
                            <div class="card-body">
                                <p class="card-text">BCSE Eligibility: <span class="badge bg-success">Approved</span></p>
                                <p class="card-text">Score: 85/100</p>
                                <p class="card-text">Protocol: ${this.currentProtocol.toUpperCase()}</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            feather.replace();
        }
    }
    
    updateProtocolDisplay() {
        document.getElementById('current-protocol').textContent = this.currentProtocol.toUpperCase();
        document.querySelector(`input[value="${this.currentProtocol}"]`).checked = true;
    }
    
    updateStatus(message, type) {
        const toast = document.getElementById('status-toast');
        const toastBody = toast.querySelector('.toast-body');
        
        let icon = 'info';
        let bgClass = 'bg-info';
        
        switch (type) {
            case 'success':
                icon = 'check-circle';
                bgClass = 'bg-success';
                break;
            case 'warning':
                icon = 'alert-triangle';
                bgClass = 'bg-warning';
                break;
            case 'error':
                icon = 'alert-circle';
                bgClass = 'bg-danger';
                break;
        }
        
        toast.className = `toast ${bgClass} text-white`;
        toast.querySelector('i').setAttribute('data-feather', icon);
        toastBody.textContent = message;
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        feather.replace();
        
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
    
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    }
}

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.multiAgentDemo = new MultiAgentDemo();
});
