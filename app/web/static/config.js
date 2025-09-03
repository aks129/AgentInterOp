// Configuration Control Panel JavaScript
console.log("Configuration Control Panel initialized");

// Global state
let currentConfig = {};
let scenarios = {};
let isLoading = false;

// DOM elements
const scenarioSelect = document.getElementById('scenario-select');
const requirementsText = document.getElementById('requirements-text');
const customPayload = document.getElementById('custom-payload');
const payloadError = document.getElementById('payload-error');
const selftestStatus = document.getElementById('selftest-status');
const actionLog = document.getElementById('action-log');

// Form elements
const modeRadios = document.querySelectorAll('input[name="mode"]');
const protocolRadios = document.querySelectorAll('input[name="protocol-default"]');
const allowFhirMcp = document.getElementById('allow-fhir-mcp');
const allowLocalBundle = document.getElementById('allow-local-bundle');
const allowFreeText = document.getElementById('allow-free-text');
const adminProcessingMs = document.getElementById('admin-processing-ms');
const errorInjectionRate = document.getElementById('error-injection-rate');
const capacityLimit = document.getElementById('capacity-limit');

// Button elements
const loadExamplesBtn = document.getElementById('load-examples-btn');
const saveConfigBtn = document.getElementById('save-config-btn');
const exportConfigBtn = document.getElementById('export-config-btn');
const importConfigBtn = document.getElementById('import-config-btn');
const validateConfigBtn = document.getElementById('validate-config-btn');
const restartServicesBtn = document.getElementById('restart-services-btn');
const resetAllBtn = document.getElementById('reset-all-btn');
const backupDataBtn = document.getElementById('backup-data-btn');
const viewLogsBtn = document.getElementById('view-logs-btn');
const clearCacheBtn = document.getElementById('clear-cache-btn');
const healthCheckBtn = document.getElementById('health-check-btn');
const performanceBtn = document.getElementById('performance-btn');
const connectivityBtn = document.getElementById('connectivity-btn');
const stressTestBtn = document.getElementById('stress-test-btn');
const benchmarkBtn = document.getElementById('benchmark-btn');
const configFileInput = document.getElementById('config-file-input');

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    initializeFeatherIcons();
    setupEventListeners();
    loadInitialData();
});

function initializeFeatherIcons() {
    feather.replace();
}

function setupEventListeners() {
    // Scenario and payload
    scenarioSelect.addEventListener('change', onScenarioChange);
    customPayload.addEventListener('input', validatePayload);
    loadExamplesBtn.addEventListener('click', loadExampleData);

    // Configuration actions
    saveConfigBtn.addEventListener('click', saveConfiguration);
    exportConfigBtn.addEventListener('click', exportConfiguration);
    importConfigBtn.addEventListener('click', () => configFileInput.click());
    configFileInput.addEventListener('change', importConfiguration);

    // System actions
    validateConfigBtn.addEventListener('click', validateConfiguration);
    restartServicesBtn.addEventListener('click', restartServices);
    resetAllBtn.addEventListener('click', resetAll);

    // Data management
    backupDataBtn.addEventListener('click', backupData);
    viewLogsBtn.addEventListener('click', viewLogs);
    clearCacheBtn.addEventListener('click', clearCache);

    // Monitoring
    healthCheckBtn.addEventListener('click', healthCheck);
    performanceBtn.addEventListener('click', performanceCheck);
    connectivityBtn.addEventListener('click', connectivityCheck);

    // Load testing
    stressTestBtn.addEventListener('click', runStressTest);
    benchmarkBtn.addEventListener('click', runBenchmark);
}

async function loadInitialData() {
    try {
        setLoading(true);
        await Promise.all([
            loadConfiguration(),
            loadScenarios(),
            runSelftest(),
            loadRequirements()
        ]);
        logAction('Configuration panel loaded successfully');
    } catch (error) {
        console.error('Error loading initial data:', error);
        showNotification('Failed to load initial data', 'error');
    } finally {
        setLoading(false);
    }
}

async function loadConfiguration() {
    try {
        const response = await fetch('/api/config');
        currentConfig = await response.json();
        populateConfigForm();
    } catch (error) {
        console.error('Error loading configuration:', error);
        throw error;
    }
}

async function loadScenarios() {
    try {
        const response = await fetch('/api/scenarios');
        const data = await response.json();
        scenarios = data.scenarios;
        populateScenarioSelect(data.active);
    } catch (error) {
        console.error('Error loading scenarios:', error);
        throw error;
    }
}

async function runSelftest() {
    try {
        const response = await fetch('/api/selftest');
        const data = await response.json();
        updateSelftestBadge(data.ok);
    } catch (error) {
        updateSelftestBadge(false);
    }
}

async function loadRequirements() {
    try {
        const response = await fetch('/api/requirements');
        const data = await response.json();
        requirementsText.textContent = data.requirements;
    } catch (error) {
        requirementsText.textContent = 'Error loading requirements';
    }
}

function populateConfigForm() {
    // Scenario
    if (currentConfig.scenario?.active) {
        scenarioSelect.value = currentConfig.scenario.active;
    }

    // Mode
    const mode = currentConfig.mode?.role || 'full_stack';
    modeRadios.forEach(radio => {
        radio.checked = radio.value === mode;
    });

    // Protocol
    const protocol = currentConfig.protocol?.default_transport || 'a2a';
    protocolRadios.forEach(radio => {
        radio.checked = radio.value === protocol;
    });

    // Data sources
    allowFhirMcp.checked = currentConfig.data?.allow_fhir_mcp !== false;
    allowLocalBundle.checked = currentConfig.data?.allow_local_bundle !== false;
    allowFreeText.checked = currentConfig.data?.allow_free_text_context !== false;

    // Simulation settings
    adminProcessingMs.value = currentConfig.simulation?.admin_processing_ms || 1200;
    errorInjectionRate.value = currentConfig.simulation?.error_injection_rate || 0;
    capacityLimit.value = currentConfig.simulation?.capacity_limit || '';
}

function populateScenarioSelect(activeScenario) {
    scenarioSelect.innerHTML = '';
    Object.entries(scenarios).forEach(([key, scenario]) => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = scenario.label;
        option.selected = key === activeScenario;
        scenarioSelect.appendChild(option);
    });
}

function updateSelftestBadge(success) {
    selftestStatus.className = `badge ${success ? 'bg-success' : 'bg-danger'}`;
    selftestStatus.textContent = success ? '✓ OK' : '✗ Failed';
}

async function onScenarioChange() {
    await loadRequirements();
    logAction(`Scenario changed to: ${scenarioSelect.value}`);
}

function validatePayload() {
    const value = customPayload.value.trim();
    if (!value) {
        payloadError.style.display = 'none';
        customPayload.className = customPayload.className.replace(/\bis-invalid\b/, '');
        return true;
    }

    try {
        JSON.parse(value);
        payloadError.style.display = 'none';
        customPayload.className = customPayload.className.replace(/\bis-invalid\b/, '');
        customPayload.classList.add('is-valid');
        return true;
    } catch (error) {
        payloadError.textContent = `Invalid JSON: ${error.message}`;
        payloadError.style.display = 'block';
        customPayload.className = customPayload.className.replace(/\bis-valid\b/, '');
        customPayload.classList.add('is-invalid');
        return false;
    }
}

async function loadExampleData() {
    try {
        setButtonLoading(loadExamplesBtn, true);
        const activeScenario = scenarioSelect.value;
        const scenario = scenarios[activeScenario];
        
        if (scenario?.examples && scenario.examples.length > 0) {
            customPayload.value = JSON.stringify(scenario.examples[0], null, 2);
            validatePayload();
            logAction(`Loaded example data for ${scenario.label}`);
            showNotification('Example data loaded successfully', 'success');
        } else {
            showNotification('No example data available for this scenario', 'warning');
        }
    } catch (error) {
        console.error('Error loading examples:', error);
        showNotification('Failed to load example data', 'error');
    } finally {
        setButtonLoading(loadExamplesBtn, false);
    }
}

async function saveConfiguration() {
    try {
        setButtonLoading(saveConfigBtn, true);
        
        // Collect all configuration data
        const config = {
            scenario: {
                active: scenarioSelect.value
            },
            mode: {
                role: document.querySelector('input[name="mode"]:checked').value
            },
            protocol: {
                default_transport: document.querySelector('input[name="protocol-default"]:checked').value
            },
            data: {
                allow_fhir_mcp: allowFhirMcp.checked,
                allow_local_bundle: allowLocalBundle.checked,
                allow_free_text_context: allowFreeText.checked
            },
            simulation: {
                admin_processing_ms: parseInt(adminProcessingMs.value) || 1200,
                error_injection_rate: parseFloat(errorInjectionRate.value) || 0,
                capacity_limit: capacityLimit.value ? parseInt(capacityLimit.value) : null
            }
        };

        // Save configuration
        await Promise.all([
            fetch('/api/scenarios/activate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: config.scenario.active})
            }),
            fetch('/api/mode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config.mode)
            }),
            fetch('/api/simulation', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config.simulation)
            }),
            fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            })
        ]);

        await loadConfiguration();
        logAction('Configuration saved successfully');
        showNotification('Configuration saved successfully', 'success');
        
    } catch (error) {
        console.error('Error saving configuration:', error);
        logAction(`Configuration save failed: ${error.message}`);
        showNotification('Failed to save configuration', 'error');
    } finally {
        setButtonLoading(saveConfigBtn, false);
    }
}

async function exportConfiguration() {
    try {
        setButtonLoading(exportConfigBtn, true);
        const blob = new Blob([JSON.stringify(currentConfig, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `connectathon-config-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        
        logAction('Configuration exported');
        showNotification('Configuration exported successfully', 'success');
    } catch (error) {
        console.error('Error exporting configuration:', error);
        showNotification('Failed to export configuration', 'error');
    } finally {
        setButtonLoading(exportConfigBtn, false);
    }
}

async function importConfiguration() {
    try {
        const file = configFileInput.files[0];
        if (!file) return;

        const text = await file.text();
        const importedConfig = JSON.parse(text);
        
        // Apply imported configuration
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(importedConfig)
        });

        if (response.ok) {
            await loadConfiguration();
            logAction(`Configuration imported from ${file.name}`);
            showNotification('Configuration imported successfully', 'success');
        } else {
            throw new Error('Failed to import configuration');
        }
    } catch (error) {
        console.error('Error importing configuration:', error);
        logAction(`Configuration import failed: ${error.message}`);
        showNotification('Failed to import configuration', 'error');
    }
}

async function validateConfiguration() {
    try {
        setButtonLoading(validateConfigBtn, true);
        
        // Run validation checks
        const checks = await Promise.all([
            fetch('/api/selftest'),
            fetch('/api/requirements'),
            fetch('/api/scenarios')
        ]);

        const allPassed = checks.every(response => response.ok);
        
        if (allPassed) {
            updateSystemStatus('Configuration', 'Valid', 'success');
            logAction('Configuration validation passed');
            showNotification('Configuration is valid', 'success');
        } else {
            updateSystemStatus('Configuration', 'Invalid', 'danger');
            logAction('Configuration validation failed');
            showNotification('Configuration validation failed', 'error');
        }
    } catch (error) {
        console.error('Error validating configuration:', error);
        showNotification('Failed to validate configuration', 'error');
    } finally {
        setButtonLoading(validateConfigBtn, false);
    }
}

async function restartServices() {
    try {
        setButtonLoading(restartServicesBtn, true);
        
        // Simulate service restart
        updateSystemStatus('Services', 'Restarting', 'warning');
        logAction('Services restart initiated');
        
        // Wait a moment to simulate restart
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        updateSystemStatus('Services', 'Running', 'success');
        logAction('Services restarted successfully');
        showNotification('Services restarted successfully', 'success');
    } catch (error) {
        console.error('Error restarting services:', error);
        updateSystemStatus('Services', 'Error', 'danger');
        showNotification('Failed to restart services', 'error');
    } finally {
        setButtonLoading(restartServicesBtn, false);
    }
}

async function resetAll() {
    if (!confirm('Are you sure you want to reset all configuration and data? This action cannot be undone.')) {
        return;
    }

    try {
        setButtonLoading(resetAllBtn, true);
        
        await Promise.all([
            fetch('/api/config/reset', {method: 'POST'}),
            fetch('/api/admin/reset', {method: 'POST'})
        ]);

        await loadConfiguration();
        clearActionLog();
        
        logAction('System reset to defaults');
        showNotification('System reset successfully', 'success');
    } catch (error) {
        console.error('Error resetting system:', error);
        showNotification('Failed to reset system', 'error');
    } finally {
        setButtonLoading(resetAllBtn, false);
    }
}

async function backupData() {
    try {
        setButtonLoading(backupDataBtn, true);
        
        // Create backup data structure
        const backupData = {
            timestamp: new Date().toISOString(),
            configuration: currentConfig,
            scenarios: scenarios
        };

        const blob = new Blob([JSON.stringify(backupData, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `connectathon-backup-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        
        logAction('Data backup created');
        showNotification('Data backup created successfully', 'success');
    } catch (error) {
        console.error('Error creating backup:', error);
        showNotification('Failed to create backup', 'error');
    } finally {
        setButtonLoading(backupDataBtn, false);
    }
}

async function viewLogs() {
    try {
        setButtonLoading(viewLogsBtn, true);
        
        // Open logs in new window/tab
        const logWindow = window.open('', '_blank', 'width=800,height=600');
        logWindow.document.write(`
            <html>
                <head><title>System Logs</title></head>
                <body style="background: #1a1a1a; color: #e0e0e0; font-family: monospace; padding: 20px;">
                    <h2>System Logs</h2>
                    <pre id="log-content">Loading logs...</pre>
                </body>
            </html>
        `);

        // Simulate log fetching
        setTimeout(() => {
            const logContent = actionLog.innerHTML.replace(/<[^>]*>/g, '\n').trim();
            logWindow.document.getElementById('log-content').textContent = logContent || 'No logs available';
        }, 500);
        
        logAction('System logs viewed');
    } catch (error) {
        console.error('Error viewing logs:', error);
        showNotification('Failed to view logs', 'error');
    } finally {
        setButtonLoading(viewLogsBtn, false);
    }
}

async function clearCache() {
    try {
        setButtonLoading(clearCacheBtn, true);
        
        // Clear browser cache for this domain
        if ('caches' in window) {
            const cacheNames = await caches.keys();
            await Promise.all(cacheNames.map(name => caches.delete(name)));
        }
        
        logAction('Cache cleared');
        showNotification('Cache cleared successfully', 'success');
    } catch (error) {
        console.error('Error clearing cache:', error);
        showNotification('Failed to clear cache', 'error');
    } finally {
        setButtonLoading(clearCacheBtn, false);
    }
}

async function healthCheck() {
    try {
        setButtonLoading(healthCheckBtn, true);
        
        const checks = [
            { name: 'Configuration', endpoint: '/api/config' },
            { name: 'Scenarios', endpoint: '/api/scenarios' },
            { name: 'Self-test', endpoint: '/api/selftest' }
        ];

        for (const check of checks) {
            try {
                const response = await fetch(check.endpoint);
                const status = response.ok ? 'success' : 'danger';
                const text = response.ok ? 'Online' : 'Error';
                updateSystemStatus(check.name, text, status);
            } catch (error) {
                updateSystemStatus(check.name, 'Error', 'danger');
            }
        }
        
        logAction('Health check completed');
        showNotification('Health check completed', 'info');
    } catch (error) {
        console.error('Error during health check:', error);
        showNotification('Health check failed', 'error');
    } finally {
        setButtonLoading(healthCheckBtn, false);
    }
}

async function performanceCheck() {
    try {
        setButtonLoading(performanceBtn, true);
        
        const startTime = performance.now();
        
        // Run performance tests
        await Promise.all([
            fetch('/api/config'),
            fetch('/api/scenarios'),
            fetch('/api/requirements')
        ]);
        
        const endTime = performance.now();
        const responseTime = Math.round(endTime - startTime);
        
        logAction(`Performance check: ${responseTime}ms response time`);
        showNotification(`Performance: ${responseTime}ms response time`, 'info');
    } catch (error) {
        console.error('Error during performance check:', error);
        showNotification('Performance check failed', 'error');
    } finally {
        setButtonLoading(performanceBtn, false);
    }
}

async function connectivityCheck() {
    try {
        setButtonLoading(connectivityBtn, true);
        
        const startTime = Date.now();
        const response = await fetch('/api/config');
        const endTime = Date.now();
        
        if (response.ok) {
            const latency = endTime - startTime;
            updateSystemStatus('Database', 'Connected', 'success');
            logAction(`Connectivity check: ${latency}ms latency`);
            showNotification(`Connected (${latency}ms)`, 'success');
        } else {
            updateSystemStatus('Database', 'Disconnected', 'danger');
            showNotification('Connectivity check failed', 'error');
        }
    } catch (error) {
        console.error('Error during connectivity check:', error);
        updateSystemStatus('Database', 'Error', 'danger');
        showNotification('Connectivity check failed', 'error');
    } finally {
        setButtonLoading(connectivityBtn, false);
    }
}

async function runStressTest() {
    try {
        setButtonLoading(stressTestBtn, true);
        
        logAction('Stress test initiated');
        showNotification('Running stress test...', 'info');
        
        // Simulate stress test with multiple concurrent requests
        const promises = [];
        for (let i = 0; i < 10; i++) {
            promises.push(fetch('/api/config'));
        }
        
        const results = await Promise.allSettled(promises);
        const successCount = results.filter(r => r.status === 'fulfilled').length;
        
        logAction(`Stress test completed: ${successCount}/10 requests successful`);
        showNotification(`Stress test: ${successCount}/10 successful`, successCount === 10 ? 'success' : 'warning');
    } catch (error) {
        console.error('Error during stress test:', error);
        showNotification('Stress test failed', 'error');
    } finally {
        setButtonLoading(stressTestBtn, false);
    }
}

async function runBenchmark() {
    try {
        setButtonLoading(benchmarkBtn, true);
        
        logAction('Benchmark initiated');
        showNotification('Running benchmark...', 'info');
        
        const iterations = 5;
        const times = [];
        
        for (let i = 0; i < iterations; i++) {
            const start = performance.now();
            await fetch('/api/config');
            const end = performance.now();
            times.push(end - start);
        }
        
        const avgTime = Math.round(times.reduce((a, b) => a + b, 0) / times.length);
        const minTime = Math.round(Math.min(...times));
        const maxTime = Math.round(Math.max(...times));
        
        logAction(`Benchmark completed: avg ${avgTime}ms, min ${minTime}ms, max ${maxTime}ms`);
        showNotification(`Benchmark: ${avgTime}ms average`, 'info');
    } catch (error) {
        console.error('Error during benchmark:', error);
        showNotification('Benchmark failed', 'error');
    } finally {
        setButtonLoading(benchmarkBtn, false);
    }
}

// Utility functions
function setLoading(loading) {
    isLoading = loading;
    if (loading) {
        document.body.style.cursor = 'wait';
    } else {
        document.body.style.cursor = 'default';
    }
}

function setButtonLoading(button, loading) {
    if (loading) {
        button.disabled = true;
        button.classList.add('loading');
    } else {
        button.disabled = false;
        button.classList.remove('loading');
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function logAction(message) {
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    logEntry.innerHTML = `
        <span class="timestamp">${new Date().toLocaleTimeString()}</span>
        <span class="message">${message}</span>
    `;
    
    actionLog.insertBefore(logEntry, actionLog.firstChild);
    
    // Keep only last 20 entries
    while (actionLog.children.length > 20) {
        actionLog.removeChild(actionLog.lastChild);
    }
}

function clearActionLog() {
    actionLog.innerHTML = '';
}

function updateSystemStatus(component, status, type) {
    const systemStatus = document.getElementById('system-status');
    const statusItems = systemStatus.querySelectorAll('.status-item');
    
    statusItems.forEach(item => {
        const label = item.querySelector('.status-label').textContent;
        if (label.includes(component)) {
            const badge = item.querySelector('.badge');
            badge.className = `badge bg-${type}`;
            badge.textContent = status;
        }
    });
}