export function formatDate(isoStringRaw: string, style: "short" | "long" = "short"): string {
  if (!isoStringRaw) return "N/A";
  const date = new Date(isoStringRaw);
  if (isNaN(date.getTime())) return "Invalid Date";
  
  if (style === "short") {
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }
  return date.toLocaleString("en-US", { month: "long", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
