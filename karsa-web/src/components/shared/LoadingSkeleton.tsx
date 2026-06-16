import React from "react";
import { Skeleton } from "../ui/skeleton";

export interface LoadingSkeletonProps {
  variant: "card" | "table" | "page";
}

export function LoadingSkeleton({ variant }: LoadingSkeletonProps) {
  if (variant === "card") {
    return (
      <div className="p-4 border rounded-xl space-y-3" data-testid="loading-skeleton">
        <Skeleton className="h-4 w-[100px]" />
        <Skeleton className="h-8 w-[200px]" />
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div className="space-y-4" data-testid="loading-skeleton">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6" data-testid="loading-skeleton">
      <Skeleton className="h-12 w-1/3" />
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
