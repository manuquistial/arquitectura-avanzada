"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useSession, signOut } from 'next-auth/react';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Bell,
  ChevronDown,
  FileText,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  Shuffle,
  User,
  Users,
} from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import NotificationBell from './NotificationBell';

type NavigationItem = {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: string[];
};

const NAV_ITEMS: NavigationItem[] = [
  { name: 'Panel', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Documentos', href: '/documents', icon: FileText },
  { name: 'Transferencias', href: '/transfers', icon: Shuffle },
];

const ADMIN_ITEMS: NavigationItem[] = [
  { name: 'Administración', href: '/admin', icon: ShieldCheck, roles: ['admin', 'mintic'] },
];

function allowItem(item: NavigationItem, userRoles?: string[]) {
  if (!item.roles?.length) return true;
  return item.roles.some((role) => userRoles?.includes(role));
}

export default function Navigation() {
  const { data: session, status } = useSession();
  const pathname = usePathname();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement | null>(null);

  const userRoles = session?.user?.roles ?? [];

  useEffect(() => {
    if (!userMenuOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        userMenuRef.current &&
        event.target instanceof Node &&
        !userMenuRef.current.contains(event.target)
      ) {
        setUserMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [userMenuOpen]);

  const primaryLinks = useMemo(
    () => NAV_ITEMS.filter((item) => allowItem(item, userRoles)),
    [userRoles]
  );

  const adminLinks = useMemo(
    () => ADMIN_ITEMS.filter((item) => allowItem(item, userRoles)),
    [userRoles]
  );

  if (pathname === '/login' || pathname === '/' || status === 'loading') {
    return null;
  }

  if (status === 'unauthenticated') {
    return null;
  }

  const isActive = (href: string) =>
    pathname === href || pathname?.startsWith(`${href}/`);

  const initials =
    session?.user?.name
      ?.split(' ')
      .map((part) => part[0])
      .join('')
      .slice(0, 2)
      .toUpperCase() || session?.user?.email?.[0]?.toUpperCase() || 'CC';

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--primary-100)] bg-gradient-to-r from-white/95 via-white/95 to-[var(--primary-25)]/80 shadow-sm backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-8">
          <Link href="/dashboard" className="flex items-center gap-3 text-[var(--primary-600)] transition-colors hover:text-[var(--primary-500)]">
            <div className="flex flex-col">
              <span className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">
                Carpeta Ciudadana
              </span>
            </div>
          </Link>

          <nav className="hidden items-center gap-1 lg:flex">
            {primaryLinks.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'group inline-flex items-center gap-2 rounded-lg px-4 py-2 text-[0.95rem] font-semibold transition-all',
                    active
                      ? 'bg-[var(--primary-50)] text-[var(--primary-700)] shadow-sm border border-[var(--primary-200)]'
                      : 'text-[var(--text-tertiary)] hover:bg-[var(--primary-25)] hover:text-[var(--primary-600)]'
                  )}
                >
                  <Icon
                    className={cn(
                      'h-4.5 w-4.5 transition-colors',
                      active ? 'text-[var(--primary-500)]' : 'text-slate-400 group-hover:text-[var(--primary-500)]'
                    )}
                  />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden items-center gap-3 md:flex">
            <NotificationBell />
          </div>

          <div className="relative hidden items-center md:flex" ref={userMenuRef}>
            <button
              type="button"
              onClick={() => setUserMenuOpen((open) => !open)}
              className="inline-flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--primary-100)] bg-white/80 px-3 py-2 text-sm font-medium text-[var(--text-primary)] transition-colors hover:border-[var(--primary-200)] hover:shadow-sm"
              aria-haspopup="menu"
              aria-expanded={userMenuOpen}
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-500 text-sm font-semibold text-white">
                {initials}
              </span>
              <span className="flex flex-col items-start">
                <span>{session?.user?.name ?? 'Usuario'}</span>
                <span className="text-xs text-[var(--text-tertiary)]">{session?.user?.email}</span>
              </span>
              <ChevronDown className={cn('h-4 w-4 transition-transform', userMenuOpen && 'rotate-180')} />
            </button>

            {userMenuOpen ? (
              <div className="absolute right-0 top-full mt-2 w-60 rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-white shadow-soft">
                <div className="px-4 py-3">
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    {session?.user?.name ?? 'Usuario'}
                  </p>
                  <p className="text-xs text-[var(--text-tertiary)]">{session?.user?.email}</p>
                </div>
                <div className="border-t border-[var(--border-subtle)] px-2 py-2 text-sm">
                  <Link
                    href="/account"
                    className="flex items-center gap-2 rounded-md px-3 py-2 text-[var(--text-secondary)] transition-colors hover:bg-primary-25"
                    onClick={() => setUserMenuOpen(false)}
                  >
                    <User className="h-4 w-4 text-primary-500" />
                    Mi cuenta
                  </Link>
                  {adminLinks.length > 0 ? (
                    <div className="mt-2 space-y-1">
                      <p className="px-3 text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
                        Administración
                      </p>
                      {adminLinks.map((item) => (
                <Link
                          key={`admin-${item.href}`}
                  href={item.href}
                          className="flex items-center gap-2 rounded-md px-3 py-2 text-[var(--text-secondary)] transition-colors hover:bg-primary-25"
                          onClick={() => setUserMenuOpen(false)}
                        >
                          <item.icon className="h-4 w-4 text-primary-500" />
                  {item.name}
                </Link>
              ))}
            </div>
                  ) : null}
                </div>
                <div className="border-t border-[var(--border-subtle)] px-2 py-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-start text-danger-500 hover:bg-danger-100/60"
                    icon={<LogOut className="h-4 w-4" />}
                    onClick={() => {
                      setUserMenuOpen(false);
                      signOut({ callbackUrl: '/login' });
                    }}
                  >
                    Cerrar sesión
                  </Button>
                </div>
              </div>
            ) : null}
          </div>

        </div>
      </div>
    </header>
  );
}

