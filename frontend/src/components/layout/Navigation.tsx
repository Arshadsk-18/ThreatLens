import React from 'react';
import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  Layers,
  Shield,
  Search,
  AlertOctagon,
  CheckCircle2,
  Radio,
  FlaskConical,
} from 'lucide-react';

interface NavItem {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { label: 'Overview', path: '/', icon: Layers },
  { label: 'Brand profile', path: '/brand', icon: Shield },
  { label: 'Scans', path: '/scan', icon: Search },
  { label: 'Findings queue', path: '/findings', icon: AlertOctagon },
  { label: 'Cleared items', path: '/cleared', icon: CheckCircle2 },
  { label: 'Source coverage', path: '/sources', icon: Radio },
  { label: 'Evaluation lab', path: '/evaluation', icon: FlaskConical },
];

export function Navigation({ className }: { className?: string }) {
  return (
    <nav
      aria-label="Main Navigation"
      className={cn('flex items-center space-x-1.5 overflow-x-auto py-2', className)}
    >
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2 px-3.5 py-1.5 rounded-pill text-xs font-medium transition-all whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lens',
                isActive
                  ? 'bg-ink text-surface dark:bg-surface dark:text-ink font-semibold shadow-sm'
                  : 'text-ink-muted hover:bg-surface-2 hover:text-ink'
              )
            }
          >
            <Icon className="w-3.5 h-3.5" aria-hidden="true" />
            <span>{item.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
