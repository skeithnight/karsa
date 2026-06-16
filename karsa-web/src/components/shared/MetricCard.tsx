import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";

export interface MetricCardProps {
  title: string;
  metric: string;
  subtext?: string;
  delta?: number;
  statusIndicator?: "positive" | "negative" | "neutral";
}

export function MetricCard({ title, metric, subtext, delta, statusIndicator = "neutral" }: MetricCardProps) {
  return (
    <Card data-testid="metric-card">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{metric}</div>
        {(subtext || delta !== undefined) && (
          <p className="text-xs text-muted-foreground flex items-center mt-1">
            {statusIndicator === "positive" && <ArrowUp className="w-3 h-3 text-green-500 mr-1" />}
            {statusIndicator === "negative" && <ArrowDown className="w-3 h-3 text-red-500 mr-1" />}
            {statusIndicator === "neutral" && <Minus className="w-3 h-3 text-gray-500 mr-1" />}
            {delta !== undefined && <span className="mr-1">{delta}%</span>}
            {subtext}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
