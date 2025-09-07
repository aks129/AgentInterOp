// BCSE Demo JavaScript
console.log("BCSE Demo initialized");

// Global state
let currentStage = 'eligibility';
let demoState = {
    eligibility: { completed: false, status: 'pending' },
    patient: { completed: false, status: 'pending' },
    order: { completed: false, status: 'pending' },
    'gap-closure': { completed: false, status: 'pending' },
    'next-steps': { completed: false, status: 'pending' }
};
let conversationData = {
    provider: { messages: [], active: false },
    patient: { messages: [], active: false }
};
let currentProtocol = 'a2a';

// Role avatars mapping
const roleAvatars = {
    'provider': '🩺',
    'patient': '🙂',
    'evaluator': '🤖',
    'admin': '📅',
    'scheduler': '📅',
    'system': '⚙️',
    'error': '❌'
};

// Initialize when DOM loads
document.addEventListener('DOMContentLoaded', function() {
    initializeBCSEDemo();
    setupEventListeners();
    updateStageDisplay();
});

function initializeBCSEDemo() {
    console.log("Initializing BCSE Demo");
    
    // Set default preferred date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const preferredDateInput = document.getElementById('preferred-date');
    if (preferredDateInput) {
        preferredDateInput.value = tomorrow.toISOString().split('T')[0];
    }
    
    // Initialize chat inputs as disabled
    disableChatInputs();
    
    // Clear any existing messages
    clearAllChats();
}

function setupEventListeners() {
    // Stage navigation
    document.querySelectorAll('.wizard-step').forEach(step => {
        step.addEventListener('click', function() {
            const targetStage = this.dataset.stage;
            if (canNavigateToStage(targetStage)) {
                switchToStage(targetStage);
            }
        });
    });
    
    // Demo controls
    const startBtn = document.getElementById('start-demo-btn');
    const continueBtn = document.getElementById('continue-btn');
    const resetBtn = document.getElementById('reset-demo-btn');
    
    if (startBtn) startBtn.addEventListener('click', startDemo);
    if (continueBtn) continueBtn.addEventListener('click', continueToNextStage);
    if (resetBtn) resetBtn.addEventListener('click', resetDemo);
    
    // FHIR controls
    const useDemoBtn = document.getElementById('use-demo-patient-btn');
    const testConnectionBtn = document.getElementById('test-fhir-connection');
    
    if (useDemoBtn) useDemoBtn.addEventListener('click', useDemoPatient);
    if (testConnectionBtn) testConnectionBtn.addEventListener('click', testFhirConnection);
    
    // Chat controls
    setupChatEventListeners('provider-chat');
    setupChatEventListeners('patient-chat');
    
    // Order form
    const orderForm = document.getElementById('order-form');
    if (orderForm) orderForm.addEventListener('submit', handleOrderSubmit);
    
    // Gap closure simulation
    const simulateGapBtn = document.getElementById('simulate-gap-closure-btn');
    if (simulateGapBtn) simulateGapBtn.addEventListener('click', simulateGapClosure);
    
    // Notification simulation
    const simulateNotificationBtn = document.getElementById('simulate-notification-btn');
    if (simulateNotificationBtn) simulateNotificationBtn.addEventListener('click', simulateNotification);
}

function setupChatEventListeners(chatId) {
    const sendBtn = document.getElementById(`${chatId}-send`);
    const input = document.getElementById(`${chatId}-input`);
    
    if (sendBtn && input) {
        sendBtn.addEventListener('click', () => sendChatMessage(chatId));
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !input.disabled) {
                sendChatMessage(chatId);
            }
        });
    }
}

function canNavigateToStage(targetStage) {
    // Allow navigation to completed stages and the next available stage
    const stages = ['eligibility', 'patient', 'order', 'gap-closure', 'next-steps'];
    const targetIndex = stages.indexOf(targetStage);
    const currentIndex = stages.indexOf(currentStage);
    
    // Allow navigation to previous stages or one stage ahead if previous is completed
    if (targetIndex <= currentIndex) return true;
    if (targetIndex === currentIndex + 1 && demoState[currentStage].completed) return true;
    
    return false;
}

function switchToStage(stageName) {
    // Hide all stage panels
    document.querySelectorAll('.stage-panel').forEach(panel => {
        panel.classList.add('d-none');
    });
    
    // Show target stage panel
    const targetPanel = document.getElementById(`stage-${stageName}`);
    if (targetPanel) {
        targetPanel.classList.remove('d-none');
    }
    
    // Update wizard navigation
    document.querySelectorAll('.wizard-step').forEach(step => {
        step.classList.remove('active');
        if (demoState[step.dataset.stage]?.completed) {
            step.classList.add('completed');
        }
    });
    
    const activeStep = document.querySelector(`.wizard-step[data-stage="${stageName}"]`);
    if (activeStep) {
        activeStep.classList.add('active');
    }
    
    currentStage = stageName;
    updateStageDisplay();
}

function updateStageDisplay() {
    const stageNameElement = document.getElementById('current-stage-name');
    if (stageNameElement) {
        const stageNames = {
            'eligibility': 'Eligibility',
            'patient': 'Patient View',
            'order': 'Order',
            'gap-closure': 'Gap Closure',
            'next-steps': 'Next Appt & Results'
        };
        stageNameElement.textContent = stageNames[currentStage] || currentStage;
    }
    
    // Update continue button state
    const continueBtn = document.getElementById('continue-btn');
    if (continueBtn) {
        continueBtn.disabled = !demoState[currentStage].completed;
    }
}

async function startDemo() {
    console.log("Starting BCSE Demo");
    
    const startBtn = document.getElementById('start-demo-btn');
    if (startBtn) {
        startBtn.disabled = true;
        startBtn.innerHTML = '⏳ Starting...';
    }
    
    try {
        // Reset demo state
        resetDemoState();
        
        // Switch to eligibility stage
        switchToStage('eligibility');
        
        // Enable chat inputs
        enableChatInputs();
        
        // Add welcome message
        addChatMessage('provider-chat', 'system', 'Welcome to the BCS Eligibility Demo! This demonstrates Language-First Interoperability using A2A JSON-RPC and MCP protocols.');
        
        addChatMessage('provider-chat', 'system', 'Click "Use Canned Demo Patient" to load patient data, then start a conversation with the evaluator agent.');
        
        // Update status
        updateChatStatus('provider-chat', 'ready');
        updateChatStatus('patient-chat', 'ready');
        
    } catch (error) {
        console.error('Error starting demo:', error);
        addChatMessage('provider-chat', 'error', `Failed to start demo: ${error.message}`);
    } finally {
        if (startBtn) {
            startBtn.disabled = false;
            startBtn.innerHTML = '▶️ Start Demo';
        }
    }
}

function resetDemo() {
    console.log("Resetting BCSE Demo");
    
    // Reset demo state
    resetDemoState();
    
    // Clear all chats
    clearAllChats();
    
    // Hide all outcome cards
    hideAllCards();
    
    // Disable chat inputs
    disableChatInputs();
    
    // Reset form
    const orderForm = document.getElementById('order-form');
    if (orderForm) orderForm.reset();
    
    // Switch back to eligibility stage
    switchToStage('eligibility');
    
    // Reset control buttons
    const startBtn = document.getElementById('start-demo-btn');
    const continueBtn = document.getElementById('continue-btn');
    
    if (startBtn) {
        startBtn.disabled = false;
        startBtn.innerHTML = '▶️ Start Demo';
    }
    if (continueBtn) {
        continueBtn.disabled = true;
    }
}

function resetDemoState() {
    demoState = {
        eligibility: { completed: false, status: 'pending' },
        patient: { completed: false, status: 'pending' },
        order: { completed: false, status: 'pending' },
        'gap-closure': { completed: false, status: 'pending' },
        'next-steps': { completed: false, status: 'pending' }
    };
    
    conversationData = {
        provider: { messages: [], active: false },
        patient: { messages: [], active: false }
    };
}

function continueToNextStage() {
    const stages = ['eligibility', 'patient', 'order', 'gap-closure', 'next-steps'];
    const currentIndex = stages.indexOf(currentStage);
    
    if (currentIndex < stages.length - 1) {
        const nextStage = stages[currentIndex + 1];
        switchToStage(nextStage);
    }
}

// Chat Functions
function enableChatInputs() {
    const inputs = document.querySelectorAll('.chat-input input');
    const buttons = document.querySelectorAll('.chat-input button');
    
    inputs.forEach(input => input.disabled = false);
    buttons.forEach(button => button.disabled = false);
}

function disableChatInputs() {
    const inputs = document.querySelectorAll('.chat-input input');
    const buttons = document.querySelectorAll('.chat-input button');
    
    inputs.forEach(input => input.disabled = true);
    buttons.forEach(button => button.disabled = true);
}

function clearAllChats() {
    ['provider-chat', 'patient-chat'].forEach(chatId => {
        const messagesContainer = document.getElementById(`${chatId}-messages`);
        if (messagesContainer) {
            messagesContainer.innerHTML = `
                <div class="no-messages text-center text-muted py-4">
                    <div class="mb-2">💬</div>
                    <p class="mb-0">No messages yet</p>
                    <small>Conversation will appear here</small>
                </div>
            `;
        }
    });
}

function addChatMessage(chatId, role, message, status = null) {
    const messagesContainer = document.getElementById(`${chatId}-messages`);
    if (!messagesContainer) return;
    
    // Remove "no messages" placeholder
    const noMessages = messagesContainer.querySelector('.no-messages');
    if (noMessages) {
        noMessages.remove();
    }
    
    // Create message element
    const messageElement = createMessageElement(role, message, status);
    messagesContainer.appendChild(messageElement);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Store in conversation data
    const chatType = chatId.replace('-chat', '');
    if (!conversationData[chatType]) {
        conversationData[chatType] = { messages: [], active: false };
    }
    conversationData[chatType].messages.push({ role, message, status, timestamp: new Date() });
}

function createMessageElement(role, message, status = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message mb-3';
    
    const avatar = roleAvatars[role] || '❓';
    const timestamp = new Date().toLocaleTimeString();
    
    messageDiv.innerHTML = `
        <div class="d-flex align-items-start">
            <div class="message-avatar me-2" data-role="${role}">
                <span class="avatar-icon">${avatar}</span>
            </div>
            <div class="message-content flex-grow-1">
                <div class="message-header d-flex justify-content-between align-items-center mb-1">
                    <div class="d-flex align-items-center">
                        <span class="message-role fw-bold me-2">${role.toUpperCase()}</span>
                        <small class="message-timestamp text-muted">${timestamp}</small>
                    </div>
                    ${status ? `<span class="message-status-chip ${status}">${status.replace('-', ' ')}</span>` : ''}
                </div>
                <div class="message-text" data-role="${role}">${escapeHtml(message)}</div>
            </div>
        </div>
    `;
    
    return messageDiv;
}

function updateChatStatus(chatId, status) {
    const statusElement = document.getElementById(`${chatId}-status`);
    if (statusElement) {
        statusElement.textContent = status.replace('-', ' ').toUpperCase();
        statusElement.className = `status-chip ${status}`;
    }
}

async function sendChatMessage(chatId) {
    const input = document.getElementById(`${chatId}-input`);
    const sendBtn = document.getElementById(`${chatId}-send`);
    
    if (!input || !sendBtn) return;
    
    const message = input.value.trim();
    if (!message) return;
    
    const chatType = chatId.replace('-chat', '');
    const role = chatType === 'provider' ? 'provider' : 'patient';
    
    // Disable input while sending
    input.disabled = true;
    sendBtn.disabled = true;
    sendBtn.innerHTML = '⏳';
    
    try {
        // Add user message
        addChatMessage(chatId, role, message);
        
        // Clear input
        input.value = '';
        
        // Update status to working
        updateChatStatus(chatId, 'working');
        
        // Simulate processing delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Send to appropriate endpoint based on chat type
        if (chatType === 'provider') {
            await handleProviderMessage(chatId, message);
        } else {
            await handlePatientMessage(chatId, message);
        }
        
    } catch (error) {
        console.error(`Error sending message to ${chatId}:`, error);
        addChatMessage(chatId, 'error', `Error: ${error.message}`);
        updateChatStatus(chatId, 'error');
    } finally {
        // Re-enable input
        input.disabled = false;
        sendBtn.disabled = false;
        sendBtn.innerHTML = 'Send';
    }
}

async function handleProviderMessage(chatId, message) {
    try {
        // Simulate A2A call
        const response = await fetch('/api/bridge/bcse/a2a', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                method: 'message/send',
                params: {
                    message: {
                        parts: [{ kind: 'text', text: message }]
                    }
                }
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Add evaluator response
        addChatMessage(chatId, 'evaluator', 
            data.result?.message || 'Request received and processed via A2A JSON-RPC protocol.',
            'completed'
        );
        
        updateChatStatus(chatId, 'completed');
        
        // If this is the first successful message, mark eligibility as completed
        if (currentStage === 'eligibility' && message.toLowerCase().includes('eligib')) {
            completeEligibilityStage();
        }
        
    } catch (error) {
        console.error('Provider message error:', error);
        addChatMessage(chatId, 'evaluator', 
            'Error processing request via A2A protocol. Please try again.',
            'error'
        );
        updateChatStatus(chatId, 'error');
    }
}

async function handlePatientMessage(chatId, message) {
    try {
        // Start with MCP protocol
        const beginResponse = await fetch('/api/mcp/bcse/begin_chat_thread', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        if (!beginResponse.ok) {
            throw new Error('Failed to begin MCP chat thread');
        }
        
        const beginData = await beginResponse.json();
        const conversationId = JSON.parse(beginData.content[0].text).conversationId;
        
        // Send message
        const sendResponse = await fetch('/api/mcp/bcse/send_message_to_chat_thread', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                conversationId: conversationId,
                message: message
            })
        });
        
        if (!sendResponse.ok) {
            throw new Error('Failed to send MCP message');
        }
        
        // Check for replies
        const checkResponse = await fetch('/api/mcp/bcse/check_replies', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                conversationId: conversationId,
                waitMs: 2000
            })
        });
        
        if (checkResponse.ok) {
            const checkData = await checkResponse.json();
            
            if (checkData.messages && checkData.messages.length > 0) {
                checkData.messages.forEach(msg => {
                    addChatMessage(chatId, 'evaluator', 
                        msg.text || msg.content || 'Response received via MCP protocol.',
                        'completed'
                    );
                });
            } else {
                addChatMessage(chatId, 'evaluator', 
                    'Request processed via MCP triplet (begin → send → check).',
                    'completed'
                );
            }
        }
        
        updateChatStatus(chatId, 'completed');
        
    } catch (error) {
        console.error('Patient message error:', error);
        addChatMessage(chatId, 'evaluator', 
            'Error processing request via MCP protocol. Please try again.',
            'error'
        );
        updateChatStatus(chatId, 'error');
    }
}

// FHIR Functions
async function useDemoPatient() {
    const btn = document.getElementById('use-demo-patient-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '⏳ Loading Demo Patient...';
    }
    
    try {
        const response = await fetch('/api/bcse/ingest/demo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.ok) {
            // Populate patient card
            showPatientCard(data.applicant_payload);
            
            // Show eligibility evaluation
            await evaluateEligibility(data.applicant_payload);
            
            // Show raw payload in advanced section
            const rawPayloadTextarea = document.getElementById('raw-payload');
            if (rawPayloadTextarea) {
                rawPayloadTextarea.value = JSON.stringify(data.applicant_payload, null, 2);
            }
            
            addChatMessage('provider-chat', 'system', 
                'Demo patient data loaded successfully. Patient information available in the right panel.'
            );
            
        } else {
            throw new Error(data.error || 'Failed to load demo patient');
        }
        
    } catch (error) {
        console.error('Error loading demo patient:', error);
        addChatMessage('provider-chat', 'error', `Failed to load demo patient: ${error.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '📋 Use Canned Demo Patient';
        }
    }
}

function showPatientCard(payload) {
    const patientCard = document.getElementById('patient-card');
    if (patientCard) {
        patientCard.classList.remove('d-none');
        
        // Populate patient data
        document.getElementById('patient-sex').textContent = payload.sex || '-';
        document.getElementById('patient-age').textContent = payload.age ? `${payload.age} years` : '-';
        document.getElementById('patient-dob').textContent = payload.birthDate || '-';
        document.getElementById('patient-last-mammo').textContent = payload.last_mammogram || '-';
    }
}

async function evaluateEligibility(payload) {
    try {
        const response = await fetch('/api/bcse/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (data.ok && data.decision) {
            showEligibilityCard(data.decision);
        }
        
    } catch (error) {
        console.error('Error evaluating eligibility:', error);
    }
}

function showEligibilityCard(decision) {
    const eligibilityCard = document.getElementById('eligibility-card');
    if (!eligibilityCard) return;
    
    eligibilityCard.classList.remove('d-none');
    
    const statusBadge = document.getElementById('eligibility-status-badge');
    const icon = document.getElementById('eligibility-icon');
    const text = document.getElementById('eligibility-text');
    const rationale = document.getElementById('eligibility-rationale');
    const metadata = document.getElementById('eligibility-metadata');
    
    // Update status based on decision
    let status, iconText, statusText;
    
    if (decision.eligible === true) {
        status = 'eligible';
        iconText = '✅';
        statusText = 'Eligible for BCS';
    } else if (decision.eligible === false) {
        status = 'ineligible';
        iconText = '❌';
        statusText = 'Not Eligible for BCS';
    } else {
        status = 'needs-info';
        iconText = '⚠️';
        statusText = 'Needs Additional Information';
    }
    
    if (statusBadge) {
        statusBadge.textContent = statusText;
        statusBadge.className = `eligibility-badge ${status}`;
    }
    
    if (icon) icon.textContent = iconText;
    if (text) text.textContent = statusText;
    
    // Show rationale
    if (rationale && decision.rationale) {
        rationale.innerHTML = '';
        decision.rationale.forEach(reason => {
            const li = document.createElement('li');
            li.textContent = reason;
            rationale.appendChild(li);
        });
    }
    
    // Show metadata
    if (metadata) {
        const parts = [];
        if (decision.last_mammogram) parts.push(`Last mammogram: ${decision.last_mammogram}`);
        if (decision.age_band) parts.push(`Age band: ${decision.age_band}`);
        metadata.textContent = parts.join(' | ');
    }
    
    // Mark eligibility stage as completed if we have a definitive result
    if (decision.eligible !== null) {
        completeEligibilityStage();
    }
}

function completeEligibilityStage() {
    demoState.eligibility.completed = true;
    demoState.eligibility.status = 'completed';
    updateStageDisplay();
    
    // Mark patient stage as accessible
    demoState.patient.status = 'ready';
}

// Order Functions
async function handleOrderSubmit(event) {
    event.preventDefault();
    
    const submitBtn = document.getElementById('submit-order-btn');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '⏳ Submitting Order...';
    }
    
    try {
        // Get form data
        const facility = document.getElementById('facility-select').value;
        const priority = document.getElementById('priority-select').value;
        const preferredDate = document.getElementById('preferred-date').value;
        const dateWindow = document.getElementById('date-window').value;
        const notes = document.getElementById('order-notes').value;
        
        // Show service request card
        showServiceRequestCard({
            facility,
            priority,
            preferredDate,
            dateWindow,
            notes
        });
        
        // Simulate scheduler response after delay
        setTimeout(() => {
            showSchedulerResponse({
                proposedDate: preferredDate,
                proposedTime: '10:30 AM - 11:00 AM',
                location: facility
            });
            
            // Complete order stage
            demoState.order.completed = true;
            demoState.order.status = 'completed';
            updateStageDisplay();
            
        }, 2000);
        
    } catch (error) {
        console.error('Error submitting order:', error);
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '📋 Submit Service Request';
        }
    }
}

function showServiceRequestCard(orderData) {
    const card = document.getElementById('service-request-card');
    if (card) {
        card.classList.remove('d-none');
        
        document.getElementById('request-facility').textContent = orderData.facility || '-';
        document.getElementById('request-date-window').textContent = 
            orderData.preferredDate ? `${orderData.preferredDate} (±${orderData.dateWindow} days)` : '-';
        document.getElementById('request-priority').textContent = orderData.priority || '-';
        document.getElementById('request-status').textContent = 'Submitted';
    }
}

function showSchedulerResponse(responseData) {
    const card = document.getElementById('scheduler-response-card');
    if (card) {
        card.classList.remove('d-none');
        
        document.getElementById('proposed-date').textContent = responseData.proposedDate || '-';
        document.getElementById('proposed-time').textContent = responseData.proposedTime || '-';
        document.getElementById('proposed-location').textContent = responseData.location || '-';
        
        // Setup button handlers
        const acceptBtn = document.getElementById('accept-slot-btn');
        const alternativeBtn = document.getElementById('request-alternative-btn');
        
        if (acceptBtn) {
            acceptBtn.addEventListener('click', function() {
                this.textContent = '✅ Accepted';
                this.disabled = true;
                alternativeBtn.disabled = true;
            });
        }
        
        if (alternativeBtn) {
            alternativeBtn.addEventListener('click', function() {
                this.textContent = '🔄 Requesting...';
                this.disabled = true;
            });
        }
    }
}

// Gap Closure Functions
function simulateGapClosure() {
    const btn = document.getElementById('simulate-gap-closure-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '⏳ Simulating...';
    }
    
    setTimeout(() => {
        showGapClosureCard();
        
        // Complete gap closure stage
        demoState['gap-closure'].completed = true;
        demoState['gap-closure'].status = 'completed';
        updateStageDisplay();
        
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '🧪 Simulate BCS Completion';
        }
        
        // Update the gap closure status display
        const statusDisplay = document.getElementById('gap-closure-status');
        if (statusDisplay) {
            statusDisplay.innerHTML = `
                <div class="text-center py-4">
                    <div class="mb-3">
                        <div class="status-icon-large">✅</div>
                    </div>
                    <h6 class="text-success">BCS Gap Closed Successfully</h6>
                    <p class="text-muted">Mammogram procedure (CPT 77067) has been completed and recorded.</p>
                </div>
            `;
        }
        
    }, 2000);
}

function showGapClosureCard() {
    const card = document.getElementById('gap-closure-card');
    if (card) {
        card.classList.remove('d-none');
        
        const statusBadge = document.getElementById('completion-status-badge');
        const icon = document.getElementById('completion-icon');
        const text = document.getElementById('completion-text');
        const metadata = document.getElementById('completion-metadata');
        const traceLink = document.getElementById('trace-link');
        
        if (statusBadge) {
            statusBadge.textContent = 'Completed';
            statusBadge.className = 'completion-badge bg-success';
        }
        
        if (icon) icon.textContent = '✅';
        if (text) text.textContent = 'BCS completed successfully on ' + new Date().toLocaleDateString();
        if (metadata) {
            metadata.textContent = `Source: Demo Abstractor | CPT: 77067 | Time: ${new Date().toLocaleTimeString()}`;
        }
        
        if (traceLink) {
            traceLink.style.display = 'inline-block';
            traceLink.href = `/api/trace/demo-context-${Date.now()}`;
        }
    }
}

// Notification Functions
function simulateNotification() {
    const notifications = [
        {
            type: 'provider',
            icon: '🩺',
            title: 'Results Ready for Review',
            message: 'Mammogram results are available. Patient screening completed successfully.',
            metadata: 'Priority: Normal | Next screening: 24 months'
        },
        {
            type: 'patient',
            icon: '🙂', 
            title: 'Your Results Are Available',
            message: 'Good news! Your mammogram shows no signs of concern.',
            metadata: 'Access via Patient Portal | Next appointment: Auto-scheduled'
        },
        {
            type: 'care-manager',
            icon: '📅',
            title: 'Follow-up Scheduled',
            message: 'BCS gap closed. Next screening reminder set for January 2027.',
            metadata: 'Action: Auto-reminder created | Priority: Routine'
        }
    ];
    
    const notification = notifications[Math.floor(Math.random() * notifications.length)];
    addNotification(notification);
    
    // Complete next-steps stage if not already completed
    if (!demoState['next-steps'].completed) {
        demoState['next-steps'].completed = true;
        demoState['next-steps'].status = 'completed';
        updateStageDisplay();
    }
}

function addNotification(notification) {
    const notificationList = document.getElementById('notification-list');
    if (!notificationList) return;
    
    // Remove "no notifications" message if present
    const noNotifications = notificationList.querySelector('.text-center');
    if (noNotifications) {
        noNotifications.remove();
    }
    
    // Create notification element
    const notificationDiv = document.createElement('div');
    notificationDiv.className = 'notification-item border rounded p-3 mb-2';
    notificationDiv.innerHTML = `
        <div class="d-flex align-items-start">
            <div class="notification-icon ${notification.type} me-3">${notification.icon}</div>
            <div class="flex-grow-1">
                <div class="d-flex justify-content-between align-items-start mb-1">
                    <h6 class="notification-title mb-0">${notification.title}</h6>
                    <small class="notification-timestamp text-muted">${new Date().toLocaleTimeString()}</small>
                </div>
                <p class="notification-message mb-1">${notification.message}</p>
                <div class="notification-metadata small text-muted">${notification.metadata}</div>
            </div>
        </div>
    `;
    
    notificationList.appendChild(notificationDiv);
}

// FHIR Connection Functions
async function testFhirConnection() {
    const btn = document.getElementById('test-fhir-connection');
    const baseUrl = document.getElementById('fhir-base-url').value;
    
    if (!baseUrl) {
        addChatMessage('provider-chat', 'error', 'Please enter a FHIR base URL first.');
        return;
    }
    
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '⏳ Testing...';
    }
    
    try {
        // Save FHIR config first
        await fetch('/api/fhir/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                base: baseUrl,
                token: document.getElementById('fhir-token').value
            })
        });
        
        // Test capabilities
        const response = await fetch('/api/fhir/capabilities');
        const data = await response.json();
        
        if (data.fhirVersion) {
            addChatMessage('provider-chat', 'system', 
                `✅ FHIR server connection successful! Version: ${data.fhirVersion}`
            );
            
            const ingestBtn = document.getElementById('ingest-fhir-data');
            if (ingestBtn) ingestBtn.disabled = false;
        } else {
            throw new Error(data.error || 'Failed to connect to FHIR server');
        }
        
    } catch (error) {
        console.error('FHIR connection error:', error);
        addChatMessage('provider-chat', 'error', `FHIR connection failed: ${error.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = 'Test Connection';
        }
    }
}

// Helper Functions
function hideAllCards() {
    const cards = document.querySelectorAll('.outcome-card');
    cards.forEach(card => card.classList.add('d-none'));
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}