import React from "react";
import { Button } from "../ui/button";

export interface ErrorStateProps {
  errorMessage: string;
  onRetry?: () => void;
  fallbackDisplay?: React.ReactNode;
}

export function ErrorState({ errorMessage, onRetry, fallbackDisplay }: ErrorStateProps) {
  if (fallbackDisplay) {
    return <div data-testid="error-state-fallback">{fallbackDisplay}</div>;
  }

  return (
    <div 
      className="flex flex-col items-center justify-center p-8 border border-red-200 bg-red-50 text-red-800 rounded-md" 
      data-testid="error-state"
      role="alert"
      aria-live="assertive"
    >
      <h3 className="text-lg font-semibold mb-2">An error occurred</h3>
      <p className="text-sm mb-4">{errorMessage}</p>
      {onRetry && (
        <Button
          onClick={onRetry}
          variant="destructive"
          data-testid="error-retry-button"
        >
          Retry
        </Button>
      )}
    </div>
  );
}
