'use client';

import React from 'react';
import { QueryProvider } from './query-provider';
import { ThemeProvider } from './theme-provider';
import { NotificationProvider, ToastContainer } from '../components/shared/NotificationCenter';

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <QueryProvider>
      <ThemeProvider>
        <NotificationProvider>
          {children}
          <ToastContainer />
        </NotificationProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}
