import React, { useState, useRef, useEffect } from "react";
import { useBrand } from "@/context/useBrand";
import { Building2, ChevronDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";

export function BrandSwitcher({ collapsed = false }: { collapsed?: boolean }) {
  const { activeBrand, brands, setActiveBrandId } = useBrand();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!activeBrand) return null;

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={cn(
          "w-full flex items-center justify-between gap-2.5 p-2 rounded-xl bg-surface-2 border border-hairline hover:border-ink/20 transition-all text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens",
          collapsed && "justify-center px-2"
        )}
        title={`Active brand: ${activeBrand.name}`}
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-7 h-7 rounded-lg bg-surface border border-hairline flex items-center justify-center shrink-0 text-lens">
            <Building2 className="w-4 h-4" aria-hidden="true" />
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-xs text-ink truncate">
                  {activeBrand.name}
                </span>
                {activeBrand.demo_brand && (
                  <span className="font-mono text-[9px] px-1.5 py-0.2 rounded-pill bg-[#6D28D9]/10 text-[#6D28D9] dark:text-[#C4B5FD] border border-[#6D28D9]/30 font-medium">
                    DEMO
                  </span>
                )}
              </div>
              <p className="text-[10px] text-ink-muted truncate">
                {activeBrand.industry_category}
              </p>
            </div>
          )}
        </div>
        {!collapsed && (
          <ChevronDown
            className={cn(
              "w-3.5 h-3.5 text-ink-muted shrink-0 transition-transform",
              isOpen && "rotate-180"
            )}
            aria-hidden="true"
          />
        )}
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full mt-1.5 w-60 z-50 bg-surface rounded-xl border border-hairline shadow-floating p-1.5 animate-in fade-in slide-in-from-top-1">
          <div className="px-2.5 py-1.5 text-[10px] font-semibold text-ink-muted uppercase tracking-wider">
            Switch Monitored Brand
          </div>
          <div className="space-y-1">
            {brands.map((brand) => (
              <button
                key={brand.id}
                type="button"
                onClick={() => {
                  setActiveBrandId(brand.id);
                  setIsOpen(false);
                }}
                className={cn(
                  "w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-xs transition-colors",
                  brand.id === activeBrand.id
                    ? "bg-surface-2 font-medium text-ink"
                    : "text-ink-muted hover:bg-surface-2 hover:text-ink"
                )}
              >
                <div className="flex items-center gap-2 overflow-hidden">
                  <span className="truncate">{brand.name}</span>
                  {brand.demo_brand && (
                    <span className="font-mono text-[9px] px-1 rounded-pill bg-[#6D28D9]/10 text-[#6D28D9] dark:text-[#C4B5FD]">
                      DEMO
                    </span>
                  )}
                </div>
                {brand.id === activeBrand.id && (
                  <Check className="w-3.5 h-3.5 text-lens shrink-0" aria-hidden="true" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
