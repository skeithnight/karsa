import { StatusBadge } from "./status";

export function formatPerformanceState(stateRaw: string): StatusBadge {
  if (!stateRaw) return { text: "Unknown", variant: "secondary" };
  
  const normalized = stateRaw.toUpperCase();
  switch (normalized) {
    case "OUTPERFORM": return { text: "Outperform", variant: "success" };
    case "UNDERPERFORM": return { text: "Underperform", variant: "destructive" };
    case "NEUTRAL": return { text: "Neutral", variant: "secondary" };
    default: return { text: stateRaw, variant: "secondary" };
  }
}
