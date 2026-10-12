import { test, expect } from "@playwright/test";

test.describe("ThreatLens End-to-End Scan & Brand Flow", () => {
  test("brand profile view -> start DEMO scan -> polls pipeline stages -> reaches COMPLETED with funnel & outcomes", async ({
    page,
  }) => {
    // 1. Visit Brand Profile & Asset Registry
    await page.goto("/brand");

    // Check header and core sections
    await expect(
      page.getByRole("heading", { name: /Brand Profile & Asset Registry/i })
    ).toBeVisible();
    await expect(page.getByText("How This Profile Drives Detection")).toBeVisible();
    await expect(page.getByText("Official Assets Registry")).toBeVisible();

    // Check brand form input values
    const brandNameInput = page.locator("#brand-name");
    await expect(brandNameInput).toBeVisible({ timeout: 10000 });
    await expect(brandNameInput).toHaveValue("Kaveri Bank");

    // 2. Navigate to Scan Setup
    await page.goto("/scan");
    await expect(
      page.getByRole("heading", { name: /Scan Setup & History/i })
    ).toBeVisible();

    // Verify Mode Cards
    const demoCard = page.getByRole("button", { name: /DEMO Mode/i });
    await expect(demoCard).toBeVisible();
    await demoCard.click();

    // Verify DEMO fixtures are selected
    await expect(page.getByText("ThreatLens Demo Fixtures")).toBeVisible();

    // 3. Launch DEMO Scan
    const launchButton = page.getByRole("button", { name: /Launch DEMO Scan/i });
    await expect(launchButton).toBeEnabled();
    await launchButton.click();

    // 4. Navigates to /scan/:id
    await page.waitForURL(/\/scan\/scan-/);
    await expect(
      page.getByRole("heading", { name: /Scan Detail/i })
    ).toBeVisible();

    // 5. Poll until scan completes (up to ~15s to allow state machine in mock.ts to advance to 100%)
    await expect(page.getByText("100%")).toBeVisible({ timeout: 20000 });
    await expect(page.locator("span", { hasText: "completed" }).first()).toBeVisible();

    // 6. Verify Detection & Filtering Funnel and Invariant Arithmetic Note
    await expect(page.getByText("Detection & Filtering Funnel")).toBeVisible();
    await expect(
      page.getByText(
        /Invariant note: 60 \(deduplicated\) = 5 \(cleared\) \+ 29 \(not relevant\) \+ 14 \(benign lookalike\) \+ 0 \(below threshold\) \+ 12 \(findings\)\./i
      )
    ).toBeVisible();

    // 7. Verify Per-Source Outcome Cards
    await expect(page.getByText("Per-Source Query Outcomes")).toBeVisible();
    await expect(page.getByText("apple_itunes", { exact: true })).toBeVisible();
    await expect(page.getByText("bluesky_public", { exact: true })).toBeVisible();
    await expect(
      page.getByText(/not connected\. No official API; not queried\. Not queried\./i)
    ).toBeVisible();

    // 8. Verify Review Findings Link is visible and click through
    const reviewFindingsButton = page.getByRole("link", {
      name: /Review Findings/i,
    });
    await expect(reviewFindingsButton).toBeVisible();
    await reviewFindingsButton.click();

    await page.waitForURL(/\/findings\?scan_id=/);

    // 9. Navigate to Cleared Items from findings header link
    const clearedLink = page.getByRole("link", {
      name: /cleared by rules/i,
    });
    await expect(clearedLink).toBeVisible();
    await clearedLink.click();

    await page.waitForURL(/\/cleared/);
    await expect(
      page.getByRole("heading", { name: /Cleared Assets Registry/i })
    ).toBeVisible();

    // Verify Decision Tabs are present
    await expect(page.getByRole("button", { name: /Official exact ID/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Official publisher ID/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Benign lookalike/i })).toBeVisible();

    // Verify exact copy for R1_EXACT_ID in default / first tab
    await expect(page.getByText("R1_EXACT_ID").first()).toBeVisible();
    await expect(
      page.getByText(/Cleared: exact bundle ID match with registered official app com\.kaveribank\.mobile\./i).first()
    ).toBeVisible();

    // Switch to Official publisher ID tab and verify R2 copy
    await page.getByRole("button", { name: /Official publisher ID/i }).click();
    await expect(page.getByText("R2_PUBLISHER_ID").first()).toBeVisible();
    await expect(
      page.getByText("Published by the registered developer. Consider registering this app.").first()
    ).toBeVisible();

    // Switch to Benign lookalike tab and verify G4 & G5 copy
    await page.getByRole("button", { name: /Benign lookalike/i }).click();
    await expect(
      page.getByText("Similar name, unrelated category, no corroborating evidence.").first()
    ).toBeVisible();
    await expect(
      page.getByText(
        "Declared unofficial in its bio. Not verified. Disclaimers can be copied by impersonators; an analyst may reopen this."
      ).first()
    ).toBeVisible();
    await expect(
      page.getByText("Declared unofficial, not verified").first()
    ).toBeVisible();
    await expect(
      page.getByText(/\(score capped: G4\/G5 prevents candidate reaching alert threshold\)/i).first()
    ).toBeVisible();

    // Verify Reopen button is disabled
    const reopenBtn = page.getByRole("button", { name: /Reopen \(P1\)/i }).first();
    await expect(reopenBtn).toBeVisible();
    await expect(reopenBtn).toBeDisabled();

    // 10. Navigate to Source Coverage (/sources)
    await page.getByRole("link", { name: /Source Coverage/i }).first().click();
    await page.waitForURL(/\/sources/);
    await expect(
      page.getByRole("heading", { name: /Source Coverage/i })
    ).toBeVisible();

    // Verify Legend and explanation
    await expect(page.getByText(/Source Modes & Status Legend/i)).toBeVisible();
    await expect(page.getByText(/Real-time query sent directly to platform catalog APIs\./i)).toBeVisible();

    // Verify Provider Cards
    await expect(page.getByText("Apple App Store search").first()).toBeVisible();
    await expect(page.getByText("Bluesky Public Directory").first()).toBeVisible();
    await expect(page.getByText("Instagram Graph API").first()).toBeVisible();
    await expect(page.getByText("X (Twitter) API v2").first()).toBeVisible();

    // Click "Check now" button to verify refresh flow
    const checkNowBtn = page.getByRole("button", { name: /Check now/i });
    await expect(checkNowBtn).toBeVisible();
    await checkNowBtn.click();
    await expect(page.getByRole("heading", { name: /Source Coverage/i })).toBeVisible();

    // 11. Navigate to Overview (/)
    await page.getByRole("link", { name: /Overview/i }).first().click();
    await page.waitForURL("/");
    await expect(
      page.getByRole("heading", { name: /Kaveri Bank/i })
    ).toBeVisible();

    // Verify black greeting banner and demo brand badge
    await expect(page.getByText(/Demo brand Kaveri Bank/i)).toBeVisible();
    const startScanBtn = page.getByRole("link", { name: /Start scan/i });
    await expect(startScanBtn).toBeVisible();

    // Verify KPI tiles
    await expect(page.getByText("Candidates for review").first()).toBeVisible();
    await expect(page.getByText("Cleared by rules").first()).toBeVisible();
    await expect(page.getByText("Official assets registered").first()).toBeVisible();
    await expect(page.getByText("Last Scan").first()).toBeVisible();

    // Verify Detection & Filtering Funnel
    await expect(page.getByText("Detection & Filtering Funnel").first()).toBeVisible();

    // Verify Review progress gauge
    await expect(page.getByText("Review progress").first()).toBeVisible();

    // Verify Source Coverage Strip
    await expect(page.getByText("Source Coverage").first()).toBeVisible();

    // Verify Last Scan Events Live Feed
    await expect(page.getByText(/Last Scan Pipeline Event Feed/i)).toBeVisible();
  });
});

