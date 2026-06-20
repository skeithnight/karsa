import React from "react";

export function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      <div className="h-4 bg-muted rounded w-3/4 animate-pulse" />
      <div className="h-4 bg-muted rounded w-1/2 animate-pulse" />
      <div className="h-4 bg-muted rounded w-5/6 animate-pulse" />
    </div>
  );
}
