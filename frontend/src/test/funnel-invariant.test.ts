import { describe, it, expect } from "vitest";
import { mockApiClient } from "../api/mock";
import {
  MOCK_FUNNEL,
  MOCK_FINDINGS,
  MOCK_CLEARED,
  MOCK_SOURCES_STATUS,
  SCAN_ID,
  BRAND_ID,
} from "../api/mock-data/fixtures";
import { ApiError } from "../api/errors";

describe("Funnel Invariant & Mock Dataset Compliance", () => {
  it("strictly enforces the funnel invariant: deduplicated == official_cleared + not_relevant + benign_lookalike + below_threshold + findings", () => {
    const {
      retrieved,
      deduplicated,
      official_cleared,
      not_relevant,
      benign_lookalike,
      below_threshold,
      findings,
    } = MOCK_FUNNEL;

    // Funnel equation check
    const sum = official_cleared + not_relevant + benign_lookalike + below_threshold + findings;
    expect(deduplicated).toBe(sum);
    expect(retrieved).toBeGreaterThanOrEqual(deduplicated);

    // Exact required quantities from Prompt Step 4
    expect(retrieved).toBe(64);
    expect(deduplicated).toBe(60);
    expect(official_cleared).toBe(5);
    expect(not_relevant).toBe(29);
    expect(benign_lookalike).toBe(14);
    expect(below_threshold).toBe(0);
    expect(findings).toBe(12);
  });

  it("asserts the funnel invariant on getScan(scan_id)", async () => {
    const scan = await mockApiClient.getScan(SCAN_ID);
    const { retrieved, deduplicated, official_cleared, not_relevant, benign_lookalike, below_threshold, findings } =
      scan.funnel;

    expect(deduplicated).toBe(
      official_cleared + not_relevant + benign_lookalike + below_threshold + findings
    );
    expect(retrieved).toBeGreaterThanOrEqual(deduplicated);

    // Check severity distribution: CRITICAL 2, HIGH 4, MEDIUM 6, LOW 0
    expect(scan.findings_by_severity.CRITICAL).toBe(2);
    expect(scan.findings_by_severity.HIGH).toBe(4);
    expect(scan.findings_by_severity.MEDIUM).toBe(6);
    expect(scan.findings_by_severity.LOW).toBe(0);
  });

  it("asserts the funnel invariant on newly created scans", async () => {
    const created = await mockApiClient.createScan({
      brand_id: BRAND_ID,
      mode: "DEMO",
      source_ids: ["demo_fixtures"],
    });
    expect(created.status).toBe("QUEUED");
    expect(created.stage).toBe("queued");
    expect(created.progress_percent).toBe(0);

    const scanDetail = await mockApiClient.getScan(created.id);
    const { retrieved, deduplicated, official_cleared, not_relevant, benign_lookalike, below_threshold, findings } =
      scanDetail.funnel;

    expect(deduplicated).toBe(
      official_cleared + not_relevant + benign_lookalike + below_threshold + findings
    );
    expect(retrieved).toBeGreaterThanOrEqual(deduplicated);
  });

  it("exercises the MODE_NOT_ALLOWED path when LIVE scan uses demo_fixtures", async () => {
    await expect(
      mockApiClient.createScan({
        brand_id: BRAND_ID,
        mode: "LIVE",
        source_ids: ["demo_fixtures"],
      })
    ).rejects.toThrowError(ApiError);

    try {
      await mockApiClient.createScan({
        brand_id: BRAND_ID,
        mode: "LIVE",
        source_ids: ["demo_fixtures"],
      });
    } catch (err) {
      const apiErr = err as ApiError;
      expect(apiErr.code).toBe("MODE_NOT_ALLOWED");
      expect(apiErr.status).toBe(422);
      expect(apiErr.details?.[0].issue).toContain("demo_fixtures requires DEMO mode");
    }
  });

  it("persists analyst decision on PATCH /findings and enforces decision_reason for dismiss/confirm", async () => {
    const findingId = MOCK_FINDINGS[0].id;

    // Missing reason should throw 422 VALIDATION_ERROR
    await expect(
      mockApiClient.patchFinding(findingId, {
        status: "DISMISSED_FALSE_POSITIVE",
        decision_reason: "",
      })
    ).rejects.toThrowError(ApiError);

    // Valid update
    const updated = await mockApiClient.patchFinding(findingId, {
      status: "DISMISSED_FALSE_POSITIVE",
      decision_reason: "Legitimate subsidiary rewards loyalty app.",
    });

    expect(updated.status).toBe("DISMISSED_FALSE_POSITIVE");
    expect(updated.decision_history.length).toBeGreaterThan(0);
  });

  it("contains all required findings records exercising UI rules", () => {
    // 1) "Kaveri Bank Rewards" iOS, score 72 HIGH, 7-signal breakdown, technique ADDED_WORD
    const rewards = MOCK_FINDINGS.find((f) => f.candidate.display_name === "Kaveri Bank Rewards");
    expect(rewards).toBeDefined();
    expect(rewards?.risk_score).toBe(72);
    expect(rewards?.severity).toBe("HIGH");
    expect(rewards?.technique).toBe("ADDED_WORD");
    expect(rewards?.score_breakdown).toHaveLength(7);

    // 2) Bluesky "Kaveri Bank Fans" (9 days old, copied avatar), score 58 HIGH
    const fans = MOCK_FINDINGS.find(
      (f) => f.candidate.display_name === "Kaveri Bank Fans" && f.risk_score === 58
    );
    expect(fans).toBeDefined();
    expect(fans?.severity).toBe("HIGH");
    expect(fans?.corroborating_groups).toContain("VISUAL");

    // 3) Bluesky "Kaveri Bank Care" score 75 CRITICAL
    const care = MOCK_FINDINGS.find((f) => f.candidate.display_name === "Kaveri Bank Care");
    expect(care).toBeDefined();
    expect(care?.risk_score).toBe(75);
    expect(care?.severity).toBe("CRITICAL");

    // 4) Homoglyph account "kaveribank" containing Cyrillic U+0456
    const homoglyph = MOCK_FINDINGS.find((f) => f.technique === "HOMOGLYPH");
    expect(homoglyph).toBeDefined();
    expect(homoglyph?.candidate.display_name).toContain("\u0456");

    // 5) Character swap "KaveriBnak"
    const swap = MOCK_FINDINGS.find((f) => f.technique === "CHARACTER_SWAP");
    expect(swap).toBeDefined();
    expect(swap?.candidate.display_name).toBe("KaveriBnak");

    // 6) Spacing "Kav eri Bank"
    const spacing = MOCK_FINDINGS.find((f) => f.technique === "SPACING");
    expect(spacing).toBeDefined();
    expect(spacing?.candidate.display_name).toBe("Kav eri Bank");

    // 7) Exact name reuse "Kaveri Bank" with nothing else observable: score 49, MEDIUM, gates_applied [G2, G3], note Insufficient evidence
    const exactName = MOCK_FINDINGS.find((f) => f.technique === "EXACT_NAME_REUSE");
    expect(exactName).toBeDefined();
    expect(exactName?.risk_score).toBe(49);
    expect(exactName?.severity).toBe("MEDIUM");
    expect(exactName?.gates_applied).toContain("G2");
    expect(exactName?.gates_applied).toContain("G3");
    expect(exactName?.explanation).toContain("Insufficient evidence");

    // 8) At least one finding with changed_since_decision=true
    const changed = MOCK_FINDINGS.find((f) => f.changed_since_decision === true);
    expect(changed).toBeDefined();

    // 9) Android, Instagram, X and Facebook findings marked SIMULATED
    const platforms = ["google_play", "instagram", "x", "facebook"];
    for (const p of platforms) {
      const match = MOCK_FINDINGS.find(
        (f) => f.candidate.platform === p && f.source_mode === "SIMULATED"
      );
      expect(match).toBeDefined();
    }
  });

  it("contains all required cleared items exercising clearing rules", () => {
    // Official iOS app by R1_EXACT_ID with exact 11.5 explanation
    const r1Ios = MOCK_CLEARED.find(
      (c) => c.rule === "R1_EXACT_ID" && c.candidate.platform === "apple_app_store"
    );
    expect(r1Ios).toBeDefined();
    expect(r1Ios?.explanation).toContain(
      "Cleared: exact bundle ID match with registered official app com.kaveribank.mobile."
    );

    // Second app by R2_PUBLISHER_ID
    const r2App = MOCK_CLEARED.find((c) => c.rule === "R2_PUBLISHER_ID");
    expect(r2App).toBeDefined();

    // AUTHORIZED_PARTNER_MATCH
    const partner = MOCK_CLEARED.find((c) => c.decision === "AUTHORIZED_PARTNER_MATCH");
    expect(partner).toBeDefined();

    // Official Bluesky account
    const bskyOfficial = MOCK_CLEARED.find(
      (c) => c.decision === "OFFICIAL_EXACT_MATCH" && c.candidate.platform === "bluesky"
    );
    expect(bskyOfficial).toBeDefined();

    // Official Android (SIMULATED)
    const androidOfficial = MOCK_CLEARED.find(
      (c) => c.candidate.platform === "google_play" && c.source_mode === "SIMULATED"
    );
    expect(androidOfficial).toBeDefined();

    // "Kaveri Coffee Roasters" G4_UNRELATED_CATEGORY
    const coffee = MOCK_CLEARED.find((c) => c.candidate.display_name === "Kaveri Coffee Roasters");
    expect(coffee).toBeDefined();
    expect(coffee?.rule).toBe("G4_UNRELATED_CATEGORY");
    expect(coffee?.source_mode).toBe("CACHED");

    // "Kaveri Bank Fans" honest fan page G4_LOW_CONTENT_OVERLAP
    const fanPage = MOCK_CLEARED.find(
      (c) => c.candidate.display_name === "Kaveri Bank Fans" && c.rule === "G4_LOW_CONTENT_OVERLAP"
    );
    expect(fanPage).toBeDefined();

    // Declared-unofficial page G5_DECLARED_UNOFFICIAL with 15.3 copy
    const declaredUnofficial = MOCK_CLEARED.find((c) => c.rule === "G5_DECLARED_UNOFFICIAL");
    expect(declaredUnofficial).toBeDefined();
    expect(declaredUnofficial?.explanation).toContain(
      "Declared unofficial in its bio. Not verified. Disclaimers can be copied by impersonators; an analyst may reopen this."
    );
  });

  it("strictly implements Section 11.1 source statuses", () => {
    const googlePlay = MOCK_SOURCES_STATUS.find((s) => s.source_id === "google_play_snapshot");
    expect(googlePlay?.status).toBe("NOT_CONNECTED");
    expect(googlePlay?.message).toContain("No official API");

    const instagram = MOCK_SOURCES_STATUS.find((s) => s.source_id === "instagram");
    expect(instagram?.status).toBe("NOT_CONNECTED");
    expect(instagram?.message).toContain("Requires platform API access");

    const x = MOCK_SOURCES_STATUS.find((s) => s.source_id === "x");
    expect(x?.status).toBe("NOT_CONNECTED");

    const fb = MOCK_SOURCES_STATUS.find((s) => s.source_id === "facebook");
    expect(fb?.status).toBe("NOT_CONNECTED");
  });

  it("computes evaluation metrics dynamically per Section 14 math with 0 official assets flagged", async () => {
    const evalResult = await mockApiClient.getLatestEvaluation({ split: "HELDOUT" });
    expect(evalResult.official_flagged_count).toBe(0);
    expect(evalResult.precision).toBeGreaterThan(0.7);
    expect(evalResult.recall).toBeGreaterThan(0.7);
    expect(evalResult.confidence_intervals.precision).toBeDefined();
    expect(evalResult.confidence_intervals.recall).toBeDefined();
    expect(evalResult.hard_negatives.false_positives).toBe(1);
    expect(evalResult.limitations[0]).toContain("Mock data");
  });
});
