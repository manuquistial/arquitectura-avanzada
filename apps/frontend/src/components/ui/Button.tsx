"use client";

import Link from 'next/link';
import { forwardRef, ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'outline' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg' | 'icon';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
  iconPosition?: 'left' | 'right';
  isLoading?: boolean;
  href?: string;
}

const baseStyles =
  'inline-flex items-center justify-center gap-2 rounded-[var(--radius-sm)] font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed';

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-[var(--primary-400)] text-white shadow-[0_10px_25px_-12px_rgba(11,76,140,0.45)] hover:bg-[var(--primary-500)] active:bg-[var(--primary-300)] focus-visible:ring-[var(--primary-200)] focus-visible:ring-offset-2 focus-visible:ring-offset-white [&>span]:text-white',
  secondary:
    'bg-white text-[var(--primary-700)] border border-[var(--primary-200)] shadow-[0_8px_18px_-12px_rgba(11,76,140,0.35)] hover:bg-[var(--primary-50)] hover:text-[var(--primary-700)] focus-visible:ring-[var(--primary-300)] focus-visible:ring-offset-0 active:bg-[var(--primary-100)] active:text-[var(--primary-800)]',
  ghost:
    'bg-transparent text-[var(--primary-600)] hover:text-[var(--primary-700)] hover:bg-[var(--primary-25)] focus-visible:ring-[var(--primary-100)] focus-visible:ring-offset-0 active:bg-[var(--primary-50)] active:text-[var(--primary-800)]',
  outline:
    'bg-transparent text-[var(--primary-700)] border border-[var(--primary-300)] hover:bg-[var(--primary-50)] hover:text-[var(--primary-800)] focus-visible:ring-[var(--primary-200)] focus-visible:ring-offset-0 active:bg-[var(--primary-100)] active:text-[var(--primary-900)]',
  danger:
    'bg-[var(--danger-400)] text-white shadow-[0_10px_25px_-12px_rgba(224,34,58,0.4)] hover:bg-[var(--danger-500)] active:bg-[var(--danger-300)] focus-visible:ring-[var(--danger-200)] focus-visible:ring-offset-2 focus-visible:ring-offset-white [&>span]:text-white',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'h-9 px-3 text-sm',
  md: 'h-11 px-5 text-sm',
  lg: 'h-12 px-6 text-base',
  icon: 'h-10 w-10 p-0',
};

const spinner =
  'h-4 w-4 animate-spin rounded-full border-[3px] border-white/60 border-t-white';

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      icon,
      iconPosition = 'left',
      children,
      isLoading,
      disabled,
      href,
      ...props
    },
    ref
  ) => {
    const isIconRight = icon && iconPosition === 'right';
    const showSpinner = isLoading;

    const content = (
      <>
        {showSpinner ? (
          <span
            className={cn(
              spinner,
              variant === 'secondary' || variant === 'ghost'
                ? 'border-[var(--primary-500)]/40 border-t-[var(--primary-500)]'
                : variant === 'outline'
                  ? 'border-[var(--primary-500)]/60 border-t-[var(--primary-500)]'
                  : variant === 'danger'
                    ? 'border-[var(--danger-400)]/50 border-t-[var(--danger-200)]'
                    : ''
            )}
          />
        ) : (
          icon && iconPosition === 'left' && (
            <span className="inline-flex items-center text-inherit">{icon}</span>
          )
        )}
        <span className="truncate">{children}</span>
        {!showSpinner && isIconRight && (
          <span className="inline-flex items-center text-inherit">{icon}</span>
        )}
      </>
    );

    if (href) {
      return (
        <Link
          href={href}
          className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
        >
          {content}
        </Link>
      );
    }

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {content}
      </button>
    );
  }
);

Button.displayName = 'Button';

