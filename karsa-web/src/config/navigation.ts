export interface NavItem {
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
  { label: 'Proposals', href: '/proposals', icon: 'file-check', owner: 'Capital Allocation' },
  { label: 'Investments', href: '/investments', icon: 'target', owner: 'Investment Workflow' },
  { label: 'Analytics', href: '/analytics', icon: 'bar-chart-2', owner: 'Analytics' },
  { label: 'Forecasts', href: '/analytics/forecasts', icon: 'crystal-ball', owner: 'Analytics' },
  { label: 'Attribution', href: '/performance/attribution', icon: 'pie-chart', owner: 'Performance' },
  { label: 'Policies', href: '/oversight/policies', icon: 'shield-check', owner: 'Governance' },
];

export const NAV_TABS = [
  { label: 'Dashboard', href: '/', icon: 'LayoutDashboard' },
  { label: 'Signals', href: '/signals', icon: 'Bolt' },
  { label: 'Portfolio', href: '/portfolio', icon: 'ChartPie' },
  { label: 'Performance', href: '/performance', icon: 'TrendingUp' },
  { label: 'Governance', href: '/governance', icon: 'ShieldCheck' },
] as const;
