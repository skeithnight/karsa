import React from 'react';
import { useRouter } from 'next/navigation';
import { DataTable } from '../../../components/grid/DataTable';
import { ThesisVM } from '../../theses/types/viewmodels';

interface ThesisGridProps {
  data: ThesisVM[];
}

export function ThesisGrid({ data }: ThesisGridProps) {
  const router = useRouter();
  
  return (
    <DataTable 
      rowData={data} 
      columnDefs={[
        { field: 'title', headerName: 'Title' }, 
        { field: 'status', headerName: 'Status' }, 
        { field: 'confidence', headerName: 'Confidence' },
        { field: 'author_urn', headerName: 'Author' },
        { field: 'regime_urn', headerName: 'Regime' },
        { field: 'version', headerName: 'Version' }
      ]} 
      onRowClick={(row: ThesisVM) => router.push(`/theses/${row.urn}`)}
    />
  );
}
