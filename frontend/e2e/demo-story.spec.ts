import { test, expect } from "@playwright/test";

test.describe("ThreatLens 3-Minute Rehearsal & Demo Story (§18.1)", () => {
  test("Full DEMO story: /brand prefill -> DEMO scan with NOT_CONNECTED sources -> /cleared -> Evidence Compare -> /evaluation", async ({
    page,
  }) => {
    // ------------------------------------------------------------------------
    // Step 1 (0:00–0:20): Brand Profile & App Store Link Prefill
    // ------------------------------------------------------------------------
    await page.goto("/brand");
    await expect(page.getByRole("heading", { name: /Brand Profile & Asset Registry/i })).toBeVisible();

    // Verify brand name & identity
    const brandNameInput = page.locator("#brand-name");
    await expect(brandNameInput).toBeVisible({ timeout: 10000 });
    await expect(brandNameInput).toHaveValue("Kaveri Bank");

    // Open Register Official Asset Dialog for App Store link prefill
    const registerBtn = page.getByRole("button", { name: /Register Official Asset/i });
    await expect(registerBtn).toBeVisible();
    await registerBtn.click();

    // Dialog should appear
    await expect(page.getByRole("heading", { name: "Register Official Asset" })).toBeVisible();

    // Enter real App Store link
    const prefillInput = page.locator("#prefill-url");
    await expect(prefillInput).toBeVisible();
    await prefillInput.fill("https://apps.apple.com/us/app/kaveri-mobile-plus/id1524312345");

    // Click Fetch Metadata
    const fetchMetadataBtn = page.getByRole("button", { name: /Fetch Metadata/i });
    await fetchMetadataBtn.click();

    // Form step should activate and populate prefilled asset details
    const displayNameInput = page.locator("#asset-display-name");
    await expect(displayNameInput).toBeVisible({ timeout: 5000 });
    await expect(displayNameInput).toHaveValue("Kaveri Bank");

    const stableIdInput = page.locator("#asset-stable-id");
    await expect(stableIdInput).toHaveValue("1524312345");

    // Close dialog
    const closeDialogBtn = page.getByLabel("Close dialog");
    await closeDialogBtn.click();

    // ------------------------------------------------------------------------
    // Step 2 (0:20–1:00): DEMO Scan with NOT_CONNECTED Sources Visible
    // ------------------------------------------------------------------------
    await page.goto("/scan");
    await expect(page.getByRole("heading", { name: /Scan Setup & History/i })).toBeVisible();

    // Select DEMO mode card
    const demoModeCard = page.getByRole("button", { name: /DEMO Mode/i });
    await expect(demoModeCard).toBeVisible();
    await demoModeCard.click();

    // Verify sources list shows NOT_CONNECTED sources with honest copy
    await expect(page.getByText(/Google Play Catalog: not connected/i)).toBeVisible();
    await expect(page.getByText(/Instagram Graph API: not connected/i)).toBeVisible();
    await expect(page.getByText(/X \(Twitter\) API v2: not connected/i)).toBeVisible();

    // Launch DEMO scan
    const launchDemoBtn = page.getByRole("button", { name: /Launch DEMO Scan/i });
    await expect(launchDemoBtn).toBeEnabled();
    await launchDemoBtn.click();

    // Wait for scan detail page
    await page.waitForURL(/\/scan\/scan-/);
    await expect(page.getByRole("heading", { name: /Scan Detail/i })).toBeVisible();

    // Pipeline advances to completed
    await expect(page.getByText("100%")).toBeVisible({ timeout: 25000 });

    // Funnel & Invariant note verification
    await expect(page.getByText("Detection & Filtering Funnel")).toBeVisible();
    await expect(
      page.getByText(/Invariant note: 60 \(deduplicated\) = 5 \(cleared\) \+ 29 \(not relevant\) \+ 14 \(benign lookalike\) \+ 0 \(below threshold\) \+ 12 \(findings\)\./i)
    ).toBeVisible();

    // Verify Per-Source Query Outcomes: NOT_CONNECTED sources are explicitly listed
    await expect(page.getByText("Per-Source Query Outcomes")).toBeVisible();
    await expect(page.getByText("No official API; not queried.")).toBeVisible();

    // ------------------------------------------------------------------------
    // Step 3 (1:00–1:25): Cleared Assets Registry (/cleared)
    // ------------------------------------------------------------------------
    await page.goto("/cleared");
    await expect(page.getByRole("heading", { name: /Cleared Assets Registry/i })).toBeVisible();
    await expect(page.getByText(/cleared by rules/i)).toBeVisible();

    // Verify Exact ID Match (Rule R1_EXACT_ID)
    await expect(page.getByText("R1_EXACT_ID").first()).toBeVisible();
    await expect(page.getByText(/Cleared: exact bundle ID match/i)).toBeVisible();

    // Switch to Official Publisher ID tab (Rule R2_PUBLISHER_ID)
    const publisherTab = page.getByRole("button", { name: /Official Publisher ID/i });
    await publisherTab.click();
    await expect(page.getByText("R2_PUBLISHER_ID")).toBeVisible();
    await expect(
      page.getByText(/Published by the registered developer\. Consider registering this app\./i)
    ).toBeVisible();

    // Switch to Benign Lookalike tab (Gates G4 / G5)
    const benignTab = page.getByRole("button", { name: /Benign Lookalike/i });
    await benignTab.click();
    await expect(
      page.getByText(/Similar name, unrelated category, no corroborating evidence\./i).first()
    ).toBeVisible();
    await expect(
      page.getByText(/Declared unofficial in its bio\. Not verified\. Disclaimers can be copied by impersonators; an analyst may reopen this\./i).first()
    ).toBeVisible();
    await expect(page.getByText("Declared unofficial, not verified").first()).toBeVisible();

    // ------------------------------------------------------------------------
    // Step 4 (1:25–2:05): Findings Queue & Evidence Compare of Kaveri Bank Rewards
    // ------------------------------------------------------------------------
    await page.goto("/findings");
    await expect(page.getByRole("heading", { name: /Findings Review Queue/i })).toBeVisible();

    // Locate Kaveri Bank Rewards finding row
    const rewardsLink = page.getByRole("link", { name: "Kaveri Bank Rewards" });
    await expect(rewardsLink).toBeVisible();
    await rewardsLink.click();

    // Verify Evidence Compare view on Finding Detail page
    await page.waitForURL(/\/findings\/f1000000-/);
    await expect(page.getByRole("heading", { name: "Kaveri Bank Rewards" })).toBeVisible();

    // Confirm risk score is 72 / HIGH
    await expect(page.getByText("Risk score 72 / 100 (not a probability)")).toBeVisible();

    // Verify signals breakdown
    await expect(page.getByText("How this score was built")).toBeVisible();
    await expect(page.getByText(/Corroborating groups:/i)).toBeVisible();

    // Verify Evidence Compare forensic tables
    await expect(page.getByText("Forensic Dimension")).toBeVisible();
    await expect(page.getByText("Forensic Name Diff")).toBeVisible();
    await expect(
      page.getByText(/Icon perceptual hash is 93% similar\. Hash similarity is not proof of copying\./i)
    ).toBeVisible();
    await expect(page.getByText("Publisher difference recorded as observable fact.")).toBeVisible();

    // ------------------------------------------------------------------------
    // Step 5 (2:35–3:00): Evaluation Lab (/evaluation)
    // ------------------------------------------------------------------------
    await page.goto("/evaluation");
    await expect(page.getByRole("heading", { name: /Evaluation Lab/i })).toBeVisible();

    // Verify Honesty Panel
    await expect(page.getByText("Honesty is the feature")).toBeVisible();
    await expect(page.getByText(/Baseline metrics are reported on the frozen HELDOUT split/i)).toBeVisible();

    // Verify Confidence Intervals & Headline Metrics
    await expect(page.getByText("Headline Evaluation Metrics")).toBeVisible();
    await expect(page.getByText(/Wilson 95% CI:/i).first()).toBeVisible();
    await expect(page.getByText("PASS: 0 official assets flagged")).toBeVisible();

    // Verify Confusion Matrix
    await expect(page.getByText("True Positives (TP)")).toBeVisible();
    await expect(page.getByText("False Positives (FP)")).toBeVisible();
    await expect(page.getByText("True Negatives (TN)")).toBeVisible();
    await expect(page.getByText("False Negatives (FN)")).toBeVisible();

    // Verify Pipeline Ablation Table
    await expect(page.getByRole("heading", { name: "Ablation Study" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "NO_IDENTITYGUARD" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "NO_GATES" })).toBeVisible();
  });

  test("LIVE failure path: handles mock RATE_LIMITED source gracefully with honest outcome", async ({
    page,
  }) => {
    // 1. Visit scan detail for scan-demo-001 which includes a RATE_LIMITED source
    await page.goto("/scan/scan-demo-001");
    await expect(page.getByRole("heading", { name: /Scan Detail/i })).toBeVisible();

    // 2. Locate Per-Source Query Outcomes
    await expect(page.getByText("Per-Source Query Outcomes")).toBeVisible();

    // 3. Locate bluesky_public outcome card badged Rate limited
    const blueskyCard = page.locator("div", { hasText: "bluesky_public" }).first();
    await expect(blueskyCard).toBeVisible();
    await expect(blueskyCard.getByText(/Rate limited/i).first()).toBeVisible();

    // 4. Verify honest rate-limit explanation copy
    await expect(
      page.getByText("Stopped after 4 of 6 queries; partial results kept.").first()
    ).toBeVisible();

    // 5. Navigate to /sources and check provider health display
    await page.goto("/sources");
    await expect(page.getByRole("heading", { name: /Source Coverage & Provider Health/i })).toBeVisible();
    await expect(page.getByText("RATE_LIMITED / ERROR")).toBeVisible();
  });
});
