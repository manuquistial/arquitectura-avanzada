import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface StatTileProps {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  tone?: 'primary' | 'success' | 'warning' | 'info';
  className?: string;
  helperText?: string;
}

const toneStyles: Record<
  NonNullable<StatTileProps['tone']>,
  { icon: string; badge: string; card: string }
> = {
  primary: {
    icon: 'bg-primary-100 text-primary-600',
    badge: 'text-primary-600',
    card: 'border border-[var(--primary-100)] bg-[var(--primary-25)]',
  },
  success: {
    icon: 'bg-success-100 text-success-600',
    badge: 'text-success-600',
    card: 'border border-success-100 bg-[var(--success-50)]',
  },
  warning: {
    icon: 'bg-warning-100 text-warning-600',
    badge: 'text-warning-600',
    card: 'border border-warning-100 bg-[var(--accent-50)]',
  },
  info: {
    icon: 'bg-info-100 text-info-600',
    badge: 'text-info-600',
    card: 'border border-info-100 bg-[var(--info-50)]',
  },
};

export function StatTile({
  label,
  value,
  icon,
  tone = 'primary',
  className,
  helperText,
}: StatTileProps) {
  const toneStyle = toneStyles[tone] ?? toneStyles.primary;

  return (
    <div
      className={cn(
        'flex flex-col gap-4 rounded-[var(--radius-lg)] p-6 shadow-soft shadow-primary-900/5',
        toneStyle.card,
        className
      )}
    >
      <div className="flex items-center gap-3">
        {icon ? (
          <div
            className={cn(
              'flex h-12 w-12 items-center justify-center rounded-xl',
              toneStyle.icon
            )}
          >
            {icon}
          </div>
        ) : null}
        <div className="flex flex-col">
          <span className="text-sm font-medium text-[var(--text-tertiary)] uppercase tracking-wide">
            {label}
          </span>
          <span className="text-2xl font-semibold text-[var(--text-primary)]">
            {value}
          </span>
        </div>
      </div>
      {helperText ? (
        <span className={cn('text-xs', toneStyle.badge)}>{helperText}</span>
      ) : null}
    </div>
  );
}

