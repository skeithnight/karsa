export function formatCurrency(valueRaw: number, currency: string = "USD"): string {
  if (valueRaw === null || valueRaw === undefined) return "N/A";
  
  if (valueRaw >= 1e9) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 1 }).format(valueRaw / 1e9) + 'B';
  }
  if (valueRaw >= 1e6) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 1 }).format(valueRaw / 1e6) + 'M';
  }
  if (valueRaw >= 1e3) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 1 }).format(valueRaw / 1e3) + 'K';
  }
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(valueRaw);
}
