import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { apiClient } from "@/api/client";
import { WelcomePage } from "@/pages/WelcomePage";

function renderWelcomePage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <WelcomePage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Welcome Landing Page (/welcome) Rubric Requirements", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders Hero with exact headline, subhead, and CTA links", async () => {
    renderWelcomePage();

    // Headline & subhead
    expect(screen.getByRole("heading", { name: "Names can lie. IDs can't." })).toBeInTheDocument();
    expect(
      screen.getByText(
        /ThreatLens finds look-alike apps and social accounts, clears the official ones by exact ID, and shows the evidence behind every candidate for review\./i
      )
    ).toBeInTheDocument();

    // CTAs
    const workspaceLinks = screen.getAllByRole("link", { name: /Open the demo workspace/i });
    expect(workspaceLinks.length).toBeGreaterThan(0);
    expect(workspaceLinks[0]).toHaveAttribute("href", "/");

    const scrollLink = screen.getByRole("link", { name: /See how a finding is built/i });
    expect(scrollLink).toHaveAttribute("href", "#evidence-compare");
  });

  it("The Lens: switches candidate techniques and displays U+0456 chip on homoglyph", async () => {
    renderWelcomePage();

    // Official reference is always visible (both in hero lens and miniature compare)
    expect(screen.getAllByText("Official Reference").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Kaveri Bank").length).toBeGreaterThan(0);

    // Initial technique is Homoglyph
    expect(screen.getByText(/Technique: HOMOGLYPH/i)).toBeInTheDocument();
    expect(screen.getByText("U+0456")).toBeInTheDocument();

    // Switch to Character swap
    const swapBtn = screen.getByRole("button", { name: "Character swap" });
    fireEvent.click(swapBtn);
    expect(screen.getByText(/Technique: CHARACTER_SWAP/i)).toBeInTheDocument();
    expect(screen.getAllByText("Bnak").length).toBeGreaterThan(0);

    // Switch to Spacing
    const spacingBtn = screen.getByRole("button", { name: "Spacing" });
    fireEvent.click(spacingBtn);
    expect(screen.getByText(/Technique: SPACING/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Inserted internal space/i).length).toBeGreaterThan(0);

    // Switch to Added word
    const addedWordBtn = screen.getByRole("button", { name: "Added word" });
    fireEvent.click(addedWordBtn);
    expect(screen.getAllByText(/Technique: ADDED_WORD/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Rewards/).length).toBeGreaterThan(0);

    // Switch to Separator
    const separatorBtn = screen.getByRole("button", { name: "Separator" });
    fireEvent.click(separatorBtn);
    expect(screen.getByText(/Technique: SEPARATOR/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Hyphen substitution/i).length).toBeGreaterThan(0);

    // Switch back to Homoglyph and verify U+0456 chip reappears
    const homoglyphBtn = screen.getByRole("button", { name: "Homoglyph" });
    fireEvent.click(homoglyphBtn);
    expect(screen.getByText(/Technique: HOMOGLYPH/i)).toBeInTheDocument();
    expect(screen.getByText("U+0456")).toBeInTheDocument();
  });

  it("scans all text on /welcome and strictly verifies zero banned words", async () => {
    const { container } = renderWelcomePage();
    const allText = container.textContent || "";
    const lowerText = allText.toLowerCase();

    // Strictly forbidden words per contract rules
    expect(lowerText).not.toMatch(/\bfake\b/);
    expect(lowerText).not.toMatch(/\bscam\b/);
    expect(lowerText).not.toMatch(/\bmalicious\b/);
    expect(lowerText).not.toMatch(/\bphishing\b/);
  });

  it("Section 7: never renders a number without an API value, and shows 'No evaluation run yet' on failure", async () => {
    // Force evaluation API to fail
    vi.spyOn(apiClient, "getLatestEvaluation").mockRejectedValue(new Error("Network offline"));

    renderWelcomePage();

    await waitFor(() => {
      expect(screen.getByText("No evaluation run yet.")).toBeInTheDocument();
    });

    // Verify no fake or defaulted metric numbers are shown in Section 7
    const section7 = screen.getByRole("region", { name: /Measured, not claimed/i });
    expect(section7).toHaveTextContent("No evaluation run yet.");
    expect(section7).not.toHaveTextContent("Precision 0.00");
    expect(section7).not.toHaveTextContent("Recall 0.00");
  });

  it("Section 7: renders Wilson 95% intervals and required copy when API evaluation data exists", async () => {
    renderWelcomePage();

    await waitFor(() => {
      expect(
        screen.getByText(
          /Positives are synthetic; negatives are real captured namesakes labelled by the team\./i
        )
      ).toBeInTheDocument();
      expect(screen.getAllByText(/95% CI: \[0\.\d{2}, 0\.\d{2}\]/i).length).toBeGreaterThan(0);
    });

    // Zero accuracy claims
    const section7 = screen.getByRole("region", { name: /Measured, not claimed/i });
    expect(section7.textContent?.toLowerCase()).not.toContain("accuracy");
    expect(section7.textContent).not.toContain("99%");
  });

  it("renders Sections 2, 3, 4, 5, 6, Closing, and Footer per specifications", async () => {
    renderWelcomePage();

    // Section 2: Rules we do not break (5 panels, no numbering)
    expect(screen.getByRole("heading", { name: "Rules we do not break" })).toBeInTheDocument();
    expect(screen.getAllByText("Candidates for review, not verdicts.").length).toBe(2);
    expect(screen.getByText("Identity by ID, never by name.")).toBeInTheDocument();
    expect(screen.getByText("Missing evidence is not evidence.")).toBeInTheDocument();
    expect(screen.getByText("No silent fallbacks.")).toBeInTheDocument();
    expect(screen.getByText("Scores are not probabilities.")).toBeInTheDocument();

    // Section 3: From brand profile to decision (7 steps)
    expect(screen.getByRole("heading", { name: "From brand profile to decision" })).toBeInTheDocument();
    expect(screen.getByText("Register official assets")).toBeInTheDocument();
    expect(screen.getByText("Plan queries")).toBeInTheDocument();
    expect(screen.getByText("Fetch sources")).toBeInTheDocument();
    expect(screen.getByText("Hash icons")).toBeInTheDocument();
    expect(screen.getByText("IdentityGuard")).toBeInTheDocument();
    expect(screen.getByText("Score with gates")).toBeInTheDocument();
    expect(screen.getByText("Analyst decision")).toBeInTheDocument();
    expect(screen.getByText("Clearing Point")).toBeInTheDocument();

    // Section 4: Official assets are cleared by identity
    expect(
      screen.getByRole("heading", { name: "Official assets are cleared by identity" })
    ).toBeInTheDocument();
    expect(
      screen.getByText("Name similarity finds suspects. It never clears anyone.")
    ).toBeInTheDocument();
    expect(screen.getByText("R1_EXACT_ID")).toBeInTheDocument();
    expect(screen.getByText("R2_PUBLISHER_ID")).toBeInTheDocument();
    expect(screen.getByText("R3_PARTNER")).toBeInTheDocument();

    // Section 5: See exactly why (Evidence Compare miniature)
    expect(screen.getByRole("heading", { name: "See exactly why" })).toBeInTheDocument();
    expect(screen.getByText("72 / 100")).toBeInTheDocument();
    expect(screen.getAllByText(/Simulated demo record/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Corroborating groups: Visual, Content, Context/i)).toBeInTheDocument();

    // Section 6: Honest about sources
    expect(screen.getByRole("heading", { name: "Honest about sources" })).toBeInTheDocument();
    expect(screen.getByText("A failed source is a failure, never a clean result.")).toBeInTheDocument();
    expect(screen.getByText(/Real-time query sent directly to platform catalog APIs\./i)).toBeInTheDocument();
    expect(screen.getAllByText(/Cached result from 05:12 UTC/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Requires platform API access\. Not queried\./i)).toBeInTheDocument();
    expect(screen.getByText(/Stopped after 4 of 6 queries; partial results kept\./i)).toBeInTheDocument();

    // Footer
    expect(
      screen.getByText(/HacXLerate 2026 · Challenge 3: Digital Risk Protection/i)
    ).toBeInTheDocument();
  });
});
