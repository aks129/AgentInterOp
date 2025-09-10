// Experimental UI Controller for Connectathon Settings
// Non-breaking controller that extends the main app functionality
console.log("Experimental UI Controller initialized");

// Initialize experimental features when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if UI_EXPERIMENTAL flag is enabled by looking for settings panel
    const settingsPanel = document.querySelector('.settings-panel');
    if (!settingsPanel || settingsPanel.hasAttribute('hidden')) {
        console.log('Experimental UI not enabled - skipping initialization');
        return;
    }
    
    console.log('Experimental UI enabled - initializing features');
    initializeExperimentalFeatures();
});

function initializeExperimentalFeatures() {
    // Initialize selftest status on load
    runSelftestCheck();
    
    // Load current settings
    loadCurrentSettings();
    
    // Set up event listeners for experimental controls
    setupExperimentalEventListeners();
}

function setupExperimentalEventListeners() {
    // Settings panel event listeners (already handled in main app.js)
    // These are supplemental handlers for experimental-specific functionality
    
    // Enhanced payload examples with scenario-specific data
    const examplesBtn = document.getElementById('examples-btn');
    if (examplesBtn) {
        // Override the existing examples handler with enhanced functionality
        examplesBtn.removeEventListener('click', fillExamples); // Remove default handler
        examplesBtn.addEventListener('click', fillEnhancedExamples);
    }
    
    // Real-time settings validation
    const settingsInputs = document.querySelectorAll('#scenario-select, input[name="mode"], #admin-processing-ms, #error-injection-rate, #capacity-limit, input[name="protocol-default"]');
    settingsInputs.forEach(input => {
        input.addEventListener('change', validateSettingsRealTime);
    });
    
    // Enhanced save settings with validation
    const saveBtn = document.getElementById('save-settings-btn');
    if (saveBtn) {
        // Add enhanced validation before saving
        saveBtn.addEventListener('click', function(e) {
            if (!validateAllSettings()) {
                e.preventDefault();
                e.stopImmediatePropagation();
            }
        }, true); // Use capture phase to intercept before main handler
    }
}

async function runSelftestCheck() {
    const selftestStatus = document.getElementById('selftest-status');
    if (!selftestStatus) return;
    
    try {
        selftestStatus.className = 'badge bg-secondary';
        selftestStatus.textContent = 'Checking...';
        
        const response = await fetch('/api/selftest');
        const data = await response.json();
        
        if (data.ok) {
            selftestStatus.className = 'badge bg-success';
            selftestStatus.textContent = '✓ All Systems';
            
            // Show additional status info in title
            const statusDetails = [
                `A2A: ${data.a2a.length} methods`,
                `MCP: ${data.mcp.length} methods`,
                `Scenario: ${data.scenario}`
            ];
            selftestStatus.title = statusDetails.join('\n');
        } else {
            selftestStatus.className = 'badge bg-danger';
            selftestStatus.textContent = '✗ Failed';
        }
    } catch (error) {
        selftestStatus.className = 'badge bg-warning';
        selftestStatus.textContent = '? Unknown';
        console.warn('Selftest check failed:', error);
    }
}

async function loadCurrentSettings() {
    try {
        // Load configuration to populate current values
        const configResponse = await fetch('/api/config');
        if (configResponse.ok) {
            const config = await configResponse.json();
            populateSettingsFromConfig(config);
        }
        
        // Load current requirements
        await loadRequirementsText();
        
    } catch (error) {
        console.warn('Failed to load current settings:', error);
    }
}

function populateSettingsFromConfig(config) {
    // Scenario
    const scenarioSelect = document.getElementById('scenario-select');
    if (scenarioSelect && config.scenario?.active) {
        scenarioSelect.value = config.scenario.active;
    }
    
    // Mode
    const mode = config.mode?.role || 'full_stack';
    const modeRadio = document.querySelector(`input[name="mode"][value="${mode}"]`);
    if (modeRadio) {
        modeRadio.checked = true;
    }
    
    // Simulation settings
    const adminMs = document.getElementById('admin-processing-ms');
    const errorRate = document.getElementById('error-injection-rate');
    const capacity = document.getElementById('capacity-limit');
    
    if (adminMs) adminMs.value = config.simulation?.admin_processing_ms || 1200;
    if (errorRate) errorRate.value = config.simulation?.error_injection_rate || 0.0;
    if (capacity) capacity.value = config.simulation?.capacity_limit || '';
    
    // Protocol default
    const protocolDefault = config.protocol?.default_transport || 'a2a';
    const protocolRadio = document.querySelector(`input[name="protocol-default"][value="${protocolDefault}"]`);
    if (protocolRadio) {
        protocolRadio.checked = true;
    }
}

async function loadRequirementsText() {
    const requirementsDiv = document.getElementById('requirements-text');
    if (!requirementsDiv) return;
    
    try {
        const response = await fetch('/api/requirements');
        if (response.ok) {
            const data = await response.json();
            requirementsDiv.textContent = data.requirements || 'No requirements available';
        } else {
            requirementsDiv.textContent = 'Error loading requirements';
        }
    } catch (error) {
        requirementsDiv.textContent = 'Failed to load requirements';
    }
}

async function fillEnhancedExamples() {
    const scenarioSelect = document.getElementById('scenario-select');
    const applicantPayload = document.getElementById('applicant-payload');
    const payloadError = document.getElementById('payload-error');
    
    if (!scenarioSelect || !applicantPayload) return;
    
    const scenario = scenarioSelect.value;
    
    try {
        // Get scenario-specific examples
        const response = await fetch(`/api/scenarios/${scenario}/examples`);
        let examplePayload = {};
        
        if (response.ok) {
            const data = await response.json();
            if (data.examples && data.examples.length > 0) {
                examplePayload = data.examples[0];
            }
        } else {
            // Fallback to default examples by scenario
            examplePayload = getDefaultExampleForScenario(scenario);
        }
        
        applicantPayload.value = JSON.stringify(examplePayload, null, 2);
        
        // Validate the payload
        if (payloadError) {
            payloadError.style.display = 'none';
        }
        
        // Show success feedback
        showTemporaryFeedback('Examples loaded successfully', 'success');
        
    } catch (error) {
        console.error('Failed to load enhanced examples:', error);
        
        // Fallback to default behavior
        const defaultExample = getDefaultExampleForScenario(scenario);
        applicantPayload.value = JSON.stringify(defaultExample, null, 2);
    }
}

function getDefaultExampleForScenario(scenario) {
    const examples = {
        bcse: {
            age: 56,
            sex: "female",
            birthDate: "1968-01-15",
            last_mammogram: "2024-12-01"
        },
        clinical_trial: {
            age: 45,
            sex: "female",
            condition: "breast_cancer",
            stage: "II",
            prior_treatments: ["chemotherapy"]
        },
        referral_specialist: {
            age: 42,
            sex: "male",
            symptoms: "chest pain",
            duration_days: 3,
            referral_type: "cardiology"
        },
        prior_auth: {
            age: 60,
            procedure_code: "77067",
            diagnosis_code: "Z12.31",
            prior_authorization_required: true
        },
        custom: {
            age: 35,
            sex: "female"
        }
    };
    
    return examples[scenario] || examples.bcse;
}

function validateSettingsRealTime() {
    // Real-time validation of settings as user types/changes
    const adminMs = document.getElementById('admin-processing-ms');
    const errorRate = document.getElementById('error-injection-rate');
    const capacity = document.getElementById('capacity-limit');
    
    let isValid = true;
    
    // Validate admin processing time
    if (adminMs) {
        const ms = parseInt(adminMs.value);
        if (isNaN(ms) || ms < 0 || ms > 30000) {
            markFieldInvalid(adminMs, 'Must be 0-30000 ms');
            isValid = false;
        } else {
            markFieldValid(adminMs);
        }
    }
    
    // Validate error injection rate
    if (errorRate) {
        const rate = parseFloat(errorRate.value);
        if (isNaN(rate) || rate < 0 || rate > 1) {
            markFieldInvalid(errorRate, 'Must be 0.0-1.0');
            isValid = false;
        } else {
            markFieldValid(errorRate);
        }
    }
    
    // Validate capacity limit
    if (capacity && capacity.value) {
        const cap = parseInt(capacity.value);
        if (isNaN(cap) || cap < 1) {
            markFieldInvalid(capacity, 'Must be positive integer or blank');
            isValid = false;
        } else {
            markFieldValid(capacity);
        }
    } else if (capacity) {
        markFieldValid(capacity); // Blank is valid
    }
    
    return isValid;
}

function validateAllSettings() {
    const isValid = validateSettingsRealTime();
    
    if (!isValid) {
        showTemporaryFeedback('Please correct validation errors before saving', 'danger');
        return false;
    }
    
    return true;
}

function markFieldInvalid(field, message) {
    field.classList.add('is-invalid');
    field.classList.remove('is-valid');
    
    // Add or update invalid feedback
    let feedback = field.nextElementSibling;
    if (!feedback || !feedback.classList.contains('invalid-feedback')) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.parentNode.insertBefore(feedback, field.nextSibling);
    }
    feedback.textContent = message;
}

function markFieldValid(field) {
    field.classList.remove('is-invalid');
    field.classList.add('is-valid');
    
    // Remove invalid feedback
    const feedback = field.nextElementSibling;
    if (feedback && feedback.classList.contains('invalid-feedback')) {
        feedback.remove();
    }
}

function showTemporaryFeedback(message, type = 'info') {
    // Create a temporary alert that auto-dismisses
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-2`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert after the save button
    const saveBtn = document.getElementById('save-settings-btn');
    if (saveBtn && saveBtn.parentNode) {
        saveBtn.parentNode.insertBefore(alertDiv, saveBtn.nextSibling);
        
        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    }
}

// Enhanced payload validation with scenario-specific checks
function validatePayloadEnhanced() {
    const applicantPayload = document.getElementById('applicant-payload');
    const payloadError = document.getElementById('payload-error');
    const scenarioSelect = document.getElementById('scenario-select');
    
    if (!applicantPayload || !payloadError) return true;
    
    const value = applicantPayload.value.trim();
    if (!value) {
        payloadError.style.display = 'none';
        return true;
    }
    
    try {
        const payload = JSON.parse(value);
        
        // Basic JSON validation passed, now do scenario-specific validation
        if (scenarioSelect) {
            const scenario = scenarioSelect.value;
            const validationResult = validatePayloadForScenario(payload, scenario);
            
            if (validationResult.isValid) {
                payloadError.style.display = 'none';
                return true;
            } else {
                payloadError.textContent = validationResult.error;
                payloadError.style.display = 'block';
                return false;
            }
        }
        
        payloadError.style.display = 'none';
        return true;
        
    } catch (error) {
        payloadError.textContent = `Invalid JSON: ${error.message}`;
        payloadError.style.display = 'block';
        return false;
    }
}

function validatePayloadForScenario(payload, scenario) {
    const validators = {
        bcse: (p) => {
            if (!p.age || !p.sex) return { isValid: false, error: 'BCSE requires age and sex' };
            if (p.sex !== 'female' && p.sex !== 'male') return { isValid: false, error: 'Sex must be "female" or "male"' };
            if (typeof p.age !== 'number' || p.age < 1 || p.age > 120) return { isValid: false, error: 'Age must be 1-120' };
            return { isValid: true };
        },
        clinical_trial: (p) => {
            if (!p.age || !p.condition) return { isValid: false, error: 'Clinical trial requires age and condition' };
            return { isValid: true };
        },
        referral_specialist: (p) => {
            if (!p.symptoms || !p.referral_type) return { isValid: false, error: 'Referral requires symptoms and referral_type' };
            return { isValid: true };
        },
        prior_auth: (p) => {
            if (!p.procedure_code) return { isValid: false, error: 'Prior auth requires procedure_code' };
            return { isValid: true };
        }
    };
    
    const validator = validators[scenario];
    if (validator) {
        return validator(payload);
    }
    
    // No specific validation for this scenario
    return { isValid: true };
}

// Export functions for use by main app if needed
window.ExperimentalUI = {
    validatePayloadEnhanced,
    fillEnhancedExamples,
    validateAllSettings,
    showTemporaryFeedback
};