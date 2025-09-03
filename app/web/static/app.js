// Multi-Agent Demo JavaScript
console.log("Multi-Agent Demo initialized");

// Global state
let currentProtocol = 'A2A';
let conversationId = null;
let eventSource = null;
let artifacts = [];

// DOM elements
const transcriptElement = document.getElementById('transcript');
const artifactsElement = document.getElementById('artifacts');
const startDemoBtn = document.getElementById('start-demo-btn');
const sendApplicantInfoBtn = document.getElementById('send-applicant-info-btn');
const resetBtn = document.getElementById('reset-btn');

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    initializeInterface();
    
    // Event listeners
    startDemoBtn.addEventListener('click', startDemo);
    sendApplicantInfoBtn.addEventListener('click', sendApplicantInfo);
    resetBtn.addEventListener('click', resetDemo);
    
    // Protocol selection
    document.querySelectorAll('input[name="protocol"]').forEach(radio => {
        radio.addEventListener('change', function() {
            currentProtocol = this.value;
            console.log(`Protocol switched to: ${currentProtocol}`);
        });
    });
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
    
    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="role-badge role-${role}">${role.toUpperCase()}</span>
            <span class="timestamp">${timestamp}</span>
        </div>
        <div class="message-content">${escapeHtml(content)}</div>
    `;
    
    transcriptElement.appendChild(messageDiv);
    transcriptElement.scrollTop = transcriptElement.scrollHeight;
}

function handleArtifacts(artifactList) {
    artifacts = artifacts.concat(artifactList);
    displayArtifacts();
}

function displayArtifacts() {
    if (artifacts.length === 0) {
        artifactsElement.innerHTML = '<p class="no-artifacts">No artifacts available</p>';
        return;
    }
    
    let html = '<h3>Available Downloads:</h3><ul class="artifact-list">';
    
    artifacts.forEach((artifact, index) => {
        const fileName = artifact.file?.name || `artifact-${index}.json`;
        const taskId = 'demo-task'; // Simple task ID for demo
        
        html += `
            <li class="artifact-item">
                <a href="/artifacts/${taskId}/${fileName}" download="${fileName}" class="artifact-link">
                    📄 ${fileName}
                </a>
                <small class="artifact-type">(${artifact.file?.mimeType || 'application/json'})</small>
            </li>
        `;
    });
    
    html += '</ul>';
    artifactsElement.innerHTML = html;
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
    transcriptElement.innerHTML = '<p class="no-messages">No messages yet. Click "Start Demo" to begin.</p>';
}

function clearArtifacts() {
    artifacts = [];
    artifactsElement.innerHTML = '<p class="no-artifacts">No artifacts available</p>';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}