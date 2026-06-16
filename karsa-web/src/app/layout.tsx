import './globals.css';
import { AppProviders } from '../providers';
import { GlobalErrorBoundary } from '../components/error/GlobalErrorBoundary';
import { AppLayout } from '../components/layout/AppLayout';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <AppProviders>
          <GlobalErrorBoundary>
            <AppLayout>
              {children}
            </AppLayout>
          </GlobalErrorBoundary>
        </AppProviders>
      </body>
    </html>
  );
}
