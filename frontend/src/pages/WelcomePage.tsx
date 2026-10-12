import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { NameDiff } from "@/components/cx/NameDiff";
import { SeverityPill } from "@/components/cx/SeverityPill";
import { SourceBadge } from "@/components/cx/SourceBadge";
import { ScoreBar } from "@/components/cx/ScoreBar";
import {
  ShieldCheck,
  ArrowRight,
  Fingerprint,
  ArrowUp,
} from "lucide-react";
import { ScrollReveal } from "@/components/common/ScrollReveal";
import { cn } from "@/lib/utils";

interface TechniqueDemo {
  id: string;
  label: string;
  candidateName: string;
  technique: string;
  description: string;
  diffSegments: { text: string; changed: boolean }[];
  nonAsciiChars: { char: string; codepoint: string; index: number }[];
}

const TECHNIQUES_DEMO: TechniqueDemo[] = [
  {
    id: "homoglyph",
    label: "Homoglyph",
    candidateName: "Kaver\u0456 Bank", // Cyrillic small letter byelorussian-ukrainian i (U+0456)
    technique: "HOMOGLYPH",
    description: "Cyrillic \u0456 (U+0456) visually mimics Latin 'i' to bypass simple string comparisons.",
    diffSegments: [
      { text: "Kaver", changed: false },
      { text: "\u0456", changed: true },
      { text: " Bank", changed: false },
    ],
    nonAsciiChars: [{ char: "\u0456", codepoint: "U+0456", index: 5 }],
  },
  {
    id: "character_swap",
    label: "Character swap",
    candidateName: "KaveriBnak",
    technique: "CHARACTER_SWAP",
    description: "Adjacent character transposition ('Bnak' instead of 'Bank') exploits rapid visual scanning.",
    diffSegments: [
      { text: "Kaveri", changed: false },
      { text: "Bnak", changed: true },
    ],
    nonAsciiChars: [],
  },
  {
    id: "spacing",
    label: "Spacing",
    candidateName: "Kav eri Bank",
    technique: "SPACING",
    description: "Inserted internal space breaks keyword filters while preserving readability.",
    diffSegments: [
      { text: "Kav", changed: false },
      { text: " ", changed: true },
      { text: "eri Bank", changed: false },
    ],
    nonAsciiChars: [],
  },
  {
    id: "added_word",
    label: "Added word",
    candidateName: "Kaveri Bank Rewards",
    technique: "ADDED_WORD",
    description: "Appended promotional token ('Rewards') creates look-alike social and app listings.",
    diffSegments: [
      { text: "Kaveri Bank", changed: false },
      { text: " Rewards", changed: true },
    ],
    nonAsciiChars: [],
  },
  {
    id: "separator",
    label: "Separator",
    candidateName: "kaveri-bank",
    technique: "SEPARATOR",
    description: "Hyphen substitution replaces space to register look-alike handles and domains.",
    diffSegments: [
      { text: "kaveri", changed: false },
      { text: "-", changed: true },
      { text: "bank", changed: false },
    ],
    nonAsciiChars: [],
  },
];

const NAV_LINKS = [
  { href: "#principles", label: "Principles", id: "principles" },
  { href: "#pipeline", label: "Pipeline", id: "pipeline" },
  { href: "#identity-clearing", label: "Identity Clearing", id: "identity-clearing" },
  { href: "#evidence-compare", label: "Evidence Compare", id: "evidence-compare" },
  { href: "#sources", label: "Sources", id: "sources" },
  { href: "#evaluation", label: "Evaluation", id: "evaluation" },
];

export function WelcomePage() {
  const [activeTechniqueId, setActiveTechniqueId] = useState<string>("homoglyph");
  const [scrollProgress, setScrollProgress] = useState<number>(0);
  const [showBackToTop, setShowBackToTop] = useState<boolean>(false);
  const [activeSection, setActiveSection] = useState<string>("");

  const activeTechnique =
    TECHNIQUES_DEMO.find((t) => t.id === activeTechniqueId) || TECHNIQUES_DEMO[0];

  useEffect(() => {
    const handleScroll = () => {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      const scrollY = window.scrollY;
      if (scrollHeight > 0) {
        const progress = (scrollY / scrollHeight) * 100;
        setScrollProgress(Math.min(100, Math.max(0, progress)));
      }
      setShowBackToTop(scrollY > 400);

      // Detect active visible section
      const sectionIds = [
        "principles",
        "pipeline",
        "identity-clearing",
        "evidence-compare",
        "sources",
        "evaluation",
      ];
      for (let i = sectionIds.length - 1; i >= 0; i--) {
        const el = document.getElementById(sectionIds[i]);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= 240) {
            setActiveSection(sectionIds[i]);
            break;
          }
        }
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Optional evaluation harness query (Section 7)
  const { data: latestEval, isError: isEvalError } = useQuery({
    queryKey: ["welcome-latest-eval"],
    queryFn: () => apiClient.getLatestEvaluation({ split: "HELDOUT" }),
    retry: 0,
    staleTime: 60000,
  });

  // Optional health query for contract version
  const { data: health } = useQuery({
    queryKey: ["welcome-health"],
    queryFn: () => apiClient.getHealth(),
    retry: 0,
    staleTime: 60000,
  });

  const contractVersion = health?.contract_version || "3.0.0";

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col font-sans selection:bg-lens selection:text-white relative">
      {/* Top Navigation */}
      <header className="border-b border-hairline bg-surface/90 backdrop-blur-md sticky top-0 z-30">
        {/* Scroll Progress Bar */}
        <div
          className="absolute bottom-0 left-0 h-[2.5px] bg-lens transition-[width] duration-150 ease-out z-40 pointer-events-none"
          style={{ width: `${scrollProgress}%` }}
          aria-hidden="true"
        />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              to="/welcome"
              className="flex items-center gap-2.5 font-display font-extrabold text-lg text-ink tracking-tight focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens rounded"
            >
              <div className="w-8 h-8 rounded-pill bg-ink text-white flex items-center justify-center font-display font-bold text-sm shadow-xs">
                TL
              </div>
              <span>ThreatLens</span>
            </Link>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded-full bg-surface-2 text-ink-muted border border-hairline font-semibold">
              v{contractVersion}
            </span>
          </div>

          <nav className="hidden md:flex items-center gap-5 text-xs font-semibold">
            {NAV_LINKS.map((item) => (
              <a
                key={item.id}
                href={item.href}
                className={cn(
                  "transition-colors focus-visible:ring-2 focus-visible:ring-lens rounded px-2 py-1",
                  activeSection === item.id
                    ? "text-ink font-bold bg-surface-2"
                    : "text-ink-muted hover:text-ink"
                )}
              >
                {item.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="px-4 py-2 rounded-pill bg-ink text-white text-xs font-semibold hover:bg-ink/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens transition-all shadow-xs flex items-center gap-1.5 hover:scale-105 active:scale-95"
            >
              <span>Demo Workspace</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main id="main-content" className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-8 sm:py-12 space-y-16 sm:space-y-24">
        {/* HERO SECTION */}
        <section aria-label="Hero Introduction" className="animate-fade-in motion-reduce:animate-none">
          <div className="rounded-panel md:rounded-[36px] bg-surface p-2.5 sm:p-4 md:p-6 border border-hairline shadow-sm">
            <div className="rounded-nested md:rounded-[28px] bg-ink text-white p-6 sm:p-10 md:p-14 space-y-10 relative overflow-hidden">
              <div className="space-y-5 max-w-3xl">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-pill bg-white/10 border border-white/15 text-[11px] font-mono text-white/90">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span>Forensic Digital Risk Protection Platform</span>
                </div>

                <h1 className="font-display font-extrabold text-4xl sm:text-5xl md:text-6xl lg:text-7xl tracking-tight text-white leading-[1.05]">
                  Names can lie. IDs can&apos;t.
                </h1>

                <p className="text-white/80 text-base sm:text-lg md:text-xl font-sans leading-relaxed">
                  ThreatLens finds look-alike apps and social accounts, clears the official ones by exact
                  ID, and shows the evidence behind every candidate for review.
                </p>

                <div className="pt-2 flex flex-wrap items-center gap-3">
                  <Link
                    to="/"
                    className="px-6 py-3 rounded-pill bg-white text-ink font-semibold text-sm hover:bg-white/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens transition-all shadow-sm flex items-center gap-2"
                  >
                    <span>Open the demo workspace</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                  <a
                    href="#evidence-compare"
                    className="px-6 py-3 rounded-pill bg-white/10 text-white font-semibold text-sm hover:bg-white/20 border border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens transition-all"
                  >
                    See how a finding is built
                  </a>
                </div>
              </div>

              {/* THE LENS (Interactive Hero Object) */}
              <div className="pt-4 border-t border-white/15">
                <div className="rounded-nested bg-surface text-ink p-5 sm:p-7 border border-hairline shadow-floating space-y-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-hairline">
                    <div className="flex items-center gap-2">
                      <Fingerprint className="w-5 h-5 text-lens" />
                      <h2 className="font-display font-bold text-base text-ink">
                        The Lens: Character-Level Name Examination
                      </h2>
                    </div>
                    <span className="font-mono text-xs px-2.5 py-0.5 rounded-pill bg-surface-2 text-ink-muted border border-hairline">
                      Interactive Client Forensic Lens
                    </span>
                  </div>

                  {/* Technique Selector Chips */}
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-ink-muted block">
                      Select Look-Alike Technique:
                    </label>
                    <div className="flex flex-wrap gap-2" role="group" aria-label="Look-alike techniques">
                      {TECHNIQUES_DEMO.map((t) => {
                        const isSelected = t.id === activeTechniqueId;
                        return (
                          <button
                            key={t.id}
                            type="button"
                            onClick={() => setActiveTechniqueId(t.id)}
                            aria-pressed={isSelected}
                            className={cn(
                              "px-3.5 py-1.5 rounded-pill text-xs font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens",
                              isSelected
                                ? "bg-ink text-white shadow-xs"
                                : "bg-surface-2 text-ink-muted hover:text-ink hover:bg-hairline border border-hairline"
                            )}
                          >
                            {t.label}
                          </button>
                        );
                      })}
                    </div>
                    <p className="text-xs text-ink-muted pt-1">
                      {activeTechnique.description}
                    </p>
                  </div>

                  {/* NameDiff Display Component */}
                  <div className="space-y-3">
                    <NameDiff
                      official="Kaveri Bank"
                      candidate={activeTechnique.candidateName}
                      diffSegments={activeTechnique.diffSegments}
                      nonAsciiChars={activeTechnique.nonAsciiChars}
                      technique={activeTechnique.technique}
                    />

                    <p className="text-[11px] text-ink-muted italic">
                      Illustration with a fictional brand. Not live data.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 2: RULES WE DO NOT BREAK */}
        <section id="principles" aria-labelledby="principles-heading" className="space-y-6">
          <ScrollReveal direction="up">
            <div className="space-y-1">
              <span className="font-mono text-xs uppercase text-lens font-bold tracking-wider">
                Section 2 Specifications
              </span>
              <h2 id="principles-heading" className="font-display font-bold text-2xl sm:text-3xl text-ink">
                Rules we do not break
              </h2>
              <p className="text-sm text-ink-muted max-w-2xl">
                Non-negotiable architectural tenets baked into every scoring formula and interface rule.
              </p>
            </div>
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
            {/* Panel 1 */}
            <ScrollReveal delayMs={0} className="md:col-span-7">
              <div className="h-full rounded-panel bg-surface p-6 border border-hairline shadow-xs space-y-2 hover:-translate-y-1 hover:shadow-md hover:border-lens/30 transition-all duration-300">
                <span className="w-2 h-2 rounded-full bg-lens inline-block" />
                <h3 className="font-display font-semibold text-lg text-ink">
                  Candidates for review, not verdicts.
                </h3>
                <p className="text-sm text-ink-muted leading-relaxed">
                  We surface candidates for human analyst review, never automated judgements of guilt.
                </p>
              </div>
            </ScrollReveal>

            {/* Panel 2 */}
            <ScrollReveal delayMs={80} className="md:col-span-5">
              <div className="h-full rounded-panel bg-surface p-6 border border-hairline shadow-xs space-y-2 hover:-translate-y-1 hover:shadow-md hover:border-teal-500/30 transition-all duration-300">
                <span className="w-2 h-2 rounded-full bg-teal-600 inline-block" />
                <h3 className="font-display font-semibold text-lg text-ink">
                  Identity by ID, never by name.
                </h3>
                <p className="text-sm text-ink-muted leading-relaxed">
                  Official assets are excluded by exact cryptographic and catalog identifiers, never string similarity.
                </p>
              </div>
            </ScrollReveal>

            {/* Panel 3 */}
            <ScrollReveal delayMs={140} className="md:col-span-4">
              <div className="h-full rounded-panel bg-surface p-6 border border-hairline shadow-xs space-y-2 hover:-translate-y-1 hover:shadow-md hover:border-amber-500/30 transition-all duration-300">
                <span className="w-2 h-2 rounded-full bg-amber-600 inline-block" />
                <h3 className="font-display font-semibold text-base text-ink">
                  Missing evidence is not evidence.
                </h3>
                <p className="text-xs text-ink-muted leading-relaxed">
                  Unavailable signals score zero points and reduce coverage; they do not imply safety or danger.
                </p>
              </div>
            </ScrollReveal>

            {/* Panel 4 */}
            <ScrollReveal delayMs={200} className="md:col-span-4">
              <div className="h-full rounded-panel bg-surface p-6 border border-hairline shadow-xs space-y-2 hover:-translate-y-1 hover:shadow-md hover:border-purple-500/30 transition-all duration-300">
                <span className="w-2 h-2 rounded-full bg-purple-600 inline-block" />
                <h3 className="font-display font-semibold text-base text-ink">
                  No silent fallbacks.
                </h3>
                <p className="text-xs text-ink-muted leading-relaxed">
                  A failed provider is an explicit failure, not an empty result. Cached and simulated records are always labelled.
                </p>
              </div>
            </ScrollReveal>

            {/* Panel 5 */}
            <ScrollReveal delayMs={260} className="md:col-span-4">
              <div className="h-full rounded-panel bg-surface p-6 border border-hairline shadow-xs space-y-2 hover:-translate-y-1 hover:shadow-md hover:border-rose-500/30 transition-all duration-300">
                <span className="w-2 h-2 rounded-full bg-rose-600 inline-block" />
                <h3 className="font-display font-semibold text-base text-ink">
                  Scores are not probabilities.
                </h3>
                <p className="text-xs text-ink-muted leading-relaxed">
                  A risk score is an explainable sum of observable evidence points, not a percentage chance.
                </p>
              </div>
            </ScrollReveal>
          </div>
        </section>

        {/* SECTION 3: FROM BRAND PROFILE TO DECISION */}
        <section id="pipeline" aria-labelledby="pipeline-heading" className="space-y-6">
          <ScrollReveal direction="up">
            <div className="space-y-1">
              <span className="font-mono text-xs uppercase text-lens font-bold tracking-wider">
                Section 5.2 Architecture
              </span>
              <h2 id="pipeline-heading" className="font-display font-bold text-2xl sm:text-3xl text-ink">
                From brand profile to decision
              </h2>
              <p className="text-sm text-ink-muted max-w-2xl">
                The end-to-end processing pipeline, from initial asset registration to final analyst audit.
              </p>
            </div>
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-7 gap-3">
            {[
              {
                num: "1",
                title: "Register official assets",
                desc: "Catalog IDs, developer IDs, and domains.",
              },
              {
                num: "2",
                title: "Plan queries",
                desc: "Bounded, ordered platform search terms.",
              },
              {
                num: "3",
                title: "Fetch sources",
                desc: "Parallel catalog and directory queries.",
              },
              {
                num: "4",
                title: "Hash icons",
                desc: "Perceptual hashing for logo comparison.",
              },
              {
                num: "5",
                title: "IdentityGuard",
                desc: "Exact ID, publisher ID, and partner matching.",
                isClearing: true,
              },
              {
                num: "6",
                title: "Score with gates",
                desc: "Observable points and corroboration gates.",
              },
              {
                num: "7",
                title: "Analyst decision",
                desc: "Review record with decision audit history.",
              },
            ].map((step, idx) => (
              <ScrollReveal key={step.num} delayMs={idx * 60}>
                <div
                  className={cn(
                    "h-full p-4 rounded-panel border flex flex-col justify-between space-y-3 relative hover:-translate-y-1 hover:shadow-md transition-all duration-300",
                    step.isClearing
                      ? "bg-lens/5 border-lens shadow-xs ring-1 ring-lens/30 hover:ring-lens"
                      : "bg-surface border-hairline shadow-xs hover:border-lens/20"
                  )}
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold w-6 h-6 rounded-full bg-surface-2 border border-hairline flex items-center justify-center text-ink">
                        {step.num}
                      </span>
                      {step.isClearing && (
                        <span className="font-mono text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-lens text-white uppercase animate-pulse">
                          Clearing Point
                        </span>
                      )}
                    </div>
                    <h3 className="font-display font-semibold text-xs text-ink mt-2">
                      {step.title}
                    </h3>
                  </div>
                  <p className="text-[11px] text-ink-muted leading-snug">
                    {step.desc}
                  </p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </section>

        {/* SECTION 4: OFFICIAL ASSETS ARE CLEARED BY IDENTITY */}
        <section id="identity-clearing" aria-labelledby="identity-heading" className="space-y-6">
          <ScrollReveal direction="up">
            <div className="space-y-1">
              <span className="font-mono text-xs uppercase text-lens font-bold tracking-wider">
                Section 7 IdentityGuard
              </span>
              <h2 id="identity-heading" className="font-display font-bold text-2xl sm:text-3xl text-ink">
                Official assets are cleared by identity
              </h2>
              <p className="text-base font-semibold text-ink max-w-2xl">
                Name similarity finds suspects. It never clears anyone.
              </p>
            </div>
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* R1 */}
            <ScrollReveal delayMs={0}>
              <div className="h-full rounded-panel bg-surface p-5 border border-hairline shadow-xs space-y-4 hover:-translate-y-1 hover:shadow-md hover:border-teal-500/40 transition-all duration-300">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs px-2.5 py-1 rounded-pill bg-teal-500/10 text-teal-700 dark:text-teal-400 border border-teal-500/25">
                    R1_EXACT_ID
                  </span>
                  <ShieldCheck className="w-4 h-4 text-teal-600" />
                </div>
                <div>
                  <h3 className="font-display font-semibold text-sm text-ink">Exact ID Match</h3>
                  <p className="text-xs text-ink-muted mt-1">
                    Exact catalog or bundle identifier match against a registered, verified official asset.
                  </p>
                </div>
                <div className="p-3 rounded-panel-nested bg-surface-2 border border-hairline font-mono text-[11px] text-ink leading-relaxed">
                  &ldquo;Cleared: exact bundle ID match with registered official app com.kaveribank.mobile.&rdquo;
                </div>
              </div>
            </ScrollReveal>

            {/* R2 */}
            <ScrollReveal delayMs={100}>
              <div className="h-full rounded-panel bg-surface p-5 border border-hairline shadow-xs space-y-4 hover:-translate-y-1 hover:shadow-md hover:border-lens/40 transition-all duration-300">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs px-2.5 py-1 rounded-pill bg-lens/10 text-lens border border-lens/25">
                    R2_PUBLISHER_ID
                  </span>
                  <ShieldCheck className="w-4 h-4 text-lens" />
                </div>
                <div>
                  <h3 className="font-display font-semibold text-sm text-ink">Publisher ID Match</h3>
                  <p className="text-xs text-ink-muted mt-1">
                    Developer ID match against an asset with trusted publisher verification enabled.
                  </p>
                </div>
                <div className="p-3 rounded-panel-nested bg-surface-2 border border-hairline font-mono text-[11px] text-ink leading-relaxed">
                  &ldquo;Published by the registered developer. Consider registering this app.&rdquo;
                </div>
              </div>
            </ScrollReveal>

            {/* R3 */}
            <ScrollReveal delayMs={200}>
              <div className="h-full rounded-panel bg-surface p-5 border border-hairline shadow-xs space-y-4 hover:-translate-y-1 hover:shadow-md hover:border-blue-500/40 transition-all duration-300">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs px-2.5 py-1 rounded-pill bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-500/25">
                    R3_PARTNER
                  </span>
                  <ShieldCheck className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-display font-semibold text-sm text-ink">Authorized Partner</h3>
                  <p className="text-xs text-ink-muted mt-1">
                    Identifier match against registered affiliate, partner, or subsidiary asset whitelist.
                  </p>
                </div>
                <div className="p-3 rounded-panel-nested bg-surface-2 border border-hairline font-mono text-[11px] text-ink leading-relaxed">
                  &ldquo;Cleared: verified authorized partner asset with registered distribution credentials.&rdquo;
                </div>
              </div>
            </ScrollReveal>
          </div>
        </section>

        {/* SECTION 5: SEE EXACTLY WHY (Miniature of Evidence Compare) */}
        <section id="evidence-compare" aria-labelledby="compare-heading" className="space-y-6">
          <ScrollReveal direction="up">
            <div className="space-y-1">
              <span className="font-mono text-xs uppercase text-lens font-bold tracking-wider">
                Section 8 & 11.5 Forensic Audit
              </span>
              <h2 id="compare-heading" className="font-display font-bold text-2xl sm:text-3xl text-ink">
                See exactly why
              </h2>
              <p className="text-sm text-ink-muted max-w-2xl">
                A static, non-interactive miniature of Evidence Compare built from the exact production components.
              </p>
            </div>
          </ScrollReveal>

          <ScrollReveal delayMs={100}>
            <div className="rounded-panel bg-surface p-6 sm:p-8 border border-hairline shadow-xs space-y-6 hover:shadow-md transition-shadow duration-300">
              {/* Header Strip with Exact Mock Candidate Details */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-hairline">
                <div className="space-y-1">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <h3 className="font-display font-bold text-xl text-ink">
                      Kaveri Bank Rewards
                    </h3>
                    <SeverityPill severity="HIGH" />
                    <SourceBadge status="SIMULATED" />
                  </div>
                  <p className="text-xs text-ink-muted font-mono">
                    Simulated demo record · Apple App Store · ID: 9876543210
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-[11px] text-ink-muted block font-medium">Risk Score</span>
                    <span className="font-mono font-bold text-lg text-ink">
                      72 / 100
                    </span>
                  </div>
                  <div className="h-8 w-px bg-hairline" />
                  <div className="text-right">
                    <span className="text-[11px] text-ink-muted block font-medium">Signals</span>
                    <span className="font-mono font-bold text-lg text-lens">
                      7 observed
                    </span>
                  </div>
                </div>
              </div>

              {/* Miniature Points Breakdown (7 signals summing to 72 points) */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-semibold text-ink">
                  <span>Evidence Signals Breakdown (Sum = 72 points)</span>
                  <span className="text-ink-muted font-normal text-[11px]">
                    Risk score 72 / 100 (not a probability)
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  {[
                    { name: "Icon Similarity (VISUAL)", points: 20.0, max: 20, desc: "Perceptual hash is 93% similar to official icon." },
                    { name: "Name Look-alike (NAME)", points: 19.5, max: 25, desc: "Added word 'Rewards' to official name." },
                    { name: "Description Similarity (CONTENT)", points: 12.0, max: 15, desc: "Description text overlaps with official copy." },
                    { name: "Link Domain Mismatch (CONTEXT)", points: 8.0, max: 8, desc: "External domain kb-rewards.example." },
                    { name: "Lure Terms (CONTENT)", points: 6.0, max: 6, desc: "Contains urgent rewards and voucher lure terms." },
                    { name: "Thin Footprint (CONTEXT)", points: 6.0, max: 6, desc: "Recently published with minimal rating history." },
                    { name: "Publisher Distance (IDENTITY)", points: 0.0, max: 20, desc: "Publisher differs from registered developer." },
                  ].map((sig, i) => (
                    <div key={i} className="p-3 rounded-panel-nested bg-surface-2 border border-hairline space-y-1.5 hover:border-lens/30 transition-colors">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-ink">{sig.name}</span>
                        <span className="font-mono font-semibold text-ink">{sig.points} / {sig.max} pts</span>
                      </div>
                      <ScoreBar value={sig.points} max={sig.max} />
                      <p className="text-[10px] text-ink-muted">{sig.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Miniature NameDiff */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-ink block">Forensic Name Comparison</span>
                <NameDiff
                  official="Kaveri Bank"
                  candidate="Kaveri Bank Rewards"
                  technique="ADDED_WORD"
                  diffSegments={[
                    { text: "Kaveri Bank", changed: false },
                    { text: " Rewards", changed: true },
                  ]}
                />
              </div>

              {/* Gates Strip */}
              <div className="p-4 rounded-panel-nested bg-surface-2 border border-hairline space-y-2">
                <span className="font-semibold text-xs text-ink block">
                  Corroborating groups: Visual, Content, Context. The name group never counts as corroboration.
                </span>
                <div className="flex flex-wrap gap-2 text-[11px]">
                  <span className="px-2.5 py-0.5 rounded-full bg-teal-500/10 text-teal-700 dark:text-teal-400 border border-teal-500/25 font-semibold">
                    G1 Relevance: PASS
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full bg-surface text-ink-muted border border-hairline font-semibold">
                    G2 Name-only cap: NOT TRIGGERED
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full bg-lens/10 text-lens border border-lens/25 font-semibold">
                    G3 Corroboration: SATISFIED (Visual + Content + Context)
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full bg-surface text-ink-muted border border-hairline font-semibold">
                    G4/G5 Look-alike Gates: NOT TRIGGERED
                  </span>
                </div>
              </div>
            </div>
          </ScrollReveal>
        </section>

        {/* SECTION 6: HONEST ABOUT SOURCES */}
        <section id="sources" aria-labelledby="sources-heading" className="space-y-6">
          <ScrollReveal direction="up">
            <div className="space-y-1">
              <span className="font-mono text-xs uppercase text-lens font-bold tracking-wider">
                Section 5.3 & 15.3 Transparency
              </span>
              <h2 id="sources-heading" className="font-display font-bold text-2xl sm:text-3xl text-ink">
                Honest about sources
              </h2>
              <p className="text-base font-semibold text-ink max-w-2xl">
                A failed source is a failure, never a clean result.
              </p>
            </div>
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {[
              {
                status: "LIVE" as const,
                title: "Live Provider",
                copy: "Real-time query sent directly to platform catalog APIs.",
              },
              {
                status: "CACHED" as const,
                cacheTime: "05:12 UTC",
                title: "Cached Replay",
                copy: "Cached result from 05:12 UTC",
              },
              {
                status: "SIMULATED" as const,
                title: "Simulated Record",
                copy: "Simulated demo record",
              },
              {
                status: "NOT_CONNECTED" as const,
                title: "Unconnected Source",
                copy: "Instagram: not connected. Requires platform API access. Not queried.",
              },
              {
                status: "RATE_LIMITED" as const,
                title: "Rate Limited Source",
                copy: "Bluesky: rate limited. Stopped after 4 of 6 queries; partial results kept.",
              },
            ].map((s, idx) => (
              <ScrollReveal key={idx} delayMs={idx * 70}>
                <div
                  className="h-full p-4 rounded-panel bg-surface border border-hairline shadow-xs flex flex-col justify-between space-y-3 hover:-translate-y-1 hover:shadow-md hover:border-lens/30 transition-all duration-300"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-ink">{s.title}</span>
                    </div>
                    <div>
                      <SourceBadge status={s.status} cacheTime={s.cacheTime} />
                    </div>
                  </div>
                  <p className="text-[11px] text-ink-muted leading-relaxed font-mono">
                    {s.copy}
                  </p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </section>

        {/* SECTION 7: MEASURED, NOT CLAIMED */}
        <section id="evaluation" aria-labelledby="eval-heading" className="space-y-6">
          <ScrollReveal direction="up">
            <div className="space-y-1">
              <span className="font-mono text-xs uppercase text-lens font-bold tracking-wider">
                Section 14 Scientific Evaluation Harness
              </span>
              <h2 id="eval-heading" className="font-display font-bold text-2xl sm:text-3xl text-ink">
                Measured, not claimed
              </h2>
              <p className="text-sm text-ink-muted max-w-2xl">
                Precision, recall, and false-positive rates computed deterministically from labelled benchmarks with Wilson 95% intervals.
              </p>
            </div>
          </ScrollReveal>

          <ScrollReveal delayMs={100}>
            <div className="rounded-panel bg-surface p-6 sm:p-8 border border-hairline shadow-xs space-y-6 hover:shadow-md transition-shadow duration-300">
              {isEvalError || !latestEval || latestEval.precision === null || latestEval.precision === undefined ? (
                <div className="p-8 text-center space-y-2">
                  <p className="text-sm text-ink-muted">No evaluation run yet.</p>
                  <p className="text-xs text-ink-muted">
                    Run the offline test harness from the Evaluation Lab to generate benchmark metrics.
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="p-3.5 rounded-panel-nested bg-surface-2 border border-hairline text-xs font-semibold text-ink">
                    Positives are synthetic; negatives are real captured namesakes labelled by the team.
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {/* Precision */}
                    <div className="p-5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
                      <span className="text-xs font-medium text-ink-muted block">Precision</span>
                      <span className="font-mono font-bold text-2xl sm:text-3xl text-ink block">
                        {latestEval.precision.toFixed(2)}
                      </span>
                      {latestEval.confidence_intervals?.precision && (
                        <span className="font-mono text-xs text-lens block">
                          95% CI: [{latestEval.confidence_intervals.precision[0].toFixed(2)}, {latestEval.confidence_intervals.precision[1].toFixed(2)}]
                        </span>
                      )}
                      <span className="text-[10px] text-ink-muted block pt-1">
                        TP / (TP + FP)
                      </span>
                    </div>

                    {/* Recall */}
                    <div className="p-5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
                      <span className="text-xs font-medium text-ink-muted block">Recall</span>
                      <span className="font-mono font-bold text-2xl sm:text-3xl text-ink block">
                        {latestEval.recall !== null && latestEval.recall !== undefined
                          ? latestEval.recall.toFixed(2)
                          : "Not defined"}
                      </span>
                      {latestEval.confidence_intervals?.recall && (
                        <span className="font-mono text-xs text-lens block">
                          95% CI: [{latestEval.confidence_intervals.recall[0].toFixed(2)}, {latestEval.confidence_intervals.recall[1].toFixed(2)}]
                        </span>
                      )}
                      <span className="text-[10px] text-ink-muted block pt-1">
                        TP / (TP + FN)
                      </span>
                    </div>

                    {/* False Positive Rate */}
                    <div className="p-5 rounded-panel-nested bg-surface-2 border border-hairline space-y-1">
                      <span className="text-xs font-medium text-ink-muted block">False-Positive Rate</span>
                      <span className="font-mono font-bold text-2xl sm:text-3xl text-ink block">
                        {latestEval.false_positive_rate !== null && latestEval.false_positive_rate !== undefined
                          ? latestEval.false_positive_rate.toFixed(2)
                          : "Not defined"}
                      </span>
                      {latestEval.confidence_intervals?.false_positive_rate && (
                        <span className="font-mono text-xs text-lens block">
                          95% CI: [{latestEval.confidence_intervals.false_positive_rate[0].toFixed(2)}, {latestEval.confidence_intervals.false_positive_rate[1].toFixed(2)}]
                        </span>
                      )}
                      <span className="text-[10px] text-ink-muted block pt-1">
                        FP / (FP + TN)
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs text-ink-muted pt-2 border-t border-hairline">
                    <span>Harness split: {latestEval.split} · Sample count: {latestEval.sample_count} cases</span>
                    <Link to="/evaluation" className="text-lens font-semibold hover:underline flex items-center gap-1">
                      <span>Inspect Full Evaluation Lab</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              )}
            </div>
          </ScrollReveal>
        </section>

        {/* CLOSING PANEL */}
        <section aria-label="Demo Action Callout">
          <ScrollReveal direction="up">
            <div className="rounded-panel md:rounded-[32px] bg-ink text-white p-8 sm:p-12 text-center space-y-5 shadow-sm hover:shadow-floating transition-shadow duration-300">
              <h2 className="font-display font-bold text-2xl sm:text-3xl md:text-4xl text-white">
                Candidates for review, not verdicts.
              </h2>
              <p className="text-white/80 text-sm sm:text-base max-w-xl mx-auto leading-relaxed">
                Experience the complete digital risk monitoring workspace with live catalog queries,
                forensic character diffs, and exact identity clearing.
              </p>
              <div className="pt-2">
                <Link
                  to="/"
                  className="inline-flex items-center gap-2 px-8 py-3.5 rounded-pill bg-white text-ink font-semibold text-sm hover:bg-white/90 hover:scale-105 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens transition-all shadow-md"
                >
                  <span>Open the demo workspace</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </ScrollReveal>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="border-t border-hairline bg-surface py-8 text-xs text-ink-muted">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-ink">ThreatLens</span>
            <span>· Contract v{contractVersion}</span>
            <span>·</span>
            <span>HacXLerate 2026 · Challenge 3: Digital Risk Protection — Social & App Monitoring (Kampus.VC)</span>
          </div>

          <div className="flex items-center gap-4">
            <Link to="/welcome" className="hover:text-ink transition-colors">
              Welcome
            </Link>
            <Link to="/" className="hover:text-ink transition-colors">
              Workspace
            </Link>
            <Link to="/evaluation" className="hover:text-ink transition-colors">
              Evaluation
            </Link>
          </div>
        </div>
      </footer>

      {/* Back to top floating button */}
      {showBackToTop && (
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          aria-label="Scroll to top of page"
          className="fixed bottom-6 right-6 z-40 p-3 rounded-full bg-ink text-white shadow-floating border border-hairline/20 hover:bg-ink/90 hover:scale-110 active:scale-95 transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens"
        >
          <ArrowUp className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

export default WelcomePage;

