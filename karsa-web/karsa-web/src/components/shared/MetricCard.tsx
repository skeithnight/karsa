import React from "react";

interface MetricCardProps {
  title: string;
  metric: string;
  subtext?: string;
  statusIndicator?: "positive" | "negative" | "neutral";
}

export function MetricCard({ title, metric, subtext, statusIndicator = "neutral" }: MetricCardProps) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="text-sm font-medium text-muted-foreground">{title}</div>
      <div className="text-2xl font-bold mt-1">{metric}</div>
      {subtext && (
        <p className="text-xs text-muted-foreground mt-1">{subtext}</p>
      )}
    </div>
  );
}
