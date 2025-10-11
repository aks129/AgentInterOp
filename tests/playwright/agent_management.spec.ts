/**
 * Playwright E2E Tests for Healthcare Agent Management UI
 * Tests agent creation, listing, filtering, and management operations
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';

test.describe('Healthcare Agent Management UI', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to agent management page
    await page.goto(`${BASE_URL}/agents`);

    // Wait for page to load
    await page.waitForSelector('.header h1');
  });

  test('should display the agent management page header', async ({ page }) => {
    // Check page title
    await expect(page.locator('.header h1')).toContainText('Healthcare Agent Management');

    // Check subtitle
    await expect(page.locator('.header-subtitle')).toContainText('A2A-Compliant Agent Development');

    // Check create button exists
    await expect(page.locator('button:has-text("Create New Agent")')).toBeVisible();
  });

  test('should display tabs for navigation', async ({ page }) => {
    // Check all tabs are present
    await expect(page.locator('.tab:has-text("All Agents")')).toBeVisible();
    await expect(page.locator('.tab:has-text("Templates")')).toBeVisible();
    await expect(page.locator('.tab:has-text("Domains")')).toBeVisible();

    // Check first tab is active
    await expect(page.locator('.tab.active')).toHaveText('All Agents');
  });

  test('should switch between tabs', async ({ page }) => {
    // Click on Templates tab
    await page.click('.tab:has-text("Templates")');

    // Verify Templates tab is active
    await expect(page.locator('.tab.active')).toHaveText('Templates');
    await expect(page.locator('#templates-tab.active')).toBeVisible();

    // Click on Domains tab
    await page.click('.tab:has-text("Domains")');

    // Verify Domains tab is active
    await expect(page.locator('.tab.active')).toHaveText('Domains');
    await expect(page.locator('#domains-tab.active')).toBeVisible();
  });

  test('should display filter controls', async ({ page }) => {
    // Check filter dropdowns exist
    await expect(page.locator('#filterStatus')).toBeVisible();
    await expect(page.locator('#filterDomain')).toBeVisible();
    await expect(page.locator('#filterRole')).toBeVisible();
  });

  test('should create BCS-E sample agent', async ({ page }) => {
    // Wait for agents to load
    await page.waitForTimeout(1000);

    // Check if sample agent button exists or agent list
    const agentsContainer = page.locator('#agentsContainer');
    const content = await agentsContainer.textContent();

    if (content && content.includes('Create BCS-E Sample Agent')) {
      // Click create sample agent button
      await page.click('button:has-text("Create BCS-E Sample Agent")');

      // Wait for success message
      await page.waitForSelector('.alert-success', { timeout: 5000 });

      // Verify success message
      await expect(page.locator('.alert-success')).toContainText('created successfully');

      // Wait for agents to reload
      await page.waitForTimeout(1000);

      // Verify agent appears in list
      await expect(page.locator('.agent-card')).toBeVisible();
    } else {
      // Agent already exists
      await expect(page.locator('.agent-card')).toBeVisible();
    }
  });

  test('should open create agent modal', async ({ page }) => {
    // Click create button
    await page.click('button:has-text("Create New Agent")');

    // Verify modal is visible
    await expect(page.locator('#agentModal.active')).toBeVisible();
    await expect(page.locator('.modal-title')).toHaveText('Create New Agent');

    // Verify form fields are present
    await expect(page.locator('#agentName')).toBeVisible();
    await expect(page.locator('#agentDescription')).toBeVisible();
    await expect(page.locator('#agentPurpose')).toBeVisible();
    await expect(page.locator('#agentDomain')).toBeVisible();
    await expect(page.locator('#agentRole')).toBeVisible();
  });

  test('should close create agent modal', async ({ page }) => {
    // Open modal
    await page.click('button:has-text("Create New Agent")');
    await expect(page.locator('#agentModal.active')).toBeVisible();

    // Close modal
    await page.click('.close-btn');

    // Verify modal is hidden
    await expect(page.locator('#agentModal.active')).not.toBeVisible();
  });

  test('should validate required fields in create form', async ({ page }) => {
    // Open modal
    await page.click('button:has-text("Create New Agent")');

    // Try to submit empty form
    await page.click('button[type="submit"]');

    // Check for HTML5 validation (required fields)
    const nameInput = page.locator('#agentName');
    const isInvalid = await nameInput.evaluate((el: HTMLInputElement) => !el.validity.valid);
    expect(isInvalid).toBe(true);
  });

  test('should create a new custom agent', async ({ page }) => {
    // Open modal
    await page.click('button:has-text("Create New Agent")');

    // Fill in form
    await page.fill('#agentName', 'Test Clinical Trial Agent');
    await page.fill('#agentDescription', 'Automated clinical trial enrollment agent for testing');
    await page.fill('#agentPurpose', 'Match patients to clinical trials');
    await page.selectOption('#agentDomain', 'clinical_trial');
    await page.selectOption('#agentRole', 'administrator');

    // Fill constitution fields
    await page.fill('#constitutionConstraints', 'Age range: 18-80\nMust meet inclusion criteria');
    await page.fill('#constitutionEthics', 'Ensure informed consent\nProtect patient privacy');
    await page.fill('#constitutionCapabilities', 'FHIR integration\nTrial matching algorithm');

    // Fill plan fields
    await page.fill('#planGoals', 'Match eligible patients\nReduce enrollment time');
    await page.fill('#planCriteria', 'Match accuracy >= 90%\nResponse time < 3 seconds');

    // Submit form
    await page.click('button[type="submit"]');

    // Wait for success message
    await page.waitForSelector('.alert-success', { timeout: 5000 });

    // Verify success
    await expect(page.locator('.alert-success')).toContainText('created successfully');

    // Wait for agents to reload
    await page.waitForTimeout(1000);

    // Verify new agent appears
    await expect(page.locator('.agent-card:has-text("Test Clinical Trial Agent")')).toBeVisible();
  });

  test('should filter agents by status', async ({ page }) => {
    // Ensure we have agents
    await page.waitForTimeout(1000);

    // Create sample agent if needed
    const content = await page.locator('#agentsContainer').textContent();
    if (content && content.includes('Create BCS-E Sample Agent')) {
      await page.click('button:has-text("Create BCS-E Sample Agent")');
      await page.waitForTimeout(1500);
    }

    // Filter by active status
    await page.selectOption('#filterStatus', 'active');

    // Wait for filter to apply
    await page.waitForTimeout(500);

    // Verify all visible agents have active status
    const statusBadges = page.locator('.agent-status.status-active');
    const count = await statusBadges.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should filter agents by domain', async ({ page }) => {
    await page.waitForTimeout(1000);

    // Create sample agent if needed
    const content = await page.locator('#agentsContainer').textContent();
    if (content && content.includes('Create BCS-E Sample Agent')) {
      await page.click('button:has-text("Create BCS-E Sample Agent")');
      await page.waitForTimeout(1500);
    }

    // Filter by preventive_screening domain
    await page.selectOption('#filterDomain', 'preventive_screening');

    // Wait for filter to apply
    await page.waitForTimeout(500);

    // Verify agents are shown (sample agent is preventive_screening)
    const agents = page.locator('.agent-card');
    const count = await agents.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should display agent details correctly', async ({ page }) => {
    await page.waitForTimeout(1000);

    // Create sample agent if needed
    const content = await page.locator('#agentsContainer').textContent();
    if (content && content.includes('Create BCS-E Sample Agent')) {
      await page.click('button:has-text("Create BCS-E Sample Agent")');
      await page.waitForTimeout(1500);
    }

    // Find first agent card
    const agentCard = page.locator('.agent-card').first();

    // Verify card components
    await expect(agentCard.locator('.agent-name')).toBeVisible();
    await expect(agentCard.locator('.agent-status')).toBeVisible();
    await expect(agentCard.locator('.agent-description')).toBeVisible();
    await expect(agentCard.locator('.agent-meta')).toBeVisible();
    await expect(agentCard.locator('.agent-actions')).toBeVisible();
  });

  test('should have functional action buttons', async ({ page }) => {
    await page.waitForTimeout(1000);

    // Create sample agent if needed
    const content = await page.locator('#agentsContainer').textContent();
    if (content && content.includes('Create BCS-E Sample Agent')) {
      await page.click('button:has-text("Create BCS-E Sample Agent")');
      await page.waitForTimeout(1500);
    }

    // Find first agent card
    const agentCard = page.locator('.agent-card').first();

    // Verify action buttons exist
    await expect(agentCard.locator('button:has-text("View")')).toBeVisible();
    await expect(agentCard.locator('button:has-text("Deactivate"), button:has-text("Activate")')).toBeVisible();
    await expect(agentCard.locator('button:has-text("Archive")')).toBeVisible();
  });

  test('should display domains in Domains tab', async ({ page }) => {
    // Click on Domains tab
    await page.click('.tab:has-text("Domains")');

    // Wait for domains to load
    await page.waitForTimeout(1000);

    // Verify domain cards are displayed
    const domainCards = page.locator('#domains-tab .agent-card');
    const count = await domainCards.count();
    expect(count).toBeGreaterThan(0);

    // Check for specific domains
    await expect(page.locator('#domains-tab:has-text("Preventive Screening")')).toBeVisible();
    await expect(page.locator('#domains-tab:has-text("Clinical Trial")')).toBeVisible();
  });

  test('should display templates in Templates tab', async ({ page }) => {
    // Click on Templates tab
    await page.click('.tab:has-text("Templates")');

    // Wait for templates to load
    await page.waitForTimeout(1000);

    // Verify template cards are displayed
    const templateCards = page.locator('#templates-tab .agent-card');
    const count = await templateCards.count();
    expect(count).toBeGreaterThan(0);

    // Check for BCS-E template
    await expect(page.locator('#templates-tab:has-text("Breast Cancer Screening")')).toBeVisible();
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Intercept API call and force error
    await page.route('**/api/agents/**', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Internal server error' })
      });
    });

    // Try to create sample agent
    const content = await page.locator('#agentsContainer').textContent();
    if (content && content.includes('Create BCS-E Sample Agent')) {
      await page.click('button:has-text("Create BCS-E Sample Agent")');

      // Wait for error message
      await page.waitForSelector('.alert-error', { timeout: 5000 });

      // Verify error is displayed
      await expect(page.locator('.alert-error')).toBeVisible();
    }
  });

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Verify page is still functional
    await expect(page.locator('.header h1')).toBeVisible();
    await expect(page.locator('button:has-text("Create New Agent")')).toBeVisible();
    await expect(page.locator('.tabs')).toBeVisible();
  });

  test('should persist state when switching tabs', async ({ page }) => {
    // Select a filter
    await page.selectOption('#filterStatus', 'active');

    // Switch to another tab
    await page.click('.tab:has-text("Templates")');

    // Switch back
    await page.click('.tab:has-text("All Agents")');

    // Verify filter is still selected
    const selectedValue = await page.locator('#filterStatus').inputValue();
    expect(selectedValue).toBe('active');
  });

  test('should display capability badges for agents', async ({ page }) => {
    await page.waitForTimeout(1000);

    // Create sample agent if needed
    const content = await page.locator('#agentsContainer').textContent();
    if (content && content.includes('Create BCS-E Sample Agent')) {
      await page.click('button:has-text("Create BCS-E Sample Agent")');
      await page.waitForTimeout(1500);
    }

    // Find first agent card and check for capability badges
    const agentCard = page.locator('.agent-card').first();
    const badges = agentCard.locator('.badge');
    const count = await badges.count();

    // Should have at least one capability badge
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('Agent Management API Integration', () => {

  test('should load agents from API', async ({ page }) => {
    // Spy on API calls
    let apiCalled = false;
    await page.route('**/api/agents/', route => {
      apiCalled = true;
      route.continue();
    });

    await page.goto(`${BASE_URL}/agents`);
    await page.waitForTimeout(1000);

    // Verify API was called
    expect(apiCalled).toBe(true);
  });

  test('should load domains from API', async ({ page }) => {
    // Spy on API calls
    let apiCalled = false;
    await page.route('**/api/agents/domains/list', route => {
      apiCalled = true;
      route.continue();
    });

    await page.goto(`${BASE_URL}/agents`);
    await page.waitForTimeout(1000);

    // Verify API was called
    expect(apiCalled).toBe(true);
  });

  test('should load templates from API', async ({ page }) => {
    // Spy on API calls
    let apiCalled = false;
    await page.route('**/api/agents/templates/list', route => {
      apiCalled = true;
      route.continue();
    });

    await page.goto(`${BASE_URL}/agents`);
    await page.waitForTimeout(1000);

    // Verify API was called
    expect(apiCalled).toBe(true);
  });
});
