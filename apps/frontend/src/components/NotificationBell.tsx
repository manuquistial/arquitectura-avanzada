"use client";

import { ReactNode, useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useSession } from 'next-auth/react';
import {
  Bell,
  BellDot,
  FileSignature,
  FileText,
  Inbox,
  Loader2,
  Send,
} from 'lucide-react';

import { apiService } from '@/lib/api';

interface Notification {
  id: string;
  title: string;
  message: string;
  type: string;
  read: boolean;
  created_at: string;
}

const ICONS: Record<string, ReactNode> = {
  document_signed: <FileSignature className="h-4 w-4" />,
  document_uploaded: <FileText className="h-4 w-4" />,
  transfer_received: <Inbox className="h-4 w-4" />,
  transfer_sent: <Send className="h-4 w-4" />,
};

function getIcon(type: string) {
  return ICONS[type] ?? <Bell className="h-4 w-4" />;
}

export default function NotificationBell() {
  const { data: session } = useSession();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const loadNotifications = useCallback(async () => {
    if (!session?.user?.id) return;
    try {
      setLoading(true);
      const citizenId = session.user.id;
      const data = await apiService.getUserNotifications(citizenId);
      const items = Array.isArray(data) ? data : [];
      const ordered = items
        .sort(
          (a: Notification, b: Notification) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
        .slice(0, 5);
      setNotifications(ordered);
      setUnreadCount(items.filter((n: Notification) => !n.read).length);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    } finally {
      setLoading(false);
    }
  }, [session?.user?.id]);

  useEffect(() => {
    if (!session?.user?.id) return;
    loadNotifications();
    const interval = setInterval(loadNotifications, 30000);
    return () => clearInterval(interval);
  }, [loadNotifications, session?.user?.id]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        event.target instanceof Node &&
        !dropdownRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const formatDate = (value: string) => {
    const date = new Date(value);
    return date.toLocaleString('es-CO', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (!session?.user?.id) {
    return null;
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => {
          const next = !isOpen;
          setIsOpen(next);
          if (next) {
            void loadNotifications();
          }
        }}
        className="relative flex h-11 w-11 items-center justify-center rounded-full border border-[var(--border-subtle)] bg-white text-[var(--text-tertiary)] transition-colors hover:text-primary-600"
        aria-haspopup="true"
        aria-expanded={isOpen}
        aria-label="Notificaciones"
      >
        {unreadCount > 0 ? (
          <BellDot className="h-5 w-5" />
        ) : (
          <Bell className="h-5 w-5" />
        )}
        {unreadCount > 0 ? (
          <span className="absolute -top-1 -right-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-danger-500 px-1 text-xs font-semibold text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div className="absolute right-0 z-40 mt-3 w-80 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-white shadow-soft">
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3">
            <p className="text-sm font-semibold text-[var(--text-primary)]">
              Notificaciones
            </p>
            {unreadCount > 0 ? (
              <span className="text-xs font-medium text-primary-600">
                {unreadCount} sin leer
              </span>
            ) : null}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {loading ? (
              <div className="flex flex-col items-center gap-2 px-6 py-10 text-[var(--text-secondary)]">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-sm">Buscando novedades…</span>
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center gap-3 px-6 py-12 text-center text-[var(--text-secondary)]">
                <Bell className="h-6 w-6 text-[var(--text-tertiary)]" />
                <p className="text-sm font-medium">
                  No tienes notificaciones pendientes
                </p>
                <p className="text-xs text-[var(--text-tertiary)]">
                  Te avisaremos cuando se firmen o transfieran documentos.
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-[var(--border-subtle)]">
                {notifications.map((notification) => (
                  <li key={notification.id}>
                    <Link
                      href="/notifications"
                      onClick={() => setIsOpen(false)}
                      className="flex gap-3 px-4 py-3 transition-colors hover:bg-primary-25"
                    >
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-25 text-primary-600">
                        {getIcon(notification.type)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-[var(--text-primary)] line-clamp-1">
                          {notification.title}
                        </p>
                        <p className="text-xs text-[var(--text-secondary)] line-clamp-2">
                          {notification.message}
                        </p>
                        <p className="mt-1 text-xs text-[var(--text-tertiary)]">
                          {formatDate(notification.created_at)}
                        </p>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="border-t border-[var(--border-subtle)] bg-[var(--surface-muted)] px-4 py-3">
            <Link
              href="/notifications"
              onClick={() => setIsOpen(false)}
              className="block text-center text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              Ver todas las notificaciones
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}