'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Button, ButtonProps } from './Button';
import { BreadcrumbItem, Breadcrumbs } from './Breadcrumbs';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  className?: string;
}

export function PageHeader({
  title,
  description,
  actions,
  breadcrumbs,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn('space-y-4', className)}>
      {breadcrumbs?.length ? <Breadcrumbs items={breadcrumbs} /> : null}
      <div className="rounded-[var(--radius-lg)] border border-[var(--primary-100)] bg-gradient-to-r from-[var(--primary-25)] via-white to-[var(--primary-25)] p-6 shadow-soft">
        <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-col gap-2">
            <h1 className="text-3xl font-semibold text-[var(--text-primary)]">{title}</h1>
            {description ? (
              <p className="max-w-2xl text-base text-[var(--text-secondary)]">
                {description}
              </p>
            ) : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
        </div>
      </div>
    </div>
  );
}

export interface HeaderAction {
  label: string;
  icon?: ReactNode;
  props?: ButtonProps;
}

export function HeaderActions({ actions }: { actions: HeaderAction[] }) {
  if (!actions?.length) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      {actions.map(({ label, icon, props }) => (
        <Button key={label} icon={icon} {...props}>
          {label}
        </Button>
      ))}
    </div>
  );
}

