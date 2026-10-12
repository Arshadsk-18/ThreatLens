import { test, expect } from "@playwright/test";

test.describe("Findings Review & Decision Workflow (Playwright E2E)", () => {
  test("DEMO scan -> open Kaveri Bank Rewards -> Evidence Compare visible -> dismiss with reason -> disappears from default queue", async ({
    page,
  }) => {
    // 1. Launch a DEMO Scan
    await page.goto("/scan");
    await expect(page.getByRole("heading", { name: /Scan Setup & History/i })).toBeVisible();

    const demoCard = page.getByRole("button", { name: /DEMO Mode/i });
    await expect(demoCard).toBeVisible();
    await demoCard.click();

    const launchButton = page.getByRole("button", { name: /Launch DEMO Scan/i });
    await expect(launchButton).toBeEnabled();
    await launchButton.click();

    // Wait for scan to progress and complete
    await page.waitForURL(/\/scan\/scan-/);
    await expect(page.getByText("100%")).toBeVisible({ timeout: 25000 });

    // 2. Open Findings Queue
    const reviewFindingsButton = page.getByRole("link", { name: /Review Findings/i });
    await expect(reviewFindingsButton).toBeVisible();
    await reviewFindingsButton.click();

    await page.waitForURL(/\/findings/);
    await expect(page.getByRole("heading", { name: /Findings Review Queue/i })).toBeVisible();

    // 3. Verify Kaveri Bank Rewards candidate is present in queue
    const rewardsRowLink = page.getByRole("link", { name: "Kaveri Bank Rewards" });
    await expect(rewardsRowLink).toBeVisible();

    // 4. Open Kaveri Bank Rewards detail page
    await rewardsRowLink.click();
    await page.waitForURL(/\/findings\/f1000000-/);

    // Verify Detail Page Header and Score Banner
    await expect(page.getByRole("heading", { name: "Kaveri Bank Rewards" })).toBeVisible();
    await expect(
      page.getByText("Risk score 72 / 100 (not a probability)")
    ).toBeVisible();

    // Verify "How this score was built" panel
    await expect(page.getByText("How this score was built")).toBeVisible();
    await expect(
      page.getByText(/Corroborating groups: Visual, Content, Context\. The name group never counts as corroboration\./i)
    ).toBeVisible();

    // 5. Verify Evidence Compare is visible
    await expect(page.getByText("Forensic Dimension")).toBeVisible();
    await expect(page.getByText("Forensic Name Diff")).toBeVisible();
    await expect(
      page.getByText(/Icon perceptual hash is 93% similar\. Hash similarity is not proof of copying\./i)
    ).toBeVisible();
    await expect(page.getByText("Publisher difference recorded as observable fact.")).toBeVisible();

    // 6. Record Dismissal Decision with reason
    const recordDecisionBtn = page.getByRole("button", { name: /Record Decision/i });
    await expect(recordDecisionBtn).toBeVisible();
    await recordDecisionBtn.click();

    // Dialog opens
    await expect(page.getByText("Record Analyst Decision")).toBeVisible();

    // Select Dismissed (False Positive)
    const dismissCard = page.getByText("Dismissed (False Positive)");
    await dismissCard.click();

    // Provide mandatory decision reason
    const reasonInput = page.locator("#decision-reason");
    await reasonInput.fill("Verified legitimate partner loyalty platform following manual brand clearance.");

    // Submit decision
    const saveDecisionBtn = page.getByRole("button", { name: /Save Decision/i });
    await saveDecisionBtn.click();

    // Dialog closes
    await expect(page.getByText("Record Analyst Decision")).not.toBeVisible();

    // 7. Navigate back to default queue
    const backLink = page.getByRole("link", { name: /Back to Findings Queue/i });
    await backLink.click();
    await page.waitForURL("/findings");

    // 8. Confirm Kaveri Bank Rewards disappears from the default queue (since include_dismissed is false)
    await expect(page.getByRole("link", { name: "Kaveri Bank Rewards" })).not.toBeVisible();

    // Verify that checking "Include dismissed false positives" reveals the dismissed finding
    const includeDismissedCheckbox = page.getByLabel("Include dismissed false positives");
    await includeDismissedCheckbox.check();

    await expect(page.getByRole("link", { name: "Kaveri Bank Rewards" })).toBeVisible();
    await expect(page.getByText("Dismissed (false positive)")).toBeVisible();
  });
});
