import { StatusBadge } from "./status";

export function formatRisk(riskRaw: string): StatusBadge {
  if (!riskRaw) return { text: "Unknown", variant: "secondary" };
  
  const normalized = riskRaw.toUpperCase();
  switch (normalized) {
    case "HIGH": return { text: "High Risk", variant: "destructive" };
    case "MEDIUM": return { text: "Medium Risk", variant: "warning" };
    case "LOW": return { text: "Low Risk", variant: "success" };
    default: return { text: riskRaw, variant: "secondary" };
  }
}
