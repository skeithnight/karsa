export function formatPercentage(valueRaw: number, decimals: number = 2): string {
  if (valueRaw === null || valueRaw === undefined) return "N/A";
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(valueRaw);
}
