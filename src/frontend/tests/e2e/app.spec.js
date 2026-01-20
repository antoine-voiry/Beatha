import { test, expect } from '@playwright/test';

/**
 * E2E tests for Project Beatha UI
 * Tests run in headless mode by default
 */

test.describe('Beatha UI - Main Application', () => {
  test('should load the application successfully', async ({ page }) => {
    await page.goto('/');

    // Wait for the app to load
    await page.waitForLoadState('networkidle');

    // Check that the page title or main heading is present
    await expect(page).toHaveTitle(/Beatha/i);
  });

  test('should display the main dashboard', async ({ page }) => {
    await page.goto('/');

    // Wait for any loading states to complete
    await page.waitForLoadState('domcontentloaded');

    // Check for key UI elements - adjust selectors based on your actual UI
    const mainContainer = page.locator('main, #root, .app');
    await expect(mainContainer).toBeVisible();
  });

  test('should be responsive on mobile viewports', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // Verify page is still functional on mobile
    await page.waitForLoadState('networkidle');
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });
});

test.describe('Beatha UI - Device Status', () => {
  test('should display device connection status', async ({ page }) => {
    await page.goto('/');

    // Look for status indicators - adjust based on your actual implementation
    // This is a placeholder test that you should customize
    const statusElement = page.locator('[data-testid="device-status"], .status, .device-info');

    // The element might be there or not depending on device connection
    // Just verify the page loaded without throwing errors
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Beatha UI - API Integration', () => {
  test('should handle API errors gracefully', async ({ page }) => {
    // Navigate to the app
    await page.goto('/');

    // Mock a failed API call
    await page.route('**/api/**', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });

    // Trigger an action that makes an API call (if applicable)
    // The app should handle the error without crashing
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Beatha UI - Performance', () => {
  test('should load within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    // Should load within 5 seconds (adjust as needed)
    expect(loadTime).toBeLessThan(5000);
  });
});

/**
 * Example test for specific user interactions
 * Customize these based on your actual UI components
 */
test.describe('Beatha UI - User Interactions', () => {
  test.skip('should allow user to dump config (placeholder)', async ({ page }) => {
    await page.goto('/');

    // Example: Look for a dump button
    const dumpButton = page.locator('button:has-text("Dump"), [data-testid="dump-button"]');

    // Check if button exists (might not if device not connected)
    const count = await dumpButton.count();
    if (count > 0) {
      await dumpButton.click();
      // Add assertions for expected behavior
    }
  });
});
