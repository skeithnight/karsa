import os

def write_test(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

write_test("src/app/portfolio/__tests__/page.test.tsx", """
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import PortfolioWorkspace from '../page';
import { usePortfolioExposure } from '../../../hooks/portfolio';

vi.mock('../../../hooks/portfolio');

describe('PortfolioWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders LoadingSkeleton', () => {
    vi.mocked(usePortfolioExposure).mockReturnValue({ isLoading: true } as any);
    render(<PortfolioWorkspace />);
    expect(screen.getAllByTestId('loading-skeleton').length).toBeGreaterThan(0);
  });

  it('renders ErrorState', () => {
    vi.mocked(usePortfolioExposure).mockReturnValue({ isError: true, error: new Error('Err') } as any);
    render(<PortfolioWorkspace />);
    expect(screen.getByTestId('error-state')).toBeInTheDocument();
  });

  it('renders EmptyState', () => {
    vi.mocked(usePortfolioExposure).mockReturnValue({ data: { sectors: [] }, isLoading: false } as any);
    render(<PortfolioWorkspace />);
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
  });

  it('renders primary content', () => {
    vi.mocked(usePortfolioExposure).mockReturnValue({ data: { sectors: [{ sector: 'Tech', allocationPctDisplay: '50%' }] }, isLoading: false } as any);
    render(<PortfolioWorkspace />);
    expect(screen.getByText('Tech')).toBeInTheDocument();
  });
});
""")

write_test("src/app/research/__tests__/page.test.tsx", """
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import ResearchWorkspace from '../page';
import { useListResearchReports } from '../../../hooks/research';

vi.mock('../../../hooks/research');

describe('ResearchWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders LoadingSkeleton', () => {
    vi.mocked(useListResearchReports).mockReturnValue({ isLoading: true } as any);
    render(<ResearchWorkspace />);
    expect(screen.getAllByTestId('loading-skeleton').length).toBeGreaterThan(0);
  });

  it('renders ErrorState', () => {
    vi.mocked(useListResearchReports).mockReturnValue({ isError: true, error: new Error('Err') } as any);
    render(<ResearchWorkspace />);
    expect(screen.getByTestId('error-state')).toBeInTheDocument();
  });

  it('renders EmptyState', () => {
    vi.mocked(useListResearchReports).mockReturnValue({ data: { data: [] }, isLoading: false } as any);
    render(<ResearchWorkspace />);
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
  });

  it('renders primary content', () => {
    vi.mocked(useListResearchReports).mockReturnValue({ data: { data: [{ ticker: 'AAPL', analystId: 'A1', publishedAtDisplay: 'Now' }] }, isLoading: false } as any);
    render(<ResearchWorkspace />);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
  });
});
""")

write_test("src/app/theses/__tests__/page.test.tsx", """
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ThesesWorkspace from '../page';
import { useListTheses } from '../../../hooks/theses';
import { useRouter } from 'next/navigation';

vi.mock('../../../hooks/theses');
vi.mock('next/navigation', () => ({ useRouter: vi.fn() }));

describe('ThesesWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders LoadingSkeleton', () => {
    vi.mocked(useRouter).mockReturnValue({ push: vi.fn() } as any);
    vi.mocked(useListTheses).mockReturnValue({ isLoading: true } as any);
    render(<ThesesWorkspace />);
    expect(screen.getAllByTestId('loading-skeleton').length).toBeGreaterThan(0);
  });

  it('renders ErrorState', () => {
    vi.mocked(useRouter).mockReturnValue({ push: vi.fn() } as any);
    vi.mocked(useListTheses).mockReturnValue({ isError: true, error: new Error('Err') } as any);
    render(<ThesesWorkspace />);
    expect(screen.getByTestId('error-state')).toBeInTheDocument();
  });

  it('renders EmptyState', () => {
    vi.mocked(useRouter).mockReturnValue({ push: vi.fn() } as any);
    vi.mocked(useListTheses).mockReturnValue({ data: { data: [] }, isLoading: false } as any);
    render(<ThesesWorkspace />);
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
  });

  it('renders primary content and navigates on row click', () => {
    const pushMock = vi.fn();
    vi.mocked(useRouter).mockReturnValue({ push: pushMock } as any);
    vi.mocked(useListTheses).mockReturnValue({ data: { data: [{ thesisUrn: '1', ticker: 'AAPL', direction: 'LONG', convictionScoreDisplay: '5' }] }, isLoading: false } as any);
    render(<ThesesWorkspace />);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    
    // Simulate row click
    fireEvent.click(screen.getByText('AAPL'));
    expect(pushMock).toHaveBeenCalledWith('/theses/1');
  });
});
""")

write_test("src/app/theses/[id]/__tests__/page.test.tsx", """
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import ThesisDetailWorkspace from '../page';
import { useThesisDetail, useThesisLineage } from '../../../../hooks/theses';

vi.mock('../../../../hooks/theses');
vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react')>();
  return { ...actual, use: (p: any) => p };
});

describe('ThesisDetailWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders LoadingSkeleton', () => {
    vi.mocked(useThesisDetail).mockReturnValue({ isLoading: true } as any);
    vi.mocked(useThesisLineage).mockReturnValue({ isLoading: true } as any);
    render(<ThesisDetailWorkspace params={{ id: '1' } as any} />);
    expect(screen.getAllByTestId('loading-skeleton').length).toBeGreaterThan(0);
  });

  it('renders ErrorState', () => {
    vi.mocked(useThesisDetail).mockReturnValue({ isError: true, error: new Error('Err') } as any);
    vi.mocked(useThesisLineage).mockReturnValue({ isLoading: false } as any);
    render(<ThesisDetailWorkspace params={{ id: '1' } as any} />);
    expect(screen.getByTestId('error-state')).toBeInTheDocument();
  });

  it('renders primary content', () => {
    vi.mocked(useThesisDetail).mockReturnValue({ data: { thesisUrn: '1', ticker: 'AAPL', invalidationCriteria: ['Cr 1'] }, isLoading: false } as any);
    vi.mocked(useThesisLineage).mockReturnValue({ data: { sourceResearchIds: ['r1'], decisionUrns: [], governanceReviewIds: [] }, isLoading: false } as any);
    render(<ThesisDetailWorkspace params={{ id: '1' } as any} />);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('Cr 1')).toBeInTheDocument();
  });
});
""")

write_test("src/app/memos/__tests__/page.test.tsx", """
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import MemosWorkspace from '../page';
import { useListMemos } from '../../../hooks/memos';

vi.mock('../../../hooks/memos');

describe('MemosWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders primary content', () => {
    vi.mocked(useListMemos).mockReturnValue({ data: { data: [{ decisionUrn: '1', intent: 'long', timestampDisplay: 'Now' }] }, isLoading: false } as any);
    render(<MemosWorkspace />);
    expect(screen.getByText('long')).toBeInTheDocument();
  });
});
""")

write_test("src/app/analysts/__tests__/page.test.tsx", """
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import AnalystsWorkspace from '../page';
import { useAnalystsMetrics } from '../../../hooks/analysts';

vi.mock('../../../hooks/analysts');

describe('AnalystsWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders primary content', () => {
    vi.mocked(useAnalystsMetrics).mockReturnValue({ data: { data: [{ analystId: 'A1', role: 'W', winRateDisplay: '100%', trustScoreDisplay: '5' }] }, isLoading: false } as any);
    render(<AnalystsWorkspace />);
    expect(screen.getByText('A1')).toBeInTheDocument();
  });
});
""")

write_test("src/app/performance/__tests__/page.test.tsx", """
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import PerformanceWorkspace from '../page';
import { usePerformanceAttribution } from '../../../hooks/performance';

vi.mock('../../../hooks/performance');

describe('PerformanceWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders primary content', () => {
    vi.mocked(usePerformanceAttribution).mockReturnValue({ data: { data: [{ dateDisplay: 'Jan 1', selectionReturnDisplay: '1%', allocationReturnDisplay: '2%' }] }, isLoading: false } as any);
    render(<PerformanceWorkspace />);
    expect(screen.getByText('Jan 1')).toBeInTheDocument();
  });
});
""")

write_test("src/app/oversight/__tests__/page.test.tsx", """
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import OversightWorkspace from '../page';
import { useGovernancePostMortems } from '../../../hooks/governance';

vi.mock('../../../hooks/governance');

describe('OversightWorkspace', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders primary content', () => {
    vi.mocked(useGovernancePostMortems).mockReturnValue({ data: { data: [{ thesisUrn: '1', failureReason: 'F', policyOverridesDisplay: 'S' }] }, isLoading: false } as any);
    render(<OversightWorkspace />);
    expect(screen.getByText('1')).toBeInTheDocument();
  });
});
""")

write_test("src/app/infrastructure/__tests__/page.test.tsx", """
import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import InfrastructureWorkspace from '../page';

describe('InfrastructureWorkspace', () => {
  it('renders primary content', () => {
    render(<InfrastructureWorkspace />);
    expect(screen.getByText('Infrastructure Workspace')).toBeInTheDocument();
  });
});
""")

write_test("src/components/error/__tests__/GlobalErrorBoundary.test.tsx", """
import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GlobalErrorBoundary } from '../GlobalErrorBoundary';

const Bomb = () => { throw new Error('Global crash') };

describe('GlobalErrorBoundary', () => {
  it('catches error and renders fallback', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <GlobalErrorBoundary>
        <Bomb />
      </GlobalErrorBoundary>
    );
    expect(screen.getByText('Something went wrong!')).toBeInTheDocument();
  });
});
""")

write_test("src/components/error/__tests__/WorkspaceErrorBoundary.test.tsx", """
import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WorkspaceErrorBoundary } from '../WorkspaceErrorBoundary';

const Bomb = () => { throw new Error('Workspace crash') };

describe('WorkspaceErrorBoundary', () => {
  it('catches error and renders fallback', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <WorkspaceErrorBoundary>
        <Bomb />
      </WorkspaceErrorBoundary>
    );
    expect(screen.getByText('Workspace crash')).toBeInTheDocument();
  });
});
""")

write_test("src/components/shared/__tests__/SearchCommandPalette.test.tsx", """
import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SearchCommandPalette } from '../SearchCommandPalette';

describe('SearchCommandPalette', () => {
  it('renders properly', () => {
    const setIsOpen = vi.fn();
    const setSearchText = vi.fn();
    render(<SearchCommandPalette isOpen={true} setIsOpen={setIsOpen} searchText="" setSearchText={setSearchText} />);
    expect(screen.getByPlaceholderText('Type a command or search...')).toBeInTheDocument();
  });
});
""")
