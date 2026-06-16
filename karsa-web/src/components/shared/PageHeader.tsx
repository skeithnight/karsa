import React from "react";

export interface PageHeaderProps {
  title: string;
  description?: string;
  breadcrumbs?: string[];
  actionSlot?: React.ReactNode;
}

export function PageHeader({ title, description, breadcrumbs, actionSlot }: PageHeaderProps) {
  return (
    <div className="flex justify-between items-center pb-4 border-b mb-6">
      <div>
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="text-xs text-muted-foreground mb-1">
            {breadcrumbs.join(" / ")}
          </nav>
        )}
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {actionSlot && <div>{actionSlot}</div>}
    </div>
  );
}
