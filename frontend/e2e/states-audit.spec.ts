import { test, expect } from '@playwright/test';
import path from 'path';

const ARTIFACTS_DIR = 'C:/Users/Arshad/.gemini/antigravity-ide/brain/087d027e-448a-4582-a969-b66957b63950';

test.describe('States Audit: Loading, Empty, Error, Not-Connected, Rate-Limited', () => {
  test('1. Loading states and Skeleton accessibility', async ({ page }) => {
    // Intercept API call to delay response so we can capture loading skeleton
    await page.route('**/findings**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 800));
      await route.continue();
    });

    await page.goto('/findings');
    const loadingState = page.locator('[aria-busy="true"]');
    if (await loadingState.isVisible()) {
      await page.screenshot({
        path: path.join(ARTIFACTS_DIR, 'state_loading_skeleton.png'),
      });
    }

    // Wait for content to finish loading
    await expect(page.getByText('Findings Review Queue')).toBeVisible({ timeout: 10000 });
  });

  test('2. Empty states on Findings and Cleared registry', async ({ page }) => {
    // Empty findings queue
    await page.goto('/findings?q=NonExistentSearchToken999');
    await expect(page.getByText('No candidates for review match the selected filters.')).toBeVisible();
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'state_empty_findings.png'),
    });

    // Clear filters button is accessible
    const clearBtn = page.getByRole('button', { name: /clear active filters/i });
    await expect(clearBtn).toBeVisible();

    // Empty cleared registry
    await page.goto('/cleared?q=NonExistentClearedToken999');
    await expect(page.getByText('No cleared assets match the filter criteria.')).toBeVisible();
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'state_empty_cleared.png'),
    });
  });

  test('3. Error states displaying request_id', async ({ page }) => {
    // 404 finding error
    await page.goto('/findings/unknown-finding-xyz');
    await expect(page.getByText('Finding Not Found')).toBeVisible();
    const requestIdEl = page.locator('text=/Request ID: req-[a-z0-9-]+/');
    await expect(requestIdEl).toBeVisible();
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'state_error_finding_not_found.png'),
    });

    // 404 scan error
    await page.goto('/scan/nonexistent-scan-id');
    await expect(page.getByText('Scan Not Found or Inaccessible')).toBeVisible();
    await expect(page.locator('text=/Request ID: req-[a-z0-9-]+/')).toBeVisible();
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'state_error_scan_not_found.png'),
    });
  });

  test('4. NOT_CONNECTED sources state in Scan Setup & Sources', async ({ page }) => {
    // Scan Setup screen
    await page.goto('/scan');
    await expect(page.getByText('3. Connected Provider Sources')).toBeVisible();

    // Verify Not connected badge
    const notConnectedBadges = page.getByText('Not connected');
    await expect(notConnectedBadges.first()).toBeVisible();

    // Verify copy explaining requirement
    await expect(page.getByText(/not connected\. Requires platform API access\. Not queried\./i).first()).toBeVisible();
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'state_not_connected_scan_setup.png'),
    });

    // Sources Screen
    await page.goto('/sources');
    await expect(page.getByText('Source Coverage & Provider Health')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Instagram Graph API' })).toBeVisible();
    await expect(page.getByRole('heading', { name: /X \(Twitter\) API/i })).toBeVisible();
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'state_sources_coverage.png'),
    });
  });

  test('5. RATE_LIMITED source in Scan Detail outcomes', async ({ page }) => {
    await page.goto('/scan/scan-demo-001');
    await expect(page.getByText('Per-Source Query Outcomes')).toBeVisible();

    // Rate limited badge for Bluesky
    const rateLimitedBadge = page.getByText('Rate limited').first();
    await expect(rateLimitedBadge).toBeVisible();

    // Rate limit detail
    await expect(page.getByText(/Stopped after 4 of 6 queries; partial results kept\./i).first()).toBeVisible();
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'state_rate_limited_and_outcomes.png'),
    });
  });
});
