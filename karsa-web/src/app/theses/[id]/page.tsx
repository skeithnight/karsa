'use client';
import React, { use } from 'react';
import { PageHeader } from '../../../components/shared/PageHeader';
import { LoadingSkeleton } from '../../../components/shared/LoadingSkeleton';
import { ErrorState } from '../../../components/shared/ErrorState';
import { useThesisDetail } from '../../../hooks/theses';
import { ThesisDetailView } from '../../../features/thesis/pages/ThesisDetailView';

export default function ThesisDetailWorkspace({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const { id } = resolvedParams;
  const { data: detail, isLoading: isLoadingDetail, isError: isErrorDetail, error: detailError, refetch: refetchDetail } = useThesisDetail(id);

  if (isErrorDetail) return <ErrorState errorMessage={detailError?.message} onRetry={refetchDetail} />;

  if (isLoadingDetail || !detail) {
    return (
      <>
        <PageHeader title="Loading Thesis..." description="Retrieving deep conviction logic" />
        <LoadingSkeleton variant="page" />
      </>
    );
  }

  return <ThesisDetailView detail={detail} />;
}
