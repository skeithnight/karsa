export function buildQueryString(params: Record<string, any>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      if (typeof value === 'object') {
        // Flat nesting for simple DTOs (e.g. pagination.page -> page)
        for (const [subKey, subValue] of Object.entries(value)) {
           if (subValue !== undefined && subValue !== null) {
              query.append(subKey, String(subValue));
           }
        }
      } else {
        query.append(key, String(value));
      }
    }
  }
  const str = query.toString();
  return str ? `?${str}` : '';
}
