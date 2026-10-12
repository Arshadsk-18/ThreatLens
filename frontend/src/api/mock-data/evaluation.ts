import type { components } from "../schema";

type EvalLabel = components["schemas"]["EvalLabel"];
type EvalSplit = components["schemas"]["EvalSplit"];
type EvaluationResult = components["schemas"]["EvaluationResult"];
type LookalikeTechnique = components["schemas"]["LookalikeTechnique"];

export interface EvalCase {
  case_id: string;
  label: EvalLabel;
  predicted_positive: boolean; // assess() returned CANDIDATE_FOR_REVIEW
  technique?: LookalikeTechnique;
  predicted_technique?: LookalikeTechnique;
  split: EvalSplit;
  provenance: "REAL_CAPTURED" | "SYNTHETIC";
  name: string;
}

// Fixed set of evaluation cases for reproducible in-test math
export const MOCK_EVAL_CASES: EvalCase[] = [
  // IMPERSONATION (positive class)
  { case_id: "c-001", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", predicted_technique: "ADDED_WORD", split: "HELDOUT", provenance: "SYNTHETIC", name: "Kaveri Bank Rewards" },
  { case_id: "c-002", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", predicted_technique: "ADDED_WORD", split: "HELDOUT", provenance: "SYNTHETIC", name: "Kaveri Bank Care" },
  { case_id: "c-003", label: "IMPERSONATION", predicted_positive: true, technique: "HOMOGLYPH", predicted_technique: "HOMOGLYPH", split: "HELDOUT", provenance: "SYNTHETIC", name: "kaveribank (U+0456)" },
  { case_id: "c-004", label: "IMPERSONATION", predicted_positive: true, technique: "CHARACTER_SWAP", predicted_technique: "CHARACTER_SWAP", split: "HELDOUT", provenance: "SYNTHETIC", name: "KaveriBnak" },
  { case_id: "c-005", label: "IMPERSONATION", predicted_positive: true, technique: "SPACING", predicted_technique: "SPACING", split: "HELDOUT", provenance: "SYNTHETIC", name: "Kav eri Bank" },
  { case_id: "c-006", label: "IMPERSONATION", predicted_positive: true, technique: "EXACT_NAME_REUSE", predicted_technique: "EXACT_NAME_REUSE", split: "HELDOUT", provenance: "SYNTHETIC", name: "Kaveri Bank (Unverified)" },
  { case_id: "c-007", label: "IMPERSONATION", predicted_positive: true, technique: "OMISSION", predicted_technique: "OMISSION", split: "HELDOUT", provenance: "SYNTHETIC", name: "Kaver Bank" },
  { case_id: "c-008", label: "IMPERSONATION", predicted_positive: true, technique: "SEPARATOR", predicted_technique: "SEPARATOR", split: "HELDOUT", provenance: "SYNTHETIC", name: "kaveri-bank-official" },
  { case_id: "c-009", label: "IMPERSONATION", predicted_positive: true, technique: "REPETITION", predicted_technique: "REPETITION", split: "HELDOUT", provenance: "SYNTHETIC", name: "Kaverii Bank" },
  { case_id: "c-010", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", predicted_technique: "ADDED_WORD", split: "HELDOUT", provenance: "SYNTHETIC", name: "Kaveri Bank Loan Instant" },
  { case_id: "c-011", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", predicted_technique: "ADDED_WORD", split: "HELDOUT", provenance: "SYNTHETIC", name: "Kaveri Bank Support Center" },
  { case_id: "c-012", label: "IMPERSONATION", predicted_positive: true, technique: "HOMOGLYPH", predicted_technique: "HOMOGLYPH", split: "HELDOUT", provenance: "SYNTHETIC", name: "kaveribаnk (Cyrillic a)" },
  { case_id: "c-013", label: "IMPERSONATION", predicted_positive: true, technique: "KEYBOARD_ADJACENT", predicted_technique: "KEYBOARD_ADJACENT", split: "HELDOUT", provenance: "SYNTHETIC", name: "Kaveri Bamk" },
  { case_id: "c-014", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", predicted_technique: "ADDED_WORD", split: "HELDOUT", provenance: "SYNTHETIC", name: "Kaveri Bank KYC Verification" },
  { case_id: "c-015", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", predicted_technique: "ADDED_WORD", split: "HELDOUT", provenance: "SYNTHETIC", name: "Kaveri Bank Cashback Club" },
  // 2 False Negatives for HELDOUT
  { case_id: "c-016", label: "IMPERSONATION", predicted_positive: false, technique: "NONE", predicted_technique: "NONE", split: "HELDOUT", provenance: "SYNTHETIC", name: "K-Finance Advisory" },
  { case_id: "c-017", label: "IMPERSONATION", predicted_positive: false, technique: "NONE", predicted_technique: "NONE", split: "HELDOUT", provenance: "SYNTHETIC", name: "KB Southern Vault" },

  // BENIGN_NAMESAKE (negative class - hard negatives)
  { case_id: "c-018", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Coffee Roasters" },
  { case_id: "c-019", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Silk Sarees" },
  { case_id: "c-020", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Spices & Foods" },
  { case_id: "c-021", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Travels Bus Booking" },
  { case_id: "c-022", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri River Water Foundation" },
  { case_id: "c-023", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Educational Trust" },
  { case_id: "c-024", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Diagnostic Clinic" },
  { case_id: "c-025", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Organic Seeds" },
  { case_id: "c-026", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Hotel & Residency" },
  { case_id: "c-027", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Fitness Studio" },
  { case_id: "c-028", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Furniture World" },
  { case_id: "c-029", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Bank Fans (Honest)" },
  { case_id: "c-030", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Real Estate Agency" },
  { case_id: "c-031", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Dairy Products" },
  { case_id: "c-032", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Motors Garage" },
  { case_id: "c-033", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Printing Works" },
  { case_id: "c-034", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Book Depot" },
  { case_id: "c-035", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Dental Care" },
  { case_id: "c-036", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Pharma Chemist" },
  { case_id: "c-037", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Engineering Works" },
  { case_id: "c-038", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Arts & Crafts" },
  { case_id: "c-039", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Hardware Store" },
  { case_id: "c-040", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Tailoring Hub" },
  // 1 False Positive for HELDOUT
  { case_id: "c-041", label: "BENIGN_NAMESAKE", predicted_positive: true, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Financial Planners" },

  // OFFICIAL (negative class - must NEVER be flagged)
  { case_id: "c-042", label: "OFFICIAL", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Bank (iOS App)" },
  { case_id: "c-043", label: "OFFICIAL", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Bank Wealth (2nd App)" },
  { case_id: "c-044", label: "OFFICIAL", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Pay (Partner App)" },
  { case_id: "c-045", label: "OFFICIAL", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Bank Official Bluesky" },
  { case_id: "c-046", label: "OFFICIAL", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Bank Mobile (Android)" },
  { case_id: "c-047", label: "OFFICIAL", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Bank Cards Portal" },
  { case_id: "c-048", label: "OFFICIAL", predicted_positive: false, split: "HELDOUT", provenance: "REAL_CAPTURED", name: "Kaveri Corporate Connect" },

  // ==========================================
  // DEV SPLIT (72 cases: 25 IMPERSONATION, 35 BENIGN_NAMESAKE, 12 OFFICIAL)
  // ==========================================
  // 25 IMPERSONATION (24 TP, 1 FN)
  { case_id: "dev-001", label: "IMPERSONATION", predicted_positive: true, technique: "HOMOGLYPH", split: "DEV", provenance: "SYNTHETIC", name: "kаveri bank" },
  { case_id: "dev-002", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", split: "DEV", provenance: "SYNTHETIC", name: "Kaveri Bank Loans" },
  { case_id: "dev-003", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", split: "DEV", provenance: "SYNTHETIC", name: "Kaveri Bank FastPay" },
  { case_id: "dev-004", label: "IMPERSONATION", predicted_positive: true, technique: "CHARACTER_SWAP", split: "DEV", provenance: "SYNTHETIC", name: "Kavrei Bank" },
  { case_id: "dev-005", label: "IMPERSONATION", predicted_positive: true, technique: "SPACING", split: "DEV", provenance: "SYNTHETIC", name: "KaveriBank Secure" },
  { case_id: "dev-006", label: "IMPERSONATION", predicted_positive: true, technique: "EXACT_NAME_REUSE", split: "DEV", provenance: "SYNTHETIC", name: "Kaveri Bank (Community)" },
  { case_id: "dev-007", label: "IMPERSONATION", predicted_positive: true, technique: "OMISSION", split: "DEV", provenance: "SYNTHETIC", name: "Kavri Bank" },
  { case_id: "dev-008", label: "IMPERSONATION", predicted_positive: true, technique: "SEPARATOR", split: "DEV", provenance: "SYNTHETIC", name: "kaveri_bank_official" },
  { case_id: "dev-009", label: "IMPERSONATION", predicted_positive: true, technique: "REPETITION", split: "DEV", provenance: "SYNTHETIC", name: "Kaverii Bank Ltd" },
  { case_id: "dev-010", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", split: "DEV", provenance: "SYNTHETIC", name: "Kaveri Bank Gold Loan" },
  { case_id: "dev-011", label: "IMPERSONATION", predicted_positive: true, technique: "KEYBOARD_ADJACENT", split: "DEV", provenance: "SYNTHETIC", name: "Kaveri Bamk Pay" },
  { case_id: "dev-012", label: "IMPERSONATION", predicted_positive: true, technique: "HOMOGLYPH", split: "DEV", provenance: "SYNTHETIC", name: "kаveribank mobile" },
  { case_id: "dev-013", label: "IMPERSONATION", predicted_positive: true, technique: "SUBDOMAIN_LURE", split: "DEV", provenance: "SYNTHETIC", name: "kaveribank.login-portal.net" },
  { case_id: "dev-014", label: "IMPERSONATION", predicted_positive: true, technique: "TLD_SWAP", split: "DEV", provenance: "SYNTHETIC", name: "kaveribank.co" },
  { case_id: "dev-015", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", split: "DEV", provenance: "SYNTHETIC", name: "Kaveri Bank Netbanking" },
  { case_id: "dev-016", label: "IMPERSONATION", predicted_positive: true, technique: "CHARACTER_SWAP", split: "DEV", provenance: "SYNTHETIC", name: "Kaveri Bnak Online" },
  { case_id: "dev-017", label: "IMPERSONATION", predicted_positive: true, technique: "SPACING", split: "DEV", provenance: "SYNTHETIC", name: "Kaveri BankMobile" },
  { case_id: "dev-018", label: "IMPERSONATION", predicted_positive: true, technique: "SEPARATOR", split: "DEV", provenance: "SYNTHETIC", name: "kaveri.bank.app" },
  { case_id: "dev-019", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", split: "DEV", provenance: "SYNTHETIC", name: "Kaveri Bank Crypto" },
  { case_id: "dev-020", label: "IMPERSONATION", predicted_positive: true, technique: "HOMOGLYPH", split: "DEV", provenance: "SYNTHETIC", name: "kaveri bаnk card" },
  { case_id: "dev-021", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", split: "DEV", provenance: "SYNTHETIC", name: "Kaveri Bank Wallet" },
  { case_id: "dev-022", label: "IMPERSONATION", predicted_positive: true, technique: "EXACT_NAME_REUSE", split: "DEV", provenance: "SYNTHETIC", name: "Kaveri Bank Customer Care" },
  { case_id: "dev-023", label: "IMPERSONATION", predicted_positive: true, technique: "REPETITION", split: "DEV", provenance: "SYNTHETIC", name: "Kaaveri Bank" },
  { case_id: "dev-024", label: "IMPERSONATION", predicted_positive: true, technique: "ADDED_WORD", split: "DEV", provenance: "SYNTHETIC", name: "Kaveri Bank Bonus" },
  // 1 FN on DEV
  { case_id: "dev-025", label: "IMPERSONATION", predicted_positive: false, technique: "NONE", split: "DEV", provenance: "SYNTHETIC", name: "Southern River Wealth" },

  // 35 BENIGN_NAMESAKE (33 TN, 2 FP)
  { case_id: "dev-026", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Pottery Studio" },
  { case_id: "dev-027", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Handloom Weavers" },
  { case_id: "dev-028", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Sweet Stall" },
  { case_id: "dev-029", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Fast Freight" },
  { case_id: "dev-030", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Ayurvedic Center" },
  { case_id: "dev-031", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Hardware & Paints" },
  { case_id: "dev-032", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Cine Complex" },
  { case_id: "dev-033", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Rice Mill" },
  { case_id: "dev-034", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Bakery House" },
  { case_id: "dev-035", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri School of Dance" },
  { case_id: "dev-036", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Mineral Waters" },
  { case_id: "dev-037", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Gas Agency" },
  { case_id: "dev-038", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Steel Fabricators" },
  { case_id: "dev-039", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Photography" },
  { case_id: "dev-040", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Optical Center" },
  { case_id: "dev-041", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Poultry Farm" },
  { case_id: "dev-042", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Jewellery Works" },
  { case_id: "dev-043", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Security Services" },
  { case_id: "dev-044", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Driving School" },
  { case_id: "dev-045", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Tailors" },
  { case_id: "dev-046", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Electricals" },
  { case_id: "dev-047", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Footwear Store" },
  { case_id: "dev-048", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Timber Mart" },
  { case_id: "dev-049", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Florist" },
  { case_id: "dev-050", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Ice Cream Parlour" },
  { case_id: "dev-051", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Stationery Mart" },
  { case_id: "dev-052", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Book Binding" },
  { case_id: "dev-053", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Nursery & Gardens" },
  { case_id: "dev-054", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri General Stores" },
  { case_id: "dev-055", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Tea Stall" },
  { case_id: "dev-056", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Car Wash" },
  { case_id: "dev-057", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Sports Goods" },
  { case_id: "dev-058", label: "BENIGN_NAMESAKE", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Milk Dairy" },
  // 2 FP on DEV
  { case_id: "dev-059", label: "BENIGN_NAMESAKE", predicted_positive: true, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Investment Advisers" },
  { case_id: "dev-060", label: "BENIGN_NAMESAKE", predicted_positive: true, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Micro Capital" },

  // 12 OFFICIAL (all correctly cleared, officialFlagged = 0)
  { case_id: "dev-061", label: "OFFICIAL", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Mobile Banking App" },
  { case_id: "dev-062", label: "OFFICIAL", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Wealth Advisor" },
  { case_id: "dev-063", label: "OFFICIAL", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Pay Lite" },
  { case_id: "dev-064", label: "OFFICIAL", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Official Support Handle" },
  { case_id: "dev-065", label: "OFFICIAL", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri FastTag Service" },
  { case_id: "dev-066", label: "OFFICIAL", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Corporate Net" },
  { case_id: "dev-067", label: "OFFICIAL", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri UPI Gateway" },
  { case_id: "dev-068", label: "OFFICIAL", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Securities Hub" },
  { case_id: "dev-069", label: "OFFICIAL", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri NRI Banking" },
  { case_id: "dev-070", label: "OFFICIAL", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Commercial Desk" },
  { case_id: "dev-071", label: "OFFICIAL", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri Treasury App" },
  { case_id: "dev-072", label: "OFFICIAL", predicted_positive: false, split: "DEV", provenance: "REAL_CAPTURED", name: "Kaveri SME Connect" },
];


/**
 * Wilson 95% confidence interval formula strictly implemented per Section 14:
 * p = k/n, z = 1.96
 * centre = (p + z²/2n) / (1 + z²/n)
 * half = z · √(p(1−p)/n + z²/4n²) / (1 + z²/n)
 * interval [clamp(centre - half, 0, 1), clamp(centre + half, 0, 1)]
 */
export function calculateWilsonInterval(k: number, n: number): [number, number] | null {
  if (n <= 0) return null;
  const p = k / n;
  const z = 1.96;
  const z2 = z * z;
  const denominator = 1 + z2 / n;
  const centre = (p + z2 / (2 * n)) / denominator;
  const underSqrt = (p * (1 - p)) / n + z2 / (4 * n * n);
  const half = (z * Math.sqrt(Math.max(0, underSqrt))) / denominator;
  const lower = Math.max(0, Math.round((centre - half) * 100) / 100);
  const upper = Math.min(1, Math.round((centre + half) * 100) / 100);
  return [lower, upper];
}

/**
 * Computes all Section 14 metrics from cases dynamically.
 */
export function computeEvaluationMetrics(
  cases: EvalCase[],
  split: EvalSplit = "HELDOUT"
): EvaluationResult {
  const filtered = cases.filter((c) => c.split === split);

  let tp = 0;
  let fp = 0;
  let tn = 0;
  let fn = 0;
  let officialFlagged = 0;

  let hardNegativesTested = 0;
  let hardNegativesCorrectlyCleared = 0;

  const techniqueMap = new Map<LookalikeTechnique, { tested: number; detected: number }>();

  for (const c of filtered) {
    const isPositiveClass = c.label === "IMPERSONATION";

    if (c.label === "OFFICIAL" && c.predicted_positive) {
      officialFlagged++;
    }

    if (c.label === "BENIGN_NAMESAKE") {
      hardNegativesTested++;
      if (!c.predicted_positive) {
        hardNegativesCorrectlyCleared++;
      }
    }

    if (isPositiveClass) {
      if (c.technique) {
        const current = techniqueMap.get(c.technique) || { tested: 0, detected: 0 };
        current.tested++;
        if (c.predicted_positive) {
          current.detected++;
        }
        techniqueMap.set(c.technique, current);
      }

      if (c.predicted_positive) {
        tp++;
      } else {
        fn++;
      }
    } else {
      if (c.predicted_positive) {
        fp++;
      } else {
        tn++;
      }
    }
  }

  const precision = tp + fp > 0 ? Math.round((tp / (tp + fp)) * 100) / 100 : null;
  const recall = tp + fn > 0 ? Math.round((tp / (tp + fn)) * 100) / 100 : null;
  const f1 =
    precision !== null && recall !== null && precision + recall > 0
      ? Math.round(((2 * precision * recall) / (precision + recall)) * 100) / 100
      : null;
  const falsePositiveRate = fp + tn > 0 ? Math.round((fp / (fp + tn)) * 100) / 100 : null;

  const techniqueRecall = Array.from(techniqueMap.entries()).map(([technique, stats]) => ({
    technique,
    tested: stats.tested,
    detected: stats.detected,
  }));

  const failureCases = filtered
    .filter((c) => (c.label === "IMPERSONATION" && !c.predicted_positive) || (c.label !== "IMPERSONATION" && c.predicted_positive))
    .map((c) => ({
      case_id: c.case_id,
      expected: c.label,
      got: c.predicted_positive ? "CANDIDATE_FOR_REVIEW" : "CLEARED / BENIGN_LOOKALIKE",
      why: c.label === "IMPERSONATION"
        ? `Adversarial candidate "${c.name}" fell below review threshold due to low lexical similarity.`
        : `Benign entity "${c.name}" triggered name and context overlap with official brand profile.`,
    }));

  return {
    id: "eval-30000000-0000-0000-0000-000000000001",
    dataset_id: "threatlens-v1",
    split,
    scoring_version: "3.0.0",
    threshold: { review: 25 },
    sample_count: filtered.length,
    confusion: { tp, fp, tn, fn },
    precision,
    recall,
    f1,
    false_positive_rate: falsePositiveRate,
    confidence_intervals: {
      precision: calculateWilsonInterval(tp, tp + fp),
      recall: calculateWilsonInterval(tp, tp + fn),
      false_positive_rate: calculateWilsonInterval(fp, fp + tn),
      method: "wilson_95",
    },
    official_flagged_count: officialFlagged,
    hard_negatives: {
      tested: hardNegativesTested,
      correctly_cleared: hardNegativesCorrectlyCleared,
      false_positives: hardNegativesTested - hardNegativesCorrectlyCleared,
    },
    technique_recall: techniqueRecall,
    baseline: {
      name: "name_only_rapidfuzz",
      tuned_on: "DEV",
      precision: 0.61,
      recall: 0.94,
      false_positive_rate: 0.4,
    },
    ablation: [
      { configuration: "FULL", precision: precision ?? 0.94, recall: recall ?? 0.88 },
      { configuration: "NO_IDENTITYGUARD", precision: 0.82, recall: 0.88, official_flagged_count: 5 },
      { configuration: "NO_GATES", precision: 0.48, recall: 0.95 },
      { configuration: "NO_ICON", precision: 0.86, recall: 0.81 },
      { configuration: "NO_DESCRIPTION", precision: 0.89, recall: 0.79 },
    ],
    failure_cases: failureCases.slice(0, 3),
    definitions:
      "Positive class = IMPERSONATION. Predicted positive = decision CANDIDATE_FOR_REVIEW. OFFICIAL cases count as negatives and any flagged official asset is also reported separately.",
    limitations: [
      "Mock data computed dynamically from calibrated test cases.",
      "Positives are synthetic.",
      "Small sample; see confidence intervals.",
    ],
    created_at: "2026-10-12T05:30:00Z",
  };
}
