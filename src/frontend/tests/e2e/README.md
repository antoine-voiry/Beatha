# Playwright E2E Tests

This directory contains end-to-end tests for the Beatha UI using Playwright.

## Running Tests

### Silent/Headless Mode (Default)
```bash
npm test
```

This runs tests in headless mode across all configured browsers (Chromium, Firefox, WebKit).

### Headed Mode (See Browser)
```bash
npm run test:headed
```

### Interactive UI Mode
```bash
npm run test:ui
```

Opens Playwright's UI mode for interactive test development and debugging.

### Debug Mode
```bash
npm run test:debug
```

Runs tests with Playwright Inspector for step-by-step debugging.

### View Test Report
```bash
npm run test:report
```

Opens the HTML report from the last test run.

### Run Specific Browser
```bash
npm run test:chromium
npm run test:mobile
```

## Test Structure

- `app.spec.js` - Main application tests
  - Basic page loading
  - Responsive design
  - API integration
  - Performance checks

## Configuration

Tests are configured in `playwright.config.js`:
- **Headless by default**: Set `HEADED=true` to see browser
- **Base URL**: `http://localhost:5173` (Vite dev server)
- **Browsers**: Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari
- **Reports**: HTML report in `playwright-report/`
- **Videos**: Recorded on failure
- **Screenshots**: Captured on failure

## Writing Tests

Example test structure:

```javascript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test('should do something', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('selector')).toBeVisible();
  });
});
```

## CI/CD Integration

Tests automatically:
- Run in headless mode
- Retry failed tests 2 times
- Generate JSON and HTML reports
- Capture screenshots/videos on failure

## First Time Setup

Install browser binaries:

```bash
npx playwright install
```

This downloads Chromium, Firefox, and WebKit browsers for testing.

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Playwright Test API](https://playwright.dev/docs/api/class-test)
- [Selectors Guide](https://playwright.dev/docs/selectors)
