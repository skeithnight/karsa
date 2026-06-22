/**
 * Export utilities for CSV generation
 * Phase-1: Data export functionality
 */

/** Convert array of objects to CSV string */
export function objectsToCsv<T extends Record<string, unknown>>(
  data: T[],
  columns?: { key: string; label: string }[]
): string {
  if (data.length === 0) return '';

  // Auto-detect columns if not provided
  const cols = columns ?? Object.keys(data[0]).map(key => ({ key, label: key }));

  // Header row
  const header = cols.map(c => escapeCsvField(c.label)).join(',');

  // Data rows
  const rows = data.map(row =>
    cols.map(c => escapeCsvField(String(row[c.key] ?? ''))).join(',')
  );

  return [header, ...rows].join('\n');
}

/** Escape a CSV field (quote if contains comma, quote, or newline) */
function escapeCsvField(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

/** Trigger browser download of CSV content */
export function downloadCsv(filename: string, csvContent: string): void {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename.endsWith('.csv') ? filename : `${filename}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

/** Export data as CSV download */
export function exportToCsv<T extends Record<string, unknown>>(
  filename: string,
  data: T[],
  columns?: { key: string; label: string }[]
): void {
  const csv = objectsToCsv(data, columns);
  downloadCsv(filename, csv);
}
