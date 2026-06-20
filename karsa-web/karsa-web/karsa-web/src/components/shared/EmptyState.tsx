import React from "react";

interface EmptyStateProps {
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({ message = "No data available.", actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <p className="text-sm text-muted-foreground mb-4">{message}</p>
      {actionLabel && onAction && (
        <button onClick={onAction} className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded">
          {actionLabel}
        </button>
      )}
    </div>
  );
}
