'use client';

import { useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  Bolt,
  ChartPie,
  TrendingUp,
  ShieldCheck,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Tab {
  label: string;
  path: string;
  icon: React.ElementType;
}

const TABS: Tab[] = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'Signals', path: '/signals', icon: Bolt },
  { label: 'Portfolio', path: '/portfolio', icon: ChartPie },
  { label: 'Performance', path: '/performance', icon: TrendingUp },
  { label: 'Governance', path: '/governance', icon: ShieldCheck },
];

interface TopTabBarProps {
  activePath: string;
}

export default function TopTabBar({ activePath }: TopTabBarProps) {
  const router = useRouter();

  const isActive = (tab: Tab) => {
    if (tab.path === '/') return activePath === '/';
    return activePath.startsWith(tab.path);
  };

  return (
    <nav className="flex items-center border-b border-gray-800 bg-gray-900 px-4">
      <span className="mr-6 text-xl font-bold text-indigo-400">K</span>
      <ul className="flex gap-1">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const active = isActive(tab);
          return (
            <li key={tab.path}>
              <button
                onClick={() => router.push(tab.path)}
                className={cn(
                  'flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors',
                  active
                    ? 'border-b-2 border-indigo-500 text-indigo-400'
                    : 'text-gray-400 hover:text-gray-200'
                )}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
