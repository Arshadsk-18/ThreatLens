import { test, expect } from "@playwright/test";

test.describe("Evaluation Lab E2E Flow (§14 & §11.6 Honesty is the feature)", () => {
  test("loads /evaluation, verifies honesty banner, Wilson intervals, metrics, confusion matrix, and DEV split run", async ({
    page,
  }) => {
    // 1. Visit /evaluation
    await page.goto("/evaluation");

    // Check heading
    await expect(
      page.getByRole("heading", { name: /Evaluation Lab/i })
    ).toBeVisible();

    // 2. Permanent Honesty Panel Verification
    const honestyBanner = page.locator("div", {
      hasText: "Positives are synthetic; negatives are real captured namesakes labelled by the team. Small sample, see intervals.",
    }).first();
    await expect(honestyBanner).toBeVisible();

    // Verify dataset limitations are displayed
    await expect(page.getByText("Dataset limitations:")).toBeVisible();
    await expect(
      page.getByText(/Negatives are real captured namesakes labelled by the team/i).first()
    ).toBeVisible();

    // Strictly verify forbidden terms: never say 'accuracy' or '99%'
    const pageText = await page.innerText("body");
    expect(pageText.toLowerCase()).not.toContain("accuracy");
    expect(pageText).not.toContain("99%");

    // 3. Dataset Composition & Provenance
    await expect(page.getByRole("heading", { name: "Dataset Composition" })).toBeVisible();
    await expect(page.getByText("By Label")).toBeVisible();
    await expect(page.getByText("By Provenance")).toBeVisible();
    await expect(page.getByText("By Split")).toBeVisible();

    // 4. Headline Metrics with Wilson 95% intervals
    await expect(page.getByRole("heading", { name: "Headline Evaluation Metrics" })).toBeVisible();
    await expect(page.getByText("Precision").first()).toBeVisible();
    await expect(page.getByText("Recall").first()).toBeVisible();
    await expect(page.getByText("F1 Score").first()).toBeVisible();
    await expect(page.getByText("False-Positive Rate").first()).toBeVisible();

    // Verify Wilson 95% CI is explicitly visible for metrics
    await expect(page.getByText(/Wilson 95% CI:/i).first()).toBeVisible();
    await expect(page.getByText(/\[0\.\d{2}, 0\.\d{2}\]/i).first()).toBeVisible();

    // 5. Official Assets Flagged (Invariant: 0 flagged = PASS)
    await expect(page.getByText("PASS: 0 official assets flagged")).toBeVisible();

    // 6. Confusion Matrix with definitions
    await expect(page.getByRole("heading", { name: "Confusion Matrix" })).toBeVisible();
    await expect(page.getByText("True Positives (TP)").first()).toBeVisible();
    await expect(page.getByText("False Positives (FP)").first()).toBeVisible();
    await expect(page.getByText("False Negatives (FN)").first()).toBeVisible();
    await expect(page.getByText("True Negatives (TN)").first()).toBeVisible();
    await expect(page.getByText(/Actual impersonators correctly surfaced for review/i)).toBeVisible();

    // 7. Hard Negatives & Technique Recall
    await expect(page.getByRole("heading", { name: /Hard Negatives/i })).toBeVisible();
    await expect(page.getByText("Cleared").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Technique Recall" })).toBeVisible();

    // 8. Baseline Comparison & Ablation Study
    await expect(page.getByRole("heading", { name: /Baseline Comparison/i })).toBeVisible();
    await expect(page.getByText(/name_only_rapidfuzz \(DEV tuned\)/i)).toBeVisible();
    await expect(page.getByText(/ThreatLens Full Pipeline/i).first()).toBeVisible();

    await expect(page.getByRole("heading", { name: /Ablation Study/i })).toBeVisible();
    await expect(page.getByText("FULL").first()).toBeVisible();
    await expect(page.getByText("NO_IDENTITYGUARD").first()).toBeVisible();
    await expect(page.getByText("NO_GATES").first()).toBeVisible();

    // 9. Failure Cases
    await expect(page.getByRole("heading", { name: /Failure Cases/i })).toBeVisible();
    await expect(page.getByText(/Expected: IMPERSONATION/i).first()).toBeVisible();

    // 10. Switch split to DEV and run evaluation
    const devSplitBtn = page.getByRole("button", { name: /DEV Split/i });
    await expect(devSplitBtn).toBeVisible();
    await devSplitBtn.click();

    // Verify tuning split explanation
    await expect(
      page.getByText(/Thresholds and weights tuned only on DEV/i)
    ).toBeVisible();

    // Click "Run Evaluation (DEV)"
    const runBtn = page.getByRole("button", { name: /Run Evaluation \(DEV\)/i });
    await expect(runBtn).toBeEnabled();
    await runBtn.click();

    // Check run completion and DEV split reflection
    await expect(page.getByText("Split: DEV")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Headline Evaluation Metrics" })).toBeVisible();
  });
});
