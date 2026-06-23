export function formatCurrency(valueRaw: number, currency: string = "IDR"): string {
  if (valueRaw === null || valueRaw === undefined) return "N/A";

  // IDR formatting: id-ID locale, dot thousand separator, no decimals for whole values
  if (currency === "IDR") {
    const absValue = Math.abs(valueRaw);
    const sign = valueRaw < 0 ? "-" : "";

    if (absValue >= 1e12) {
      return `${sign}Rp ${new Intl.NumberFormat('id-ID', { maximumFractionDigits: 1 }).format(absValue / 1e12)}T`;
    }
    if (absValue >= 1e9) {
      return `${sign}Rp ${new Intl.NumberFormat('id-ID', { maximumFractionDigits: 1 }).format(absValue / 1e9)}M`;
    }
    if (absValue >= 1e6) {
      return `${sign}Rp ${new Intl.NumberFormat('id-ID', { maximumFractionDigits: 1 }).format(absValue / 1e6)}jt`;
    }
    return `${sign}${new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(absValue)}`;
  }

  // USD and other currencies: en-US locale
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
