export interface StatusBadge {
  text: string;
  variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning";
}

export function formatStatus(statusRaw: string): StatusBadge {
  if (!statusRaw) return { text: "Unknown", variant: "secondary" };
  
  const normalized = statusRaw.toUpperCase();
  switch (normalized) {
    case "ACTIVE": return { text: "Active", variant: "default" };
    case "INVALIDATED": return { text: "Invalidated", variant: "destructive" };
    case "INITIATED": return { text: "Initiated", variant: "outline" };
    case "COMPLETED": return { text: "Completed", variant: "success" };
    case "PENDING": return { text: "Pending", variant: "warning" };
    case "FAILED": return { text: "Failed", variant: "destructive" };
    default: return { text: statusRaw, variant: "secondary" };
  }
}

export function formatConviction(convictionRaw: string): StatusBadge {
  if (!convictionRaw) return { text: "Unknown", variant: "secondary" };
  
  const normalized = convictionRaw.toUpperCase();
  switch (normalized) {
    case "HIGH": return { text: "High", variant: "success" };
    case "MEDIUM": return { text: "Medium", variant: "warning" };
    case "LOW": return { text: "Low", variant: "secondary" };
    default: return { text: convictionRaw, variant: "secondary" };
  }
}
