'use client';

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
