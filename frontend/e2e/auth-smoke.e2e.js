import { expect, test } from '@playwright/test';

test('login screen uses the SandeshVani theme and accessible form labels', async ({ page }) => {
  await page.goto('/');

  await expect(page).toHaveTitle('SandeshVani');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'sandeshvani');
  await expect(page.getByRole('heading', { name: 'Institutional Sign In' })).toBeVisible();
  await expect(page.getByLabel(/Institutional Email/)).toBeVisible();
  await expect(page.getByLabel(/^Password/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
});

test('login validation, registration and password recovery navigation work without an API', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByRole('alert')).toContainText('Please enter both email and password.');

  await page.getByRole('button', { name: 'Create an account' }).click();
  await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible();
  await expect(page.getByLabel(/^Full Name/)).toBeVisible();
  await expect(page.getByLabel(/Institutional Email/)).toBeVisible();

  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByRole('button', { name: 'Forgot password?' }).click();
  await expect(page.getByRole('heading', { name: 'Recover Password' })).toBeVisible();
  await expect(page.getByLabel(/Institutional Email/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Send Recovery Link' })).toBeVisible();
});

test('verification and reset-token URLs render the correct forms', async ({ page }) => {
  await page.goto('/?verify_token=browser-smoke-token');
  await expect(page.getByRole('heading', { name: 'Verify Email Address' })).toBeVisible();
  await expect(page.getByLabel(/Verification Token/)).toBeVisible();

  await page.goto('/?reset_token=browser-smoke-token');
  await expect(page.getByRole('heading', { name: 'Set New Password' })).toBeVisible();
  await expect(page.getByLabel(/Recovery Token/)).toHaveValue('browser-smoke-token');
  await expect(page.getByLabel(/^New Password/)).toBeVisible();
});

test('keyboard navigation exposes the visible focus indicator', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === 'mobile-chromium', 'Keyboard-only focus is checked in desktop Chromium.');
  await page.goto('/');
  await page.keyboard.press('Tab');

  const email = page.getByLabel(/Institutional Email/);
  await expect(email).toBeFocused();
  await expect.poll(() => email.evaluate((element) => getComputedStyle(element).outlineWidth)).toBe('2px');
});

test('authenticated dashboard remains usable with sandbox-only sample data', async ({ page }) => {
  await page.route('**/api/v1/auth/refresh', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ access_token: 'browser-test-access-token', csrf_token: 'browser-test-csrf-token' }),
  }));
  await page.route('**/api/v1/auth/me', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      user: { id: 'browser-user', email: 'operator@example.test', full_name: 'Browser Operator' },
      active_organization: { id: 'browser-org', name: 'Browser Test Department', slug: 'browser-test' },
      organizations: [{ id: 'browser-org', name: 'Browser Test Department', slug: 'browser-test', status: 'active' }],
      roles: ['org_admin'],
      permissions: [],
    }),
  }));

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Sandbox Environment Banner' })).toContainText('No real SMS');
  await expect(page.getByText('Sample data')).toBeVisible();
  await expect(page.getByText('Dengue prevention advisory').first()).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Recent campaigns' })).toBeVisible();

  await expect(page.getByRole('button', { name: 'Approve', exact: true }).first()).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Reject', exact: true }).first()).toBeDisabled();

  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
});
