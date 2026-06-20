import React from "react";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({ message = "Something went wrong.", onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <p className="text-sm text-muted-foreground mb-4">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded">
          Retry
        </button>
      )}
    </div>
  );
}
