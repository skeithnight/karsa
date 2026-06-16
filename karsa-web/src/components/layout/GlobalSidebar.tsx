'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { NAV_ITEMS } from '../../config/navigation';
import { useUIStore } from '../../state/useUIStore';
import { LayoutDashboard, PieChart, FileText, BookOpen, File, TrendingUp, Users, Shield, Settings } from 'lucide-react';

const ICONS: Record<string, any> = {
  'layout-dashboard': LayoutDashboard,
  'pie-chart': PieChart,
  'file-text': FileText,
  'book-open': BookOpen,
  'file': File,
  'trending-up': TrendingUp,
  'users': Users,
  'shield': Shield,
  'settings': Settings,
};

export function GlobalSidebar() {
  const pathname = usePathname();
  const isSidebarCollapsed = useUIStore((state) => state.isSidebarCollapsed);
  const toggleSidebar = useUIStore((state) => state.toggleSidebar);

  return (
    <aside className={`border-r bg-white dark:bg-slate-950 transition-all duration-300 ${isSidebarCollapsed ? 'w-16' : 'w-64'}`}>
      <div className="flex h-16 items-center justify-between px-4 border-b">
        {!isSidebarCollapsed && <span className="font-bold text-lg">Karsa Console</span>}
        <button onClick={toggleSidebar} className="p-1 hover:bg-slate-100 rounded">
          <span className="sr-only">Toggle Sidebar</span>
          {/* Menu icon placeholder */}
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
      </div>
      <nav className="p-2 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = ICONS[item.icon] || FileText;
          return (
            <Link key={item.href} href={item.href} className={`flex items-center space-x-2 px-2 py-2 rounded-md transition-colors ${isActive ? 'bg-slate-100 dark:bg-slate-800 text-blue-600' : 'text-slate-600 hover:bg-slate-50'}`}>
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!isSidebarCollapsed && <span className="text-sm font-medium">{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
