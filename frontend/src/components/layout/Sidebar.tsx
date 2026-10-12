import React from "react";
import { NavLink } from "react-router-dom";
import { useBrand } from "@/context/useBrand";
import { BrandSwitcher } from "./BrandSwitcher";
import { cn } from "@/lib/utils";
import {
  Layers,
  Shield,
  Search,
  AlertOctagon,
  CheckCircle2,
  Radio,
  FlaskConical,
  FileText,
  PanelLeftClose,
  PanelLeftOpen,
  Sun,
  Moon,
  ShieldAlert,
} from "lucide-react";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  isDark: boolean;
  onToggleTheme: () => void;
}

export function Sidebar({
  collapsed,
  onToggleCollapse,
  isDark,
  onToggleTheme,
}: SidebarProps) {
  const { findingsCount, clearedCount } = useBrand();

  const navItems = [
    { label: "Overview", path: "/", icon: Layers },
    { label: "Brand Profile", path: "/brand", icon: Shield },
    { label: "Scans", path: "/scan", icon: Search },
    {
      label: "Findings",
      path: "/findings",
      icon: AlertOctagon,
      badge: findingsCount,
      badgeVariant: "findings",
    },
    {
      label: "Cleared",
      path: "/cleared",
      icon: CheckCircle2,
      badge: clearedCount,
      badgeVariant: "cleared",
    },
    { label: "Source Coverage", path: "/sources", icon: Radio },
    { label: "Evaluation Lab", path: "/evaluation", icon: FlaskConical },
    {
      label: "Report (P1)",
      path: "/report/rep-sample-01",
      icon: FileText,
      isP1: true,
    },
  ];

  return (
    <aside
      className={cn(
        "h-screen sticky top-0 bg-surface border-r border-hairline flex flex-col justify-between transition-all duration-200 z-30 select-none",
        collapsed ? "w-20" : "w-64"
      )}
      aria-label="Risk Platform Navigation"
    >
      <div className="flex flex-col gap-4 p-4">
        {/* Brand header / Platform title */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-pill bg-ink text-surface dark:bg-surface dark:text-ink flex items-center justify-center font-display font-bold text-sm shrink-0 shadow-sm">
              <ShieldAlert className="w-4 h-4 fill-current" aria-hidden="true" />
            </div>
            {!collapsed && (
              <div className="overflow-hidden">
                <span className="font-display font-bold text-base tracking-tight text-ink block leading-none">
                  ThreatLens
                </span>
                <span className="text-[10px] font-mono text-ink-muted">v3.0.0 · Forensic</span>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={onToggleCollapse}
            className="w-7 h-7 rounded-lg text-ink-muted hover:text-ink hover:bg-surface-2 flex items-center justify-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <PanelLeftOpen className="w-4 h-4" />
            ) : (
              <PanelLeftClose className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Brand switcher */}
        <BrandSwitcher collapsed={collapsed} />

        {/* Navigation list */}
        <nav className="space-y-1 mt-1" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-colors group relative focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens",
                    isActive
                      ? "bg-ink text-surface dark:bg-surface dark:text-ink shadow-sm font-semibold"
                      : "text-ink-muted hover:bg-surface-2 hover:text-ink",
                    collapsed && "justify-center px-0"
                  )
                }
                title={collapsed ? item.label : undefined}
              >
                {({ isActive }) => (
                  <>
                    <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                    {!collapsed && (
                      <span className="truncate flex-1">{item.label}</span>
                    )}

                    {/* Findings & Cleared Badges */}
                    {!collapsed && item.badge !== undefined && (
                      <span
                        className={cn(
                          "px-2 py-0.5 rounded-pill font-mono text-[10px] font-semibold shrink-0 transition-colors",
                          item.badgeVariant === "findings"
                            ? isActive
                              ? "bg-surface/20 text-surface dark:bg-ink/20 dark:text-ink"
                              : "bg-[#D9480F]/10 text-[#D9480F] border border-[#D9480F]/20"
                            : isActive
                            ? "bg-surface/20 text-surface dark:bg-ink/20 dark:text-ink"
                            : "bg-[#0E8F9C]/10 text-[#0E8F9C] border border-[#0E8F9C]/20"
                        )}
                      >
                        {item.badge}
                      </span>
                    )}

                    {/* Small badge in collapsed mode */}
                    {collapsed && item.badge !== undefined && (
                      <span
                        className={cn(
                          "absolute top-1 right-1 w-2 h-2 rounded-full",
                          item.badgeVariant === "findings" ? "bg-[#D9480F]" : "bg-[#0E8F9C]"
                        )}
                      />
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer controls inside sidebar */}
      <div className="p-4 border-t border-hairline flex flex-col gap-2">
        <div
          className={cn(
            "flex items-center gap-2",
            collapsed ? "flex-col justify-center" : "justify-between"
          )}
        >
          <button
            type="button"
            onClick={onToggleTheme}
            className="w-8 h-8 rounded-lg bg-surface-2 border border-hairline flex items-center justify-center text-ink-muted hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens"
            title={isDark ? "Switch to light theme" : "Switch to dark theme"}
            aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          {!collapsed && (
            <div className="text-[11px] font-mono text-ink-muted">
              <span>mode=</span>
              <span className="font-semibold text-lens">DEMO</span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
