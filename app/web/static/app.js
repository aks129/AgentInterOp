// BCS Demo App Controller
console.log("BCS Demo App initialized");

// Global state
let currentStage = 'eligibility';
let demoActive = false;
let protocolFrames = [];

// Stage management
const stages = ['eligibility', 'patient', 'order', 'gap-closure', 'next-steps'];
const stageNames = {
    'eligibility': 'Eligibility',
    'patient': 'Patient View', 
    'order': 'Order',
    'gap-closure': 'Gap Closure',
    'next-steps': 'Next Appt & Results'
};

// DOM Elements (cached on load)
let elements = {};

// Initialize when DOM loads
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded, initializing BCS demo");
    cacheElements();
    setupEventListeners();
    initializeUI();
});

function cacheElements() {
    // Cache all frequently used elements
    elements = {
        // Stage navigation
        wizardSteps: document.querySelectorAll('.wizard-step'),
        stagePanels: document.querySelectorAll('.stage-panel'),
        currentStageName: document.getElementById('current-stage-name'),
        
        // Control buttons  
        btnStartDemo: document.getElementById('start-demo-btn'),
        btnContinue: document.getElementById('continue-btn'),
        btnReset: document.getElementById('reset-demo-btn'),
        
        // FHIR/Data buttons
        btnUseCanned: document.getElementById('use-demo-patient-btn'),
        btnTestFhir: document.getElementById('test-fhir-connection'),
        
        // Chat elements
        providerChatInput: document.getElementById('provider-chat-input'),
        providerChatSend: document.getElementById('provider-chat-send'),
        providerChatMessages: document.getElementById('provider-chat-messages'),
        providerChatStatus: document.getElementById('provider-chat-status'),
        
        patientChatInput: document.getElementById('patient-chat-input'),
        patientChatSend: document.getElementById('patient-chat-send'),
        patientChatMessages: document.getElementById('patient-chat-messages'),
        patientChatStatus: document.getElementById('patient-chat-status'),
        
        // Cards and status elements
        eligibilityCard: document.getElementById('eligibility-card'),
        eligibilityStatusBadge: document.getElementById('eligibility-status-badge'),
        eligibilityIcon: document.getElementById('eligibility-icon'),
        eligibilityText: document.getElementById('eligibility-text'),
        eligibilityRationale: document.getElementById('eligibility-rationale'),
        eligibilityMetadata: document.getElementById('eligibility-metadata'),
        
        patientCard: document.getElementById('patient-card'),
        patientSex: document.getElementById('patient-sex'),
        patientAge: document.getElementById('patient-age'),
        patientDob: document.getElementById('patient-dob'),
        patientLastMammo: document.getElementById('patient-last-mammo'),
        
        // Order form
        orderForm: document.getElementById('order-form'),
        facilitySelect: document.getElementById('facility-select'),
        prioritySelect: document.getElementById('priority-select'),
        preferredDate: document.getElementById('preferred-date'),
        dateWindow: document.getElementById('date-window'),
        orderNotes: document.getElementById('order-notes'),
        btnSubmitOrder: document.getElementById('submit-order-btn'),
        
        schedulerCard: document.getElementById('scheduler-response-card'),
        proposedDate: document.getElementById('proposed-date'),
        proposedTime: document.getElementById('proposed-time'),
        proposedLocation: document.getElementById('proposed-location'),
        
        // Gap closure
        btnSimulateBCS: document.getElementById('simulate-gap-closure-btn'),
        gapClosureCard: document.getElementById('gap-closure-card'),
        completionStatusBadge: document.getElementById('completion-status-badge'),
        completionIcon: document.getElementById('completion-icon'),
        completionText: document.getElementById('completion-text'),
        
        // Notifications
        btnSimulateEvent: document.getElementById('simulate-notification-btn'),
        notificationList: document.getElementById('notification-list'),
        
        // Advanced
        rawPayload: document.getElementById('raw-payload'),
        protocolFrames: document.getElementById('protocol-frames')
    };
    
    console.log("Cached elements:", Object.keys(elements).length);
}

function setupEventListeners() {
    console.log("Setting up event listeners");
    
    // Stage navigation
    elements.wizardSteps.forEach(step => {
        step.addEventListener('click', (e) => {
            const targetStage = e.currentTarget.dataset.stage;
            if (canSwitchToStage(targetStage)) {
                switchToStage(targetStage);
            }
        });
    });
    
    // Control buttons
    if (elements.btnStartDemo) {
        elements.btnStartDemo.addEventListener('click', startDemo);
    }
    if (elements.btnContinue) {
        elements.btnContinue.addEventListener('click', continueToNextStage);
    }
    if (elements.btnReset) {
        elements.btnReset.addEventListener('click', resetDemo);
    }
    
    // FHIR buttons
    if (elements.btnUseCanned) {
        elements.btnUseCanned.addEventListener('click', useDemoPatient);
    }
    if (elements.btnTestFhir) {
        elements.btnTestFhir.addEventListener('click', testFhirConnection);
    }
    
    // Chat send buttons
    if (elements.providerChatSend) {
        elements.providerChatSend.addEventListener('click', () => sendProviderMessage());
    }
    if (elements.providerChatInput) {
        elements.providerChatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendProviderMessage();
            }
        });
    }
    
    if (elements.patientChatSend) {
        elements.patientChatSend.addEventListener('click', () => sendPatientMessage());
    }
    if (elements.patientChatInput) {
        elements.patientChatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendPatientMessage();
            }
        });
    }
    
    // Order form
    if (elements.orderForm) {
        elements.orderForm.addEventListener('submit', handleOrderSubmit);
    }
    
    // Simulation buttons
    if (elements.btnSimulateBCS) {
        elements.btnSimulateBCS.addEventListener('click', simulateBCSCompletion);
    }
    if (elements.btnSimulateEvent) {
        elements.btnSimulateEvent.addEventListener('click', simulateNotificationEvent);
    }
    
    console.log("Event listeners setup complete");
}

function initializeUI() {
    console.log("Initializing UI");
    
    // Set default date to tomorrow
    if (elements.preferredDate) {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        elements.preferredDate.value = tomorrow.toISOString().split('T')[0];
    }
    
    // Initialize stage display
    switchToStage('eligibility');
    
    // Disable chat inputs initially
    disableChatInputs();
}

function canSwitchToStage(targetStage) {
    const currentIndex = stages.indexOf(currentStage);
    const targetIndex = stages.indexOf(targetStage);
    
    // Always allow going backwards or staying on current
    if (targetIndex <= currentIndex) return true;
    
    // For forward navigation, check if demo is active
    return demoActive && targetIndex <= currentIndex + 1;
}

function switchToStage(stageName) {
    console.log("Switching to stage:", stageName);
    
    // Hide all panels
    elements.stagePanels.forEach(panel => {
        panel.classList.add('d-none');
    });
    
    // Show target panel
    const targetPanel = document.getElementById(`stage-${stageName}`);
    if (targetPanel) {
        targetPanel.classList.remove('d-none');
    }
    
    // Update wizard steps
    elements.wizardSteps.forEach(step => {
        step.classList.remove('active');
        if (step.dataset.stage === stageName) {
            step.classList.add('active');
        }
    });
    
    currentStage = stageName;
    
    // Update stage name display
    if (elements.currentStageName) {
        elements.currentStageName.textContent = stageNames[stageName] || stageName;
    }
    
    // Update continue button state
    updateContinueButton();
}

function updateContinueButton() {
    if (elements.btnContinue) {
        const currentIndex = stages.indexOf(currentStage);
        const canContinue = demoActive && currentIndex < stages.length - 1;
        elements.btnContinue.disabled = !canContinue;
    }
}

function continueToNextStage() {
    const currentIndex = stages.indexOf(currentStage);
    if (currentIndex < stages.length - 1) {
        switchToStage(stages[currentIndex + 1]);
    }
}

async function startDemo() {
    console.log("Starting demo");
    
    try {
        if (elements.btnStartDemo) {
            elements.btnStartDemo.disabled = true;
            elements.btnStartDemo.innerHTML = '⏳ Starting...';
        }
        
        demoActive = true;
        switchToStage('eligibility');
        enableChatInputs();
        
        // Add welcome message
        addChatMessage('provider', 'system', 'Welcome to the BCS Demo! Click "Use Canned Demo Patient" to load patient data, then start conversations with the evaluator.');
        addChatMessage('patient', 'system', 'Patient chat ready. You can interact with the evaluator using MCP protocol.');
        
        updateChatStatus('provider', 'ready');
        updateChatStatus('patient', 'ready');
        
        updateContinueButton();
        
    } catch (error) {
        console.error('Error starting demo:', error);
        showError('Failed to start demo: ' + error.message);
    } finally {
        if (elements.btnStartDemo) {
            elements.btnStartDemo.disabled = false;
            elements.btnStartDemo.innerHTML = '▶️ Start Demo';
        }
    }
}

function resetDemo() {
    console.log("Resetting demo");
    
    demoActive = false;
    currentStage = 'eligibility';
    protocolFrames = [];
    
    // Clear chat messages
    clearChatMessages('provider');
    clearChatMessages('patient');
    
    // Hide cards
    hideAllCards();
    
    // Reset forms
    if (elements.orderForm) {
        elements.orderForm.reset();
        // Reset date to tomorrow
        if (elements.preferredDate) {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            elements.preferredDate.value = tomorrow.toISOString().split('T')[0];
        }
    }
    
    // Disable chat inputs
    disableChatInputs();
    
    // Reset UI
    switchToStage('eligibility');
    updateContinueButton();
    
    // Clear protocol frames
    if (elements.protocolFrames) {
        elements.protocolFrames.textContent = 'No protocol data yet...';
    }
    if (elements.rawPayload) {
        elements.rawPayload.value = '';
    }
}

function enableChatInputs() {
    [elements.providerChatInput, elements.providerChatSend, elements.patientChatInput, elements.patientChatSend].forEach(el => {
        if (el) el.disabled = false;
    });
}

function disableChatInputs() {
    [elements.providerChatInput, elements.providerChatSend, elements.patientChatInput, elements.patientChatSend].forEach(el => {
        if (el) el.disabled = true;
    });
}

function clearChatMessages(chatType) {
    const messagesContainer = elements[`${chatType}ChatMessages`];
    if (messagesContainer) {
        messagesContainer.innerHTML = `
            <div class="no-messages text-center text-muted py-4">
                <div class="mb-2">💬</div>
                <p class="mb-0">No messages yet</p>
                <small>Conversation will appear here</small>
            </div>
        `;
    }
}

function addChatMessage(chatType, role, message, status = null) {
    const messagesContainer = elements[`${chatType}ChatMessages`];
    if (!messagesContainer) return;
    
    // Remove "no messages" placeholder
    const noMessages = messagesContainer.querySelector('.no-messages');
    if (noMessages) noMessages.remove();
    
    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message mb-3';
    
    const roleIcons = {
        'provider': '🩺',
        'patient': '🙂',
        'evaluator': '🤖',
        'system': '⚙️',
        'error': '❌'
    };
    
    const icon = roleIcons[role] || '❓';
    const timestamp = new Date().toLocaleTimeString();
    
    messageDiv.innerHTML = `
        <div class="d-flex align-items-start">
            <div class="message-avatar me-2" data-role="${role}">
                <span class="avatar-icon">${icon}</span>
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
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function updateChatStatus(chatType, status) {
    const statusElement = elements[`${chatType}ChatStatus`];
    if (statusElement) {
        statusElement.textContent = status.replace('-', ' ').toUpperCase();
        statusElement.className = `status-chip ${status}`;
    }
}

async function useDemoPatient() {
    console.log("Loading demo patient");
    
    try {
        if (elements.btnUseCanned) {
            elements.btnUseCanned.disabled = true;
            elements.btnUseCanned.innerHTML = '⏳ Loading Demo Patient...';
        }
        
        // Call ingest demo endpoint
        const response = await fetch('/api/bcse/ingest/demo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.ok) {
            // Show patient data
            showPatientCard(data.applicant_payload);
            
            // Evaluate eligibility
            await evaluateEligibility(data.applicant_payload);
            
            // Show raw payload
            if (elements.rawPayload) {
                elements.rawPayload.value = JSON.stringify(data.applicant_payload, null, 2);
            }
            
            addChatMessage('provider', 'system', 'Demo patient data loaded successfully. Patient information is now available.');
        } else {
            throw new Error(data.error || 'Failed to load demo patient');
        }
        
    } catch (error) {
        console.error('Error loading demo patient:', error);
        showError('Failed to load demo patient: ' + error.message);
        addChatMessage('provider', 'error', 'Failed to load demo patient: ' + error.message);
    } finally {
        if (elements.btnUseCanned) {
            elements.btnUseCanned.disabled = false;
            elements.btnUseCanned.innerHTML = '📋 Use Canned Demo Patient';
        }
    }
}

function showPatientCard(payload) {
    if (elements.patientCard) {
        elements.patientCard.classList.remove('d-none');
        
        if (elements.patientSex) elements.patientSex.textContent = payload.sex || '-';
        if (elements.patientAge) elements.patientAge.textContent = payload.age ? `${payload.age} years` : '-';
        if (elements.patientDob) elements.patientDob.textContent = payload.birthDate || '-';
        if (elements.patientLastMammo) elements.patientLastMammo.textContent = payload.last_mammogram || '-';
    }
}

async function evaluateEligibility(payload) {
    try {
        const response = await fetch('/api/bcse/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.ok && data.decision) {
            showEligibilityCard(data.decision);
        }
        
    } catch (error) {
        console.error('Error evaluating eligibility:', error);
        showError('Failed to evaluate eligibility: ' + error.message);
    }
}

function showEligibilityCard(decision) {
    if (!elements.eligibilityCard) return;
    
    elements.eligibilityCard.classList.remove('d-none');
    
    let status, iconText, statusText;
    
    if (decision.eligible === true) {
        status = 'eligible';
        iconText = '✅';
        statusText = 'Eligible';
    } else if (decision.eligible === false) {
        status = 'ineligible';
        iconText = '❌';
        statusText = 'Ineligible';
    } else {
        status = 'needs-info';
        iconText = '⚠️';
        statusText = 'Needs Info';
    }
    
    if (elements.eligibilityStatusBadge) {
        elements.eligibilityStatusBadge.textContent = statusText;
        elements.eligibilityStatusBadge.className = `eligibility-badge ${status}`;
    }
    
    if (elements.eligibilityIcon) elements.eligibilityIcon.textContent = iconText;
    if (elements.eligibilityText) elements.eligibilityText.textContent = `BCS ${statusText}`;
    
    // Show rationale
    if (elements.eligibilityRationale && decision.rationale) {
        elements.eligibilityRationale.innerHTML = '';
        decision.rationale.forEach(reason => {
            const li = document.createElement('li');
            li.textContent = reason;
            elements.eligibilityRationale.appendChild(li);
        });
    }
    
    // Show metadata
    if (elements.eligibilityMetadata) {
        const parts = [];
        if (decision.last_mammogram) parts.push(`Last mammogram: ${decision.last_mammogram}`);
        if (decision.age_band) parts.push(`Age band: ${decision.age_band}`);
        elements.eligibilityMetadata.textContent = parts.join(' | ');
    }
}

async function sendProviderMessage() {
    const input = elements.providerChatInput;
    const sendBtn = elements.providerChatSend;
    
    if (!input || !sendBtn) return;
    
    const message = input.value.trim();
    if (!message) return;
    
    try {
        input.disabled = true;
        sendBtn.disabled = true;
        sendBtn.innerHTML = '⏳';
        
        // Add user message
        addChatMessage('provider', 'provider', message);
        input.value = '';
        
        updateChatStatus('provider', 'working');
        
        // Call A2A endpoint
        const response = await fetch('/api/bridge/bcse/a2a', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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
        
        // Log protocol frame
        logProtocolFrame('A2A Request', {
            method: 'message/send',
            message: message
        });
        logProtocolFrame('A2A Response', data);
        
        // Show response
        const responseText = data.result?.message || 'Request processed via A2A JSON-RPC protocol.';
        addChatMessage('provider', 'evaluator', responseText, 'completed');
        
        updateChatStatus('provider', 'completed');
        
    } catch (error) {
        console.error('Error sending provider message:', error);
        addChatMessage('provider', 'error', 'Error: ' + error.message);
        updateChatStatus('provider', 'error');
    } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        sendBtn.innerHTML = 'Send';
    }
}

async function sendPatientMessage() {
    const input = elements.patientChatInput;
    const sendBtn = elements.patientChatSend;
    
    if (!input || !sendBtn) return;
    
    const message = input.value.trim();
    if (!message) return;
    
    try {
        input.disabled = true;
        sendBtn.disabled = true;
        sendBtn.innerHTML = '⏳';
        
        // Add user message
        addChatMessage('patient', 'patient', message);
        input.value = '';
        
        updateChatStatus('patient', 'working');
        
        // MCP Triplet: Begin
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
        
        logProtocolFrame('MCP Begin', { conversationId });
        
        // MCP Triplet: Send
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
        
        logProtocolFrame('MCP Send', { conversationId, message });
        
        // MCP Triplet: Check
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
            logProtocolFrame('MCP Check', checkData);
            
            if (checkData.messages && checkData.messages.length > 0) {
                checkData.messages.forEach(msg => {
                    const msgText = msg.text || msg.content || msg.message || 'Response received via MCP protocol.';
                    addChatMessage('patient', 'evaluator', msgText, 'completed');
                });
            } else {
                addChatMessage('patient', 'evaluator', 'Request processed via MCP triplet (begin → send → check).', 'completed');
            }
        }
        
        updateChatStatus('patient', 'completed');
        
    } catch (error) {
        console.error('Error sending patient message:', error);
        addChatMessage('patient', 'error', 'Error: ' + error.message);
        updateChatStatus('patient', 'error');
    } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        sendBtn.innerHTML = 'Send';
    }
}

function logProtocolFrame(type, data) {
    protocolFrames.push({
        timestamp: new Date().toISOString(),
        type: type,
        data: data
    });
    
    if (elements.protocolFrames) {
        elements.protocolFrames.textContent = JSON.stringify(protocolFrames, null, 2);
    }
}

async function handleOrderSubmit(event) {
    event.preventDefault();
    
    try {
        if (elements.btnSubmitOrder) {
            elements.btnSubmitOrder.disabled = true;
            elements.btnSubmitOrder.innerHTML = '⏳ Submitting Order...';
        }
        
        const formData = {
            facility: elements.facilitySelect?.value,
            priority: elements.prioritySelect?.value,
            preferred_date: elements.preferredDate?.value,
            date_window: elements.dateWindow?.value,
            notes: elements.orderNotes?.value
        };
        
        // Call scheduler endpoint
        const response = await fetch('/api/bcse/scheduler/request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.ok && data.proposal) {
            showSchedulerResponse(data.proposal);
        }
        
    } catch (error) {
        console.error('Error submitting order:', error);
        showError('Failed to submit order: ' + error.message);
    } finally {
        if (elements.btnSubmitOrder) {
            elements.btnSubmitOrder.disabled = false;
            elements.btnSubmitOrder.innerHTML = '📋 Submit Service Request';
        }
    }
}

function showSchedulerResponse(proposal) {
    if (elements.schedulerCard) {
        elements.schedulerCard.classList.remove('d-none');
        
        if (elements.proposedDate) elements.proposedDate.textContent = proposal.proposed_date || '-';
        if (elements.proposedTime) elements.proposedTime.textContent = proposal.proposed_time || '-';
        if (elements.proposedLocation) elements.proposedLocation.textContent = proposal.location || '-';
    }
}

function simulateBCSCompletion() {
    console.log("Simulating BCS completion");
    
    try {
        if (elements.btnSimulateBCS) {
            elements.btnSimulateBCS.disabled = true;
            elements.btnSimulateBCS.innerHTML = '⏳ Simulating...';
        }
        
        setTimeout(() => {
            showGapClosureCard();
            
            if (elements.btnSimulateBCS) {
                elements.btnSimulateBCS.disabled = false;
                elements.btnSimulateBCS.innerHTML = '🧪 Simulate BCS Completion';
            }
        }, 2000);
        
    } catch (error) {
        console.error('Error simulating BCS completion:', error);
        showError('Error simulating BCS completion: ' + error.message);
    }
}

function showGapClosureCard() {
    if (elements.gapClosureCard) {
        elements.gapClosureCard.classList.remove('d-none');
        
        if (elements.completionStatusBadge) {
            elements.completionStatusBadge.textContent = 'Completed';
            elements.completionStatusBadge.className = 'completion-badge bg-success';
        }
        
        if (elements.completionIcon) elements.completionIcon.textContent = '✅';
        if (elements.completionText) elements.completionText.textContent = `BCS completed on ${new Date().toLocaleDateString()}`;
    }
}

function simulateNotificationEvent() {
    console.log("Simulating notification event");
    
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
}

function addNotification(notification) {
    if (!elements.notificationList) return;
    
    // Remove "no notifications" message
    const noNotifications = elements.notificationList.querySelector('.text-center');
    if (noNotifications) noNotifications.remove();
    
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
    
    elements.notificationList.appendChild(notificationDiv);
}

function hideAllCards() {
    [
        elements.eligibilityCard,
        elements.patientCard,
        elements.schedulerCard,
        elements.gapClosureCard
    ].forEach(card => {
        if (card) card.classList.add('d-none');
    });
}

function showError(message) {
    console.error(message);
    // Could implement toast notifications here
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function testFhirConnection() {
    console.log("Testing FHIR connection - placeholder");
    showError("FHIR connection testing not yet implemented");
}