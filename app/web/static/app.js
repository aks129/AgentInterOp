// BCS Demo - Vanilla JS Controller
(function() {
    'use strict';
    
    // Global state
    let currentStage = 'eligibility';
    let patientData = null;
    let protocolFrames = [];
    let mcpConversationId = null;

    // Initialize when DOM loads
    document.addEventListener('DOMContentLoaded', function() {
        console.log('BCS Demo initialized');
        setupEventListeners();
        initializeChatTabs();
    });

    function setupEventListeners() {
        // Stage navigation
        document.querySelectorAll('.step').forEach(step => {
            step.addEventListener('click', function() {
                switchToStage(this.dataset.stage);
            });
        });

        // Use Demo Patient button
        const useDemoBtn = document.getElementById('use-demo-patient');
        if (useDemoBtn) {
            useDemoBtn.addEventListener('click', useDemoPatient);
        }

        // Chat tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                switchChatTab(this.dataset.chat);
            });
        });

        // Provider chat
        const providerSend = document.getElementById('provider-send');
        const providerInput = document.getElementById('provider-input');
        if (providerSend) {
            providerSend.addEventListener('click', sendProviderMessage);
        }
        if (providerInput) {
            providerInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendProviderMessage();
                }
            });
        }

        // MCP controls
        const mcpBegin = document.getElementById('mcp-begin');
        const mcpSend = document.getElementById('mcp-send');
        const mcpCheck = document.getElementById('mcp-check');
        if (mcpBegin) mcpBegin.addEventListener('click', mcpBeginChat);
        if (mcpSend) mcpSend.addEventListener('click', mcpSendMessage);
        if (mcpCheck) mcpCheck.addEventListener('click', mcpCheckReplies);

        // Order form
        const orderForm = document.getElementById('order-form');
        if (orderForm) {
            orderForm.addEventListener('submit', submitOrder);
        }

        // Gap closure simulation
        const simulateCompletion = document.getElementById('simulate-completion');
        if (simulateCompletion) {
            simulateCompletion.addEventListener('click', simulateGapClosure);
        }

        // Notification simulation
        const simulateNotification = document.getElementById('simulate-notification');
        if (simulateNotification) {
            simulateNotification.addEventListener('click', simulateNotificationEvent);
        }

        // Advanced toggle
        const advancedToggle = document.getElementById('advanced-toggle');
        if (advancedToggle) {
            advancedToggle.addEventListener('click', toggleAdvancedPanel);
        }
    }

    function switchToStage(stageName) {
        console.log('Switching to stage:', stageName);
        
        // Update stepper
        document.querySelectorAll('.step').forEach(step => {
            step.classList.remove('active');
        });
        document.querySelector(`[data-stage="${stageName}"]`).classList.add('active');
        
        // Update stage content
        document.querySelectorAll('.stage').forEach(stage => {
            stage.classList.remove('active');
        });
        document.getElementById(`stage-${stageName}`).classList.add('active');
        
        currentStage = stageName;
        
        // Populate patient view if needed
        if (stageName === 'patient' && patientData) {
            populatePatientSummary();
        }
    }

    function initializeChatTabs() {
        switchChatTab('provider');
    }

    function switchChatTab(chatType) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-chat="${chatType}"]`).classList.add('active');
        
        // Update chat panels
        document.querySelectorAll('.chat-panel').forEach(panel => {
            panel.classList.remove('active');
        });
        document.getElementById(`${chatType}-chat`).classList.add('active');
    }

    async function useDemoPatient() {
        const btn = document.getElementById('use-demo-patient');
        const loading = document.getElementById('loading');
        
        try {
            btn.disabled = true;
            btn.textContent = 'Loading...';
            loading.classList.remove('hidden');

            // Call ingest demo endpoint
            const response = await fetch('/api/bcse/ingest/demo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.ok && data.applicant_payload) {
                patientData = data.applicant_payload;
                
                // Show patient snapshot
                showPatientSnapshot(patientData);
                
                // Evaluate eligibility
                await evaluateEligibility(patientData);
                
                addMessage('provider-messages', 'system', 
                    '✅ Demo patient loaded successfully. Patient data is now available.');
                
                logProtocolFrame('FHIR Ingest', data);
            } else {
                throw new Error(data.error || 'Failed to load demo patient');
            }

        } catch (error) {
            console.error('Error loading demo patient:', error);
            addMessage('provider-messages', 'system', 
                `❌ Error loading demo patient: ${error.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = '📋 Use Canned Demo Patient';
            loading.classList.add('hidden');
        }
    }

    function showPatientSnapshot(data) {
        const card = document.getElementById('patient-snapshot');
        if (!card) return;

        document.getElementById('patient-sex').textContent = data.sex || '-';
        document.getElementById('patient-age').textContent = 
            data.age ? `${data.age} years` : (data.birthDate ? calculateAge(data.birthDate) + ' years' : '-');
        document.getElementById('patient-last-mammo').textContent = data.last_mammogram || '-';
        
        card.style.display = 'block';
    }

    function calculateAge(birthDate) {
        if (!birthDate) return '-';
        const today = new Date();
        const birth = new Date(birthDate);
        let age = today.getFullYear() - birth.getFullYear();
        const monthDiff = today.getMonth() - birth.getMonth();
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
            age--;
        }
        return age;
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
                showEligibilityResult(data.decision);
                logProtocolFrame('BCS Evaluation', data);
            }

        } catch (error) {
            console.error('Error evaluating eligibility:', error);
            showEligibilityResult({
                status: 'error',
                rationale: [`Error evaluating eligibility: ${error.message}`]
            });
        }
    }

    function showEligibilityResult(decision) {
        const card = document.getElementById('eligibility-card');
        const icon = document.getElementById('eligibility-icon');
        const text = document.getElementById('eligibility-text');
        const rationale = document.getElementById('eligibility-rationale');

        if (!card) return;

        let statusIcon, statusText, statusClass;
        
        if (decision.eligible === true) {
            statusIcon = '✅';
            statusText = 'Eligible';
            statusClass = 'eligible';
        } else if (decision.eligible === false) {
            statusIcon = '❌';
            statusText = 'Ineligible';
            statusClass = 'ineligible';
        } else {
            statusIcon = '⚠️';
            statusText = 'Needs Info';
            statusClass = 'needs-info';
        }

        icon.textContent = statusIcon;
        text.textContent = statusText;
        
        // Show rationale
        if (decision.rationale && Array.isArray(decision.rationale)) {
            const ul = document.createElement('ul');
            decision.rationale.forEach(reason => {
                const li = document.createElement('li');
                li.textContent = reason;
                ul.appendChild(li);
            });
            rationale.innerHTML = '';
            rationale.appendChild(ul);
        }

        card.style.display = 'block';
        
        // Mark step as completed
        document.querySelector('[data-stage="eligibility"]').classList.add('completed');
    }

    async function sendProviderMessage() {
        const input = document.getElementById('provider-input');
        const message = input.value.trim();
        
        if (!message) return;

        const btn = document.getElementById('provider-send');
        
        try {
            btn.disabled = true;
            btn.textContent = 'Sending...';
            
            // Add user message
            addMessage('provider-messages', 'user', message, '🩺');
            input.value = '';
            
            updateChatStatus('provider-status', 'working');

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
            logProtocolFrame('A2A Request/Response', data);
            
            // Show evaluator response
            const responseText = data.result?.message || 'Message processed via A2A JSON-RPC protocol.';
            addMessage('provider-messages', 'evaluator', responseText, '🤖');
            
            updateChatStatus('provider-status', 'completed');

        } catch (error) {
            console.error('Error sending provider message:', error);
            addMessage('provider-messages', 'system', 
                `❌ Error: ${error.message}`);
            updateChatStatus('provider-status', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Send';
        }
    }

    async function mcpBeginChat() {
        try {
            const btn = document.getElementById('mcp-begin');
            btn.disabled = true;
            btn.textContent = 'Beginning...';

            const response = await fetch('/api/mcp/bcse/begin_chat_thread', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.content && data.content[0] && data.content[0].text) {
                const result = JSON.parse(data.content[0].text);
                mcpConversationId = result.conversationId;
                
                // Enable other MCP controls
                document.getElementById('mcp-send').disabled = false;
                document.getElementById('mcp-message').disabled = false;
                
                addMessage('patient-messages', 'system', 
                    `✅ MCP chat thread started: ${mcpConversationId}`);
                
                logProtocolFrame('MCP Begin', data);
            }

        } catch (error) {
            console.error('Error beginning MCP chat:', error);
            addMessage('patient-messages', 'system', 
                `❌ Error beginning MCP chat: ${error.message}`);
        } finally {
            const btn = document.getElementById('mcp-begin');
            btn.disabled = false;
            btn.textContent = 'Begin';
        }
    }

    async function mcpSendMessage() {
        if (!mcpConversationId) {
            addMessage('patient-messages', 'system', '❌ No active conversation. Begin first.');
            return;
        }

        const input = document.getElementById('mcp-message');
        const message = input.value.trim();
        
        if (!message) return;

        try {
            const btn = document.getElementById('mcp-send');
            btn.disabled = true;
            btn.textContent = 'Sending...';
            
            addMessage('patient-messages', 'user', message, '🙂');
            input.value = '';

            const response = await fetch('/api/mcp/bcse/send_message_to_chat_thread', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    conversationId: mcpConversationId,
                    message: message
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            logProtocolFrame('MCP Send', data);
            
            addMessage('patient-messages', 'system', 
                '✅ Message sent via MCP. Use "Check Replies" to see responses.');
            
            // Enable check button
            document.getElementById('mcp-check').disabled = false;

        } catch (error) {
            console.error('Error sending MCP message:', error);
            addMessage('patient-messages', 'system', 
                `❌ Error sending message: ${error.message}`);
        } finally {
            const btn = document.getElementById('mcp-send');
            btn.disabled = false;
            btn.textContent = 'Send Message';
        }
    }

    async function mcpCheckReplies() {
        if (!mcpConversationId) {
            addMessage('patient-messages', 'system', '❌ No active conversation.');
            return;
        }

        try {
            const btn = document.getElementById('mcp-check');
            btn.disabled = true;
            btn.textContent = 'Checking...';

            const response = await fetch('/api/mcp/bcse/check_replies', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    conversationId: mcpConversationId,
                    waitMs: 2000
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            logProtocolFrame('MCP Check', data);

            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    const text = msg.text || msg.content || msg.message || 'Response received';
                    addMessage('patient-messages', 'evaluator', text, '🤖');
                });
            } else {
                addMessage('patient-messages', 'evaluator', 
                    'MCP triplet completed successfully.', '🤖');
            }

        } catch (error) {
            console.error('Error checking MCP replies:', error);
            addMessage('patient-messages', 'system', 
                `❌ Error checking replies: ${error.message}`);
        } finally {
            const btn = document.getElementById('mcp-check');
            btn.disabled = false;
            btn.textContent = 'Check Replies';
        }
    }

    async function submitOrder(event) {
        event.preventDefault();
        
        const btn = document.querySelector('#order-form button[type="submit"]');
        const formData = new FormData(event.target);
        
        try {
            btn.disabled = true;
            btn.textContent = 'Submitting...';

            // Get form data
            const orderData = {
                facility: document.getElementById('facility').value,
                date_window: document.getElementById('date-window').value,
                priority: document.getElementById('priority').value
            };

            // Mock scheduler response (since we may not have the real endpoint)
            const mockResponse = await mockSchedulerRequest(orderData);
            
            showSchedulerResponse(mockResponse);
            
            // Mark order stage as completed
            document.querySelector('[data-stage="order"]').classList.add('completed');

        } catch (error) {
            console.error('Error submitting order:', error);
            alert('Error submitting order: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = '📋 Submit Order';
        }
    }

    async function mockSchedulerRequest(orderData) {
        // Try real endpoint first, fallback to mock
        try {
            const response = await fetch('/api/bcse/scheduler/request', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(orderData)
            });

            if (response.ok) {
                const data = await response.json();
                if (data.ok && data.proposal) {
                    return data.proposal;
                }
            }
        } catch (error) {
            console.log('Real scheduler not available, using mock');
        }

        // Mock response
        const facilities = {
            'downtown-imaging': 'Downtown Imaging Center',
            'suburban-radiology': 'Suburban Radiology',
            'university-hospital': 'University Hospital'
        };

        const times = [
            '9:00 AM - 9:30 AM',
            '10:30 AM - 11:00 AM',
            '2:15 PM - 2:45 PM',
            '3:30 PM - 4:00 PM'
        ];

        // Generate a date within the window
        const today = new Date();
        const daysAhead = Math.floor(Math.random() * parseInt(orderData.date_window)) + 1;
        const proposedDate = new Date(today.getTime() + daysAhead * 24 * 60 * 60 * 1000);

        return {
            facility: facilities[orderData.facility] || orderData.facility,
            proposed_date: proposedDate.toISOString().split('T')[0],
            proposed_time: times[Math.floor(Math.random() * times.length)]
        };
    }

    function showSchedulerResponse(proposal) {
        const card = document.getElementById('scheduler-response');
        if (!card) return;

        document.getElementById('proposed-facility').textContent = proposal.facility || '-';
        document.getElementById('proposed-date').textContent = proposal.proposed_date || '-';
        document.getElementById('proposed-time').textContent = proposal.proposed_time || '-';
        
        card.style.display = 'block';
        
        logProtocolFrame('Scheduler Response', proposal);
    }

    function simulateGapClosure() {
        const btn = document.getElementById('simulate-completion');
        const icon = document.getElementById('gap-closure-icon');
        const text = document.getElementById('gap-closure-text');
        
        try {
            btn.disabled = true;
            btn.textContent = 'Simulating...';
            
            setTimeout(() => {
                // Update main display
                icon.textContent = '✅';
                text.textContent = 'BCS Completed Successfully';
                
                // Show completion card
                const card = document.getElementById('completion-card');
                if (card) {
                    const today = new Date().toLocaleDateString();
                    document.getElementById('completion-date').textContent = today;
                    document.getElementById('trace-link').href = `#trace-${Date.now()}`;
                    card.style.display = 'block';
                }
                
                // Mark stage as completed
                document.querySelector('[data-stage="gap-closure"]').classList.add('completed');
                
                logProtocolFrame('Gap Closure Simulation', {
                    status: 'completed',
                    cpt_code: '77067',
                    date: new Date().toISOString(),
                    source: 'demo-simulation'
                });
                
            }, 2000);

        } finally {
            setTimeout(() => {
                btn.disabled = false;
                btn.textContent = '🧪 Simulate BCS Completion';
            }, 2000);
        }
    }

    function simulateNotificationEvent() {
        const notifications = [
            {
                type: 'provider',
                icon: '🩺',
                title: 'Results Ready for Review',
                message: 'Mammogram results are available. Patient screening completed successfully.',
                timestamp: new Date().toLocaleString()
            },
            {
                type: 'patient',
                icon: '🙂',
                title: 'Your Results Are Available',
                message: 'Good news! Your mammogram shows no signs of concern. Next screening in 2 years.',
                timestamp: new Date().toLocaleString()
            },
            {
                type: 'care-manager',
                icon: '📅',
                title: 'Follow-up Scheduled',
                message: 'BCS gap closed. Next screening reminder set for January 2027.',
                timestamp: new Date().toLocaleString()
            }
        ];

        const notification = notifications[Math.floor(Math.random() * notifications.length)];
        addNotification(notification);
        
        // Mark stage as completed
        document.querySelector('[data-stage="next-steps"]').classList.add('completed');
        
        logProtocolFrame('Notification Event', notification);
    }

    function addNotification(notification) {
        const feed = document.getElementById('notification-feed');
        if (!feed) return;

        const div = document.createElement('div');
        div.className = 'notification';
        div.innerHTML = `
            <h5>${notification.icon} ${notification.title}</h5>
            <p>${notification.message}</p>
            <div class="timestamp">${notification.timestamp}</div>
        `;

        feed.appendChild(div);
    }

    function populatePatientSummary() {
        const summary = document.getElementById('patient-summary');
        if (!summary || !patientData) return;

        summary.innerHTML = `
            <div class="patient-info">
                <div class="info-row">
                    <span class="label">Sex:</span>
                    <span>${patientData.sex || '-'}</span>
                </div>
                <div class="info-row">
                    <span class="label">Birth Date:</span>
                    <span>${patientData.birthDate || '-'}</span>
                </div>
                <div class="info-row">
                    <span class="label">Age:</span>
                    <span>${patientData.age || (patientData.birthDate ? calculateAge(patientData.birthDate) : '-')}</span>
                </div>
                <div class="info-row">
                    <span class="label">Last Mammogram:</span>
                    <span>${patientData.last_mammogram || '-'}</span>
                </div>
            </div>
        `;
    }

    function addMessage(containerId, role, message, avatar = '') {
        const container = document.getElementById(containerId);
        if (!container) return;

        const div = document.createElement('div');
        div.className = `message ${role}`;
        div.innerHTML = `${avatar} ${message}`;
        
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    function updateChatStatus(statusId, status) {
        const statusEl = document.getElementById(statusId);
        if (statusEl) {
            statusEl.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            statusEl.className = `chat-status ${status}`;
        }
    }

    function logProtocolFrame(type, data) {
        protocolFrames.push({
            timestamp: new Date().toISOString(),
            type: type,
            data: data
        });
        
        const framesEl = document.getElementById('protocol-frames');
        if (framesEl) {
            framesEl.textContent = JSON.stringify(protocolFrames, null, 2);
        }
    }

    function toggleAdvancedPanel() {
        const panel = document.getElementById('advanced-panel');
        const btn = document.getElementById('advanced-toggle');
        
        if (panel.style.display === 'none') {
            panel.style.display = 'block';
            btn.textContent = 'Advanced ↑';
        } else {
            panel.style.display = 'none';
            btn.textContent = 'Advanced ↕';
        }
    }

})();