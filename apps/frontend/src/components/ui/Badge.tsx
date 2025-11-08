'use client';

import { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

type BadgeVariant =
  | 'default'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'secondary';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-primary-200 text-primary-800 border border-primary-300',
  success: 'bg-success-200 text-success-700 border border-success-300',
  warning: 'bg-warning-200 text-[var(--accent-600)] border border-warning-300',
  danger: 'bg-danger-200 text-danger-700 border border-danger-300',
  info: 'bg-info-200 text-info-700 border border-info-300',
  secondary: 'bg-[var(--surface-muted)] text-[var(--text-secondary)] border border-[var(--border-subtle)]',
};

const toneRing: Record<BadgeVariant, string> = {
  default: 'shadow-[0_0_12px_rgba(11,76,140,0.16)]',
  success: 'shadow-[0_0_12px_rgba(30,158,116,0.16)]',
  warning: 'shadow-[0_0_12px_rgba(243,156,18,0.18)]',
  danger: 'shadow-[0_0_12px_rgba(224,34,58,0.2)]',
  info: 'shadow-[0_0_12px_rgba(47,124,246,0.2)]',
  secondary: 'shadow-[0_0_10px_rgba(91,106,119,0.08)]',
};

export function Badge({
  className,
  variant = 'default',
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium shadow-sm',
        variantStyles[variant],
        toneRing[variant],
        className
      )}
      {...props}
    />
  );
}

