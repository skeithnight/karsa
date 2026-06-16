import os

files = {}

# Providers
files['src/providers/index.tsx'] = """'use client';

import React from 'react';
import { QueryProvider } from './query-provider';
import { ThemeProvider } from './theme-provider';

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <QueryProvider>
      <ThemeProvider>
        {children}
      </ThemeProvider>
    </QueryProvider>
  );
}
"""

files['src/providers/query-provider.tsx'] = """'use client';

import React from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '../hooks/query-client';

export function QueryProvider({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
"""

files['src/providers/theme-provider.tsx'] = """'use client';

import React, from 'react';
import { useUIStore } from '../state/useUIStore';

// Simple theme provider leveraging existing tailwind 'dark' class
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const isDarkMode = useUIStore((state) => state.isDarkMode);

  React.useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  return <>{children}</>;
}
"""

# Config
files['src/config/navigation.ts'] = """export interface NavItem {
  label: string;
  href: string;
  icon: string;
  owner: string;
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'CIO Dashboard', href: '/', icon: 'layout-dashboard', owner: 'CIO' },
  { label: 'Portfolio', href: '/portfolio', icon: 'pie-chart', owner: 'Portfolio' },
  { label: 'Research', href: '/research', icon: 'file-text', owner: 'Research' },
  { label: 'Theses', href: '/theses', icon: 'book-open', owner: 'Theses' },
  { label: 'Memos', href: '/memos', icon: 'file', owner: 'Memos' },
  { label: 'Performance', href: '/performance', icon: 'trending-up', owner: 'Performance' },
  { label: 'Analysts', href: '/analysts', icon: 'users', owner: 'Analysts' },
  { label: 'Oversight', href: '/oversight', icon: 'shield', owner: 'Governance' },
  { label: 'Infrastructure', href: '/infrastructure', icon: 'settings', owner: 'Platform Operations' },
];
"""

# State
files['src/state/useUIStore.ts'] = """import { create } from 'zustand';

interface UIState {
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
  isSearchOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  toggleSearch: () => void;
  isDarkMode: boolean;
  toggleTheme: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  isSidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
  isSearchOpen: false,
  setSearchOpen: (open) => set({ isSearchOpen: open }),
  toggleSearch: () => set((state) => ({ isSearchOpen: !state.isSearchOpen })),
  isDarkMode: false,
  toggleTheme: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
}));
"""

# Layout components
files['src/components/layout/AppLayout.tsx'] = """'use client';

import React from 'react';
import { GlobalSidebar } from './GlobalSidebar';
import { GlobalHeader } from './GlobalHeader';
import { WorkspaceErrorBoundary } from '../error/WorkspaceErrorBoundary';
import { useUIStore } from '../../state/useUIStore';

export function AppLayout({ children }: { children: React.ReactNode }) {
  const isSidebarCollapsed = useUIStore((state) => state.isSidebarCollapsed);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <GlobalSidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <GlobalHeader />
        <main className="flex-1 overflow-y-auto p-6 bg-slate-50 dark:bg-slate-900">
          <WorkspaceErrorBoundary>
            {children}
          </WorkspaceErrorBoundary>
        </main>
      </div>
    </div>
  );
}
"""

files['src/components/layout/GlobalSidebar.tsx'] = """'use client';

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
"""

files['src/components/layout/GlobalHeader.tsx'] = """'use client';

import React, { useState } from 'react';
import { useUIStore } from '../../state/useUIStore';
import { SearchCommandPalette } from '../shared/SearchCommandPalette';
import { useSearch } from '../../hooks/search';
import { usePathname } from 'next/navigation';
import { NAV_ITEMS } from '../../config/navigation';

export function GlobalHeader() {
  const { isSearchOpen, setSearchOpen, toggleTheme, isDarkMode } = useUIStore();
  const [searchText, setSearchText] = useState("");
  
  // Wave-6 Integration
  const searchResults = useSearch(searchText);
  
  const pathname = usePathname();
  const currentNav = NAV_ITEMS.find(item => item.href === pathname);
  const pageTitle = currentNav ? currentNav.label : 'Karsa Web Console';

  return (
    <header className="flex h-16 items-center justify-between px-6 border-b bg-white dark:bg-slate-950">
      <h1 className="text-xl font-semibold">{pageTitle}</h1>
      <div className="flex items-center space-x-4">
        <button 
          onClick={() => setSearchOpen(true)}
          className="px-3 py-1.5 text-sm text-slate-500 bg-slate-100 dark:bg-slate-800 rounded-md flex items-center space-x-2"
        >
          <span>Search...</span>
          <kbd className="font-mono text-xs bg-slate-200 dark:bg-slate-700 px-1 rounded">Cmd K</kbd>
        </button>
        <button onClick={toggleTheme} className="p-2 rounded-full hover:bg-slate-100">
          {isDarkMode ? '🌞' : '🌙'}
        </button>
      </div>

      <SearchCommandPalette 
        isOpen={isSearchOpen} 
        setIsOpen={setSearchOpen}
        searchText={searchText}
        setSearchText={setSearchText}
      />
    </header>
  );
}
"""

# Error Boundaries
files['src/components/error/GlobalErrorBoundary.tsx'] = """'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ErrorState } from '../shared/ErrorState';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class GlobalErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
          <ErrorState 
            errorMessage={`Catastrophic Failure: ${this.state.error?.message}`}
            onRetry={() => window.location.reload()} 
          />
        </div>
      );
    }
    return this.props.children;
  }
}
"""

files['src/components/error/WorkspaceErrorBoundary.tsx'] = """'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ErrorState } from '../shared/ErrorState';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class WorkspaceErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Workspace error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <ErrorState 
            errorMessage={`Workspace Error: ${this.state.error?.message}`}
            onRetry={() => this.setState({ hasError: false, error: null })} 
          />
        </div>
      );
    }
    return this.props.children;
  }
}
"""

# App root layout
files['src/app/layout.tsx'] = """import './globals.css';
import { AppProviders } from '../providers';
import { GlobalErrorBoundary } from '../components/error/GlobalErrorBoundary';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <GlobalErrorBoundary>
          <AppProviders>
            {children}
          </AppProviders>
        </GlobalErrorBoundary>
      </body>
    </html>
  );
}
"""

# Route Scaffolds
routes = [
  ('src/app/page.tsx', 'CIO Dashboard Workspace'),
  ('src/app/portfolio/page.tsx', 'Portfolio Workspace'),
  ('src/app/research/page.tsx', 'Research Workspace'),
  ('src/app/theses/page.tsx', 'Theses Workspace'),
  ('src/app/theses/[id]/page.tsx', 'Thesis Detail Workspace'),
  ('src/app/memos/page.tsx', 'Memos Workspace'),
  ('src/app/performance/page.tsx', 'Performance Workspace'),
  ('src/app/analysts/page.tsx', 'Analysts Workspace'),
  ('src/app/oversight/page.tsx', 'Oversight Workspace'),
  ('src/app/infrastructure/page.tsx', 'Infrastructure Workspace'),
]

for filepath, title in routes:
    files[filepath] = f"""import React from 'react';
import {{ AppLayout }} from '../../components/layout/AppLayout';
import {{ PageHeader }} from '../../components/shared/PageHeader';

export default function Page() {{
  return (
    <AppLayout>
      <PageHeader title="{title}" description="Placeholder content for {title}" />
      <div className="mt-6 border-4 border-dashed border-slate-200 rounded-xl h-64 flex items-center justify-center text-slate-400">
        {title} Placeholder
      </div>
    </AppLayout>
  );
}}
"""

# Special fix for root page to point to `../components...` and nested routes to point appropriately
for filepath, title in routes:
    depth = filepath.count('/') - 1
    rel_path = '../' * depth
    if filepath == 'src/app/page.tsx':
        rel_path = '../'
    files[filepath] = f"""import React from 'react';
import {{ AppLayout }} from '{rel_path}components/layout/AppLayout';
import {{ PageHeader }} from '{rel_path}components/shared/PageHeader';

export default function Page() {{
  return (
    <AppLayout>
      <PageHeader title="{title}" description="Placeholder content for {title}" />
      <div className="mt-6 border-4 border-dashed border-slate-200 rounded-xl h-64 flex items-center justify-center text-slate-400">
        {title} Placeholder
      </div>
    </AppLayout>
  );
}}
"""

for path, content in files.items():
    full_path = os.path.join(path)
    d = os.path.dirname(full_path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

print("Generated all application shell files")
