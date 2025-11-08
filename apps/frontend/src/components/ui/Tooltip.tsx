'use client';

import { ReactNode, useId } from "react";

import { cn } from "@/lib/utils";

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Tooltip({ content, children, className }: TooltipProps) {
  const tooltipId = useId();

  return (
    <div className={cn("group relative inline-flex", className)}>
      {children}
      <span
        role="tooltip"
        id={tooltipId}
        className="pointer-events-none absolute bottom-full left-1/2 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-md bg-white px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] opacity-0 shadow-lg shadow-primary-900/15 ring-1 ring-[var(--primary-100)] transition-all duration-150 group-hover:block group-hover:opacity-100"
      >
        {content}
        <span className="absolute left-1/2 top-full h-2 w-2 -translate-x-1/2 rotate-45 bg-white ring-1 ring-[var(--primary-100)]" />
      </span>
    </div>
  );
}
