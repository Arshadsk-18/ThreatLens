import { test, expect } from "@playwright/test";

test.describe("Welcome Landing Page (/welcome) E2E Smoke Test", () => {
  test("loads /welcome outside app shell, tests interactive lens, verifies all sections, banned words, and workspace CTA", async ({
    page,
  }) => {
    // 1. Visit /welcome
    await page.goto("/welcome");

    // 2. Verify it lives OUTSIDE the app shell (no left sidebar)
    await expect(page.locator("aside")).toHaveCount(0);

    // 3. Verify Hero headline & subhead
    await expect(
      page.getByRole("heading", { name: "Names can lie. IDs can't." })
    ).toBeVisible();

    await expect(
      page.getByText(
        /ThreatLens finds look-alike apps and social accounts, clears the official ones by exact ID, and shows the evidence behind every candidate for review\./i
      )
    ).toBeVisible();

    // 4. Test THE LENS interactive technique switching
    // Check initial Homoglyph state
    await expect(page.getByText(/Technique: HOMOGLYPH/i)).toBeVisible();
    await expect(page.getByText("U+0456", { exact: true })).toBeVisible();

    // Switch to Character swap
    const swapBtn = page.getByRole("button", { name: "Character swap" });
    await expect(swapBtn).toBeVisible();
    await swapBtn.click();
    await expect(page.getByText(/Technique: CHARACTER_SWAP/i)).toBeVisible();
    await expect(page.getByText("Bnak").first()).toBeVisible();

    // Switch to Added word
    const addedWordBtn = page.getByRole("button", { name: "Added word" });
    await expect(addedWordBtn).toBeVisible();
    await addedWordBtn.click();
    await expect(page.getByText(/Technique: ADDED_WORD/i).first()).toBeVisible();

    // Switch back to Homoglyph
    const homoglyphBtn = page.getByRole("button", { name: "Homoglyph" });
    await expect(homoglyphBtn).toBeVisible();
    await homoglyphBtn.click();
    await expect(page.getByText("U+0456", { exact: true })).toBeVisible();

    // 5. Verify Section 2: Rules we do not break
    await expect(
      page.getByRole("heading", { name: "Rules we do not break" })
    ).toBeVisible();
    await expect(page.getByText("Candidates for review, not verdicts.").first()).toBeVisible();
    await expect(page.getByText("Identity by ID, never by name.")).toBeVisible();
    await expect(page.getByText("Missing evidence is not evidence.")).toBeVisible();
    await expect(page.getByText("No silent fallbacks.")).toBeVisible();
    await expect(page.getByText("Scores are not probabilities.")).toBeVisible();

    // 6. Verify Section 3: From brand profile to decision
    await expect(
      page.getByRole("heading", { name: "From brand profile to decision" })
    ).toBeVisible();
    await expect(page.getByText("Clearing Point")).toBeVisible();

    // 7. Verify Section 4: Official assets are cleared by identity
    await expect(
      page.getByRole("heading", { name: "Official assets are cleared by identity" })
    ).toBeVisible();
    await expect(
      page.getByText("Name similarity finds suspects. It never clears anyone.")
    ).toBeVisible();
    await expect(page.getByText("R1_EXACT_ID")).toBeVisible();
    await expect(page.getByText("R2_PUBLISHER_ID")).toBeVisible();
    await expect(page.getByText("R3_PARTNER")).toBeVisible();

    // 8. Verify Section 5: See exactly why (miniature Evidence Compare)
    await expect(
      page.getByRole("heading", { name: "See exactly why" })
    ).toBeVisible();
    await expect(page.getByText("72 / 100", { exact: true })).toBeVisible();
    await expect(page.getByText(/Corroborating groups: Visual, Content, Context/i)).toBeVisible();

    // 9. Verify Section 6: Honest about sources
    await expect(
      page.getByRole("heading", { name: "Honest about sources" })
    ).toBeVisible();
    await expect(
      page.getByText("A failed source is a failure, never a clean result.")
    ).toBeVisible();

    // 10. Verify Section 7: Measured, not claimed
    await expect(
      page.getByRole("heading", { name: "Measured, not claimed" })
    ).toBeVisible();

    // 11. Test Scroll Reveal, Scroll Progress Indicator & Anchor Links
    // Verify progress bar element exists
    const progressBar = page.locator("header div[aria-hidden='true']");
    await expect(progressBar).toBeAttached();

    // Scroll down to Evidence Compare
    const evidenceSection = page.locator("#evidence-compare");
    await evidenceSection.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);

    // Save scrolled mid preview screenshot
    await page.screenshot({
      path: "C:/Users/Arshad/.gemini/antigravity-ide/brain/087d027e-448a-4582-a969-b66957b63950/welcome_landing_scroll_mid.png",
    });

    // Test Back to Top floating button appears
    const backToTopBtn = page.getByRole("button", { name: /Scroll to top of page/i });
    await expect(backToTopBtn).toBeVisible();

    // Test clicking Back to Top button
    await backToTopBtn.click();
    await page.waitForTimeout(600);

    // Capture hero preview screenshot after returning
    await page.screenshot({
      path: "C:/Users/Arshad/.gemini/antigravity-ide/brain/087d027e-448a-4582-a969-b66957b63950/welcome_landing_preview.png",
    });

    // Capture full page screenshot
    await page.screenshot({
      path: "C:/Users/Arshad/.gemini/antigravity-ide/brain/087d027e-448a-4582-a969-b66957b63950/welcome_landing_full.png",
      fullPage: true,
    });

    // 12. Banned words verification on the live DOM
    const bodyText = await page.innerText("body");
    const lowerBody = bodyText.toLowerCase();
    expect(lowerBody).not.toMatch(/\bfake\b/);
    expect(lowerBody).not.toMatch(/\bscam\b/);
    expect(lowerBody).not.toMatch(/\bmalicious\b/);
    expect(lowerBody).not.toMatch(/\bphishing\b/);

    // 13. Primary CTA navigation to / (workspace)
    const primaryCta = page.getByRole("link", { name: "Open the demo workspace" }).first();
    await expect(primaryCta).toBeVisible();
    await primaryCta.click();

    // Verify workspace loaded
    await page.waitForURL("/");
    await expect(page.getByRole("heading", { name: /Kaveri Bank/i })).toBeVisible();
    // Sidebar is visible in workspace
    await expect(page.locator("aside")).toBeVisible();
  });
});
