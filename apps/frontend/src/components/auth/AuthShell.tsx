"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { BreadcrumbItem, Breadcrumbs } from "@/components/ui/Breadcrumbs";

interface AuthShellProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  className?: string;
}

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
  breadcrumbs,
  className,
}: AuthShellProps) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-primary-500/15 via-white to-info-50/60">
      <div className="absolute inset-0 -z-10 opacity-40">
        <div className="absolute left-1/3 top-10 h-56 w-56 rounded-full bg-primary-200/70 blur-3xl" />
        <div className="absolute right-16 bottom-16 h-64 w-64 rounded-full bg-info-200/70 blur-3xl" />
        <div className="absolute left-10 bottom-10 h-36 w-36 rounded-full bg-warning-100/80 blur-2xl" />
      </div>

      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col justify-center px-4 py-8 sm:px-6 lg:flex-row lg:items-center lg:gap-20 lg:px-8">
        <aside className="hidden max-w-lg flex-1 flex-col gap-8 lg:flex">
          <Link href="/" className="flex items-center gap-3 text-[var(--primary-600)]">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary-100 text-primary-600 shadow-soft">
              <span className="text-lg font-semibold">CC</span>
            </div>
            <div className="flex flex-col">
              <span className="text-base font-semibold tracking-tight text-[var(--text-primary)]">
                Carpeta Ciudadana
              </span>
            </div>
          </Link>

          <div className="rounded-[var(--radius-lg)] border border-primary-100 bg-white/85 p-10 shadow-soft backdrop-blur">
            <h2 className="text-3xl font-semibold text-[var(--text-primary)]">
              Conecta con tus documentos digitales
            </h2>
            <p className="mt-4 text-base text-[var(--text-secondary)] leading-relaxed">
              Accede a tu carpeta ciudadana para gestionar, firmar y compartir documentos oficiales con total seguridad.
            </p>
            <div className="mt-8 grid grid-cols-2 gap-4 text-sm text-[var(--text-secondary)]">
              <div className="rounded-xl border border-primary-50 bg-primary-25/60 p-4">
                <span className="text-lg font-semibold text-primary-600">
                  24/7
                </span>
                <p className="mt-1 text-xs text-[var(--text-tertiary)]">
                  Disponible en todo momento
                </p>
              </div>
              <div className="rounded-xl border border-success-50 bg-success-50 p-4">
                <span className="text-lg font-semibold text-success-600">
                  Firma digital
                </span>
                <p className="mt-1 text-xs text-[var(--text-tertiary)]">
                  Respaldo jurídico garantizado
                </p>
              </div>
            </div>
          </div>
        </aside>

        <main
          className={cn(
            "relative flex w-full max-w-md flex-col gap-8 rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-white/90 px-6 py-8 shadow-soft backdrop-blur-sm sm:px-8",
            className
          )}
        >
          <div className="flex flex-col gap-4">
            {breadcrumbs?.length ? <Breadcrumbs items={breadcrumbs} /> : null}
            <h1 className="text-2xl font-semibold text-[var(--text-primary)] sm:text-3xl">
              {title}
            </h1>
            {subtitle ? (
              <p className="mt-2 text-sm text-[var(--text-secondary)]">{subtitle}</p>
            ) : null}
          </div>

          <div className="flex-1">{children}</div>

          {footer ? <div className="pt-2 text-sm text-[var(--text-secondary)]">{footer}</div> : null}
        </main>
      </div>
    </div>
  );
}

