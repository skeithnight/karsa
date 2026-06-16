import React from "react";
import { AlertCircle } from "lucide-react";

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center" data-testid="empty-state">
      <div className="mb-4 text-muted-foreground">
        {icon || <AlertCircle className="w-12 h-12" />}
      </div>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground mt-2 max-w-sm">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
