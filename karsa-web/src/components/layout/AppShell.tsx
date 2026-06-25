'use client';

import { usePathname } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import TopTabBar from './TopTabBar';
import TickerTape from '../shared/TickerTape';
import { ApiClient } from '@/api/client';

interface AppShellProps {
  children: React.ReactNode;
}

interface TickerItem {
  label: string;
  value: string;
  change: string;
  positive: boolean;
}

const FALLBACK_TICKERS: TickerItem[] = [
  { label: 'IHSG', value: '5,895.47', change: '-1.23%', positive: false },
  { label: 'USD/IDR', value: '15,892', change: '-0.12%', positive: false },
];

function useMarketTicker() {
  return useQuery<TickerItem[]>({
    queryKey: ['market', 'ticker'],
    queryFn: () => ApiClient.fetch<TickerItem[]>('/api/market/ticker'),
    staleTime: 60_000,
    placeholderData: FALLBACK_TICKERS,
  });
}

export default function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const { data: tickers } = useMarketTicker();

  return (
    <div className="flex min-h-screen flex-col bg-gray-950 text-gray-100">
      <TopTabBar activePath={pathname} />
      <TickerTape items={tickers ?? FALLBACK_TICKERS} />
      <main className="flex-1 px-4 py-6 lg:px-8">{children}</main>
    </div>
  );
}
