import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { apiClient } from "@/api/client";
import { EvaluationLabPage } from "@/pages/EvaluationLabPage";
import type { Schema } from "@/api/client";

function renderEvaluationLab() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <EvaluationLabPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Evaluation Lab Rubric Requirements (§14 & §11.6)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders permanent honesty panel and never writes 'accuracy' or '99%'", async () => {
    renderEvaluationLab();

    // 1. Permanent Honesty Panel is visible
    await waitFor(() => {
      expect(
        screen.getByText(
          /Positives are synthetic; negatives are real captured namesakes labelled by the team\. Small sample, see intervals\./i
        )
      ).toBeInTheDocument();
      // 2. Limitations are rendered once latest evaluation resolves
      expect(
        screen.getByText(/Small sample; see confidence intervals\./i)
      ).toBeInTheDocument();
    });

    // 3. Guardrail: Never write "accuracy" or "99%"
    const bodyText = document.body.textContent || "";
    expect(bodyText.toLowerCase()).not.toContain("accuracy");
    expect(bodyText).not.toContain("99%");
  });

  it("renders null metrics as 'Not defined' (never zero)", async () => {
    // Mock getLatestEvaluation returning null metrics
    const nullEval: Schema["EvaluationResult"] = {
      id: "eval-null-test",
      dataset_id: "threatlens-v1",
      split: "HELDOUT",
      scoring_version: "3.0.0",
      threshold: { review: 25 },
      sample_count: 10,
      confusion: { tp: 0, fp: 0, tn: 10, fn: 0 },
      precision: null,
      recall: null,
      f1: null,
      false_positive_rate: null,
      confidence_intervals: {
        precision: null,
        recall: null,
        false_positive_rate: null,
        method: "wilson_95",
      },
      official_flagged_count: 0,
      hard_negatives: { tested: 10, correctly_cleared: 10, false_positives: 0 },
      technique_recall: [],
      baseline: {
        name: "name_only_rapidfuzz",
        tuned_on: "DEV",
        precision: 0.5,
        recall: 0.5,
        false_positive_rate: 0.2,
      },
      ablation: [],
      failure_cases: [],
      definitions: "Positive class = IMPERSONATION.",
      limitations: ["Test null metrics."],
      created_at: "2026-10-12T00:00:00Z",
    };

    vi.spyOn(apiClient, "getLatestEvaluation").mockResolvedValue(nullEval);

    renderEvaluationLab();

    await waitFor(() => {
      // Must render "Not defined" instead of 0 or NaN
      const notDefinedElements = screen.getAllByText("Not defined");
      expect(notDefinedElements.length).toBeGreaterThanOrEqual(4);
    });
  });

  it("shows failure when official_flagged_count > 0, and PASS when official_flagged_count == 0", async () => {
    // 1. Failing run with official_flagged_count = 3
    const failingEval = await apiClient.getLatestEvaluation({ split: "HELDOUT" });
    failingEval.official_flagged_count = 3;

    vi.spyOn(apiClient, "getLatestEvaluation").mockResolvedValue(failingEval);

    const { unmount } = renderEvaluationLab();

    await waitFor(() => {
      expect(screen.getByText(/FAIL: 3 official assets flagged/i)).toBeInTheDocument();
    });

    unmount();

    // 2. Passing run with official_flagged_count = 0
    failingEval.official_flagged_count = 0;
    vi.spyOn(apiClient, "getLatestEvaluation").mockResolvedValue(failingEval);

    renderEvaluationLab();

    await waitFor(() => {
      expect(screen.getByText(/PASS: 0 official assets flagged/i)).toBeInTheDocument();
    });
  });

  it("always displays Wilson 95% confidence intervals on headline metrics", async () => {
    renderEvaluationLab();

    await waitFor(() => {
      expect(screen.getByText("Headline Evaluation Metrics")).toBeInTheDocument();
      // Confidence intervals formatted as [low, high]
      expect(screen.getByText(/\[0\.72, 0\.99\]/)).toBeInTheDocument();
      expect(screen.getByText(/\[0\.66, 0\.97\]/)).toBeInTheDocument();
      expect(screen.getByText(/\[0\.01, 0\.16\]/)).toBeInTheDocument();
    });

    // Wilson 95% CI text labels must be present
    expect(screen.getAllByText(/Wilson 95% CI:/i).length).toBeGreaterThanOrEqual(3);
  });

  it("renders dataset composition bars and dataset limitations", async () => {
    renderEvaluationLab();

    await waitFor(() => {
      expect(screen.getByText("Dataset Composition")).toBeInTheDocument();
      expect(screen.getByText("120 cases")).toBeInTheDocument();
    });

    // Composition labels
    expect(screen.getByText("By Label")).toBeInTheDocument();
    expect(screen.getByText("By Provenance")).toBeInTheDocument();
    expect(screen.getByText("By Split")).toBeInTheDocument();

    // Provenance breakdown
    expect(screen.getByText(/Real Captured \(70\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Synthetic \(50\)/i)).toBeInTheDocument();

    // Split breakdown
    expect(screen.getByText(/DEV \(72\)/i)).toBeInTheDocument();
    expect(screen.getByText(/HELDOUT \(48\)/i)).toBeInTheDocument();
  });

  it("renders confusion matrix, baseline comparison, ablation table, and failure cases", async () => {
    renderEvaluationLab();

    await waitFor(() => {
      expect(screen.getByText("Confusion Matrix")).toBeInTheDocument();
    });

    // Confusion matrix cells
    expect(screen.getByText("True Positives (TP)")).toBeInTheDocument();
    expect(screen.getByText("False Positives (FP)")).toBeInTheDocument();
    expect(screen.getByText("False Negatives (FN)")).toBeInTheDocument();
    expect(screen.getByText("True Negatives (TN)")).toBeInTheDocument();

    // Definitions text from response
    expect(
      screen.getByText(
        /Positive class = IMPERSONATION\. Predicted positive = decision CANDIDATE_FOR_REVIEW\./i
      )
    ).toBeInTheDocument();

    // Baseline Comparison
    expect(
      screen.getByText(/Baseline Comparison \(Name-Only RapidFuzz vs ThreatLens Full Pipeline\)/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/name_only_rapidfuzz/i)).toBeInTheDocument();

    // Ablation Table
    expect(screen.getByText("Ablation Study")).toBeInTheDocument();
    expect(screen.getByText("FULL")).toBeInTheDocument();
    expect(screen.getByText("NO_IDENTITYGUARD")).toBeInTheDocument();
    expect(screen.getByText("NO_GATES")).toBeInTheDocument();

    // Failure cases with expected, got, why
    expect(
      screen.getByText(/Audited Failure Cases \(Honest Error Analysis\)/i)
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Expected:/i).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText(/Outcome:/i).length).toBeGreaterThanOrEqual(2);
  });

  it("run panel allows selecting DEV tuning split and triggers evaluation run", async () => {
    const runSpy = vi.spyOn(apiClient, "runEvaluation");

    renderEvaluationLab();

    await waitFor(() => {
      expect(screen.getByText("Run Evaluation Harness")).toBeInTheDocument();
    });

    // Select DEV Split
    const devSplitBtn = screen.getByRole("button", { name: /DEV Split/i });
    expect(devSplitBtn).toBeInTheDocument();
    fireEvent.click(devSplitBtn);

    // Verify DEV is marked as Tuning Split
    expect(screen.getByText("Tuning Split")).toBeInTheDocument();

    // Click Run Evaluation button
    const runBtn = screen.getByRole("button", { name: /Run Evaluation \(DEV\)/i });
    expect(runBtn).toBeInTheDocument();
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(runSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          split: "DEV",
          dataset_id: "threatlens-v1",
        })
      );
    });
  });
});
