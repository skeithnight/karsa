import './globals.css';
import { AppProviders } from '../providers';
import { GlobalErrorBoundary } from '../components/error/GlobalErrorBoundary';
import AppShell from '../components/layout/AppShell';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <AppProviders>
          <GlobalErrorBoundary>
            <AppShell>
              {children}
            </AppShell>
          </GlobalErrorBoundary>
        </AppProviders>
      </body>
    </html>
  );
}
