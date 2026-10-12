import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { Info, Sparkles } from 'lucide-react';

export interface DiffSegment {
  text: string;
  changed: boolean;
}

export interface NonAsciiChar {
  char: string;
  codepoint: string;
  index: number;
}

export interface NameDiffProps {
  official: string;
  candidate: string;
  diffSegments?: DiffSegment[];
  nonAsciiChars?: NonAsciiChar[];
  technique?: string;
  className?: string;
}

/**
 * Computes simple character-level diff segments if none provided by API.
 */
function computeDiff(official: string, candidate: string): DiffSegment[] {
  if (candidate.startsWith(official)) {
    return [
      { text: official, changed: false },
      { text: candidate.slice(official.length), changed: true },
    ];
  }
  // Character-by-character naive diff
  const segments: DiffSegment[] = [];
  const minLen = Math.min(official.length, candidate.length);
  let cur = '';
  let curChanged: boolean | null = null;

  for (let i = 0; i < minLen; i++) {
    const isCh = official[i] !== candidate[i];
    if (curChanged === null) {
      curChanged = isCh;
      cur = candidate[i];
    } else if (curChanged === isCh) {
      cur += candidate[i];
    } else {
      segments.push({ text: cur, changed: curChanged });
      cur = candidate[i];
      curChanged = isCh;
    }
  }

  if (cur) {
    segments.push({ text: cur, changed: curChanged ?? false });
  }

  if (candidate.length > minLen) {
    segments.push({ text: candidate.slice(minLen), changed: true });
  }

  return segments;
}

/**
 * Finds all non-ASCII characters and their Unicode codepoint representations.
 */
function extractNonAscii(str: string): NonAsciiChar[] {
  const result: NonAsciiChar[] = [];
  for (let i = 0; i < str.length; i++) {
    const code = str.charCodeAt(i);
    if (code > 127) {
      const hex = code.toString(16).toUpperCase().padStart(4, '0');
      result.push({
        char: str[i],
        codepoint: `U+${hex}`,
        index: i,
      });
    }
  }
  return result;
}

export function NameDiff({
  official,
  candidate,
  diffSegments,
  nonAsciiChars,
  technique,
  className,
}: NameDiffProps) {
  const [selectedChar, setSelectedChar] = useState<NonAsciiChar | null>(null);

  const segments = diffSegments || computeDiff(official, candidate);
  const detectedNonAscii = nonAsciiChars || extractNonAscii(candidate);

  return (
    <div className={cn('rounded-nested border border-hairline bg-surface p-4 space-y-4', className)}>
      {/* Header with forensic inspection title */}
      <div className="flex items-center justify-between pb-2 border-b border-hairline">
        <div className="flex items-center gap-2">
          <span className="font-display font-semibold text-sm text-ink">
            Forensic Name Diff
          </span>
          {technique && (
            <span className="font-mono text-[11px] px-2 py-0.5 rounded-pill bg-surface-2 text-ink-muted border border-hairline">
              Technique: {technique}
            </span>
          )}
        </div>
        <span className="text-xs text-ink-muted">
          Character-by-character analysis
        </span>
      </div>

      {/* Official vs Candidate Display */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
        {/* Official Reference String */}
        <div className="p-3 rounded-nested bg-surface-2 border border-hairline space-y-1">
          <span className="text-[11px] font-medium text-ink-muted block">
            Official Reference
          </span>
          <p className="font-sans font-semibold text-ink text-base">
            {official}
          </p>
          <span className="text-[11px] font-mono text-ink-muted block">
            Length: {official.length} chars
          </span>
        </div>

        {/* Candidate with highlighted diffs */}
        <div className="p-3 rounded-nested bg-surface-2 border border-hairline space-y-1">
          <span className="text-[11px] font-medium text-ink-muted block">
            Observed Candidate
          </span>
          <div className="font-sans text-base leading-normal flex flex-wrap items-center">
            {segments.map((seg, sIdx) => {
              if (seg.changed) {
                return (
                  <span
                    key={sIdx}
                    className="font-bold underline decoration-severity-high decoration-2 text-[#AF3405] dark:text-severity-high bg-severity-high/10 px-1 py-0.5 rounded mx-0.5 transition-colors"
                    title="Changed segment"
                  >
                    {seg.text}
                  </span>
                );
              }
              return (
                <span key={sIdx} className="text-ink font-semibold">
                  {seg.text}
                </span>
              );
            })}
          </div>
          <span className="text-[11px] font-mono text-ink-muted block">
            Length: {candidate.length} chars
          </span>
        </div>
      </div>

      {/* Character-by-Character Forensic Tape Ruler */}
      <div className="space-y-1.5 pt-1">
        <div className="flex items-center justify-between text-xs text-ink-muted">
          <span>Character Inspection Tape:</span>
          <span>Click any character chip to inspect codepoint</span>
        </div>
        <div className="flex flex-wrap gap-1 p-2.5 rounded-nested bg-canvas border border-hairline font-mono text-xs overflow-x-auto">
          {Array.from(candidate).map((ch, idx) => {
            const isNonAscii = ch.charCodeAt(0) > 127;
            const isChanged = segments.some((s) => s.changed && s.text.includes(ch));

            return (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  const hex = ch.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0');
                  setSelectedChar({ char: ch, codepoint: `U+${hex}`, index: idx });
                }}
                className={cn(
                  'h-8 min-w-[2rem] px-1.5 rounded flex flex-col items-center justify-center transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens',
                  isNonAscii
                    ? 'bg-lens/15 text-lens border border-lens/40 font-bold shadow-sm'
                    : isChanged
                    ? 'bg-severity-high/15 text-severity-high border border-severity-high/30 font-bold'
                    : 'bg-surface text-ink border border-hairline hover:bg-surface-2'
                )}
                title={`Char: '${ch}' (Index: ${idx}, Code: U+${ch.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0')})`}
              >
                <span className="leading-none text-xs">{ch === ' ' ? '␣' : ch}</span>
                <span className="text-[9px] text-ink/70 dark:text-ink-muted leading-none mt-0.5 font-medium">{idx}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Unicode Codepoints Chips (§11.5 Homoglyph & Non-ASCII) */}
      {detectedNonAscii.length > 0 ? (
        <div className="p-3 rounded-nested bg-lens/5 border border-lens/20 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-lens">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Non-ASCII Characters & Homoglyphs Detected</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {detectedNonAscii.map((item, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill bg-surface text-lens border border-lens/30 font-mono text-xs shadow-sm"
              >
                <span className="font-bold text-sm bg-lens/10 px-1 rounded">{item.char}</span>
                <span className="font-semibold">{item.codepoint}</span>
                <span className="text-ink-muted text-[10px]">(pos {item.index})</span>
              </span>
            ))}
          </div>
          <p className="text-[11px] text-ink-muted">
            Non-ASCII characters in Latin brand names indicate deliberate homoglyph substitution or confusable character insertion.
          </p>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-xs text-ink-muted px-1">
          <Info className="w-3.5 h-3.5" />
          <span>All characters are standard ASCII. Zero homoglyph substitutions observed.</span>
        </div>
      )}

      {/* Selected character popover detail if tapped */}
      {selectedChar && (
        <div className="p-3 rounded-nested bg-surface-2 border border-hairline flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="font-mono text-base font-bold bg-surface px-2 py-0.5 rounded border border-hairline">
              '{selectedChar.char}'
            </span>
            <span className="font-mono font-semibold text-lens">
              {selectedChar.codepoint}
            </span>
            <span className="text-ink-muted">at string position {selectedChar.index}</span>
          </div>
          <button
            onClick={() => setSelectedChar(null)}
            className="text-xs text-ink-muted hover:text-ink underline"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
