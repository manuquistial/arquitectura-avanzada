"use client";

import { useEffect, useMemo, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import {
  Bell,
  FileText,
  PenSquare,
  Share2,
  Upload,
  Inbox,
} from 'lucide-react';

import { apiService } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';
import { Button } from '@/components/ui/Button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/Card';
import { StatTile } from '@/components/ui/StatTile';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

interface Notification {
  id: string;
  citizen_id: string;
  type: string;
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  metadata?: any;
}

export default function NotificationsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'unread' | 'read'>('all');
  const [stats, setStats] = useState({ total_notifications: 0 });

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    if (session?.user?.id) {
      fetchData();
    }
  }, [session, filter]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const citizenId = session?.user?.id || '1234567890';
      
      // Fetch notifications and stats
      const [notifData, statsData] = await Promise.all([
        apiService.getUserNotifications(citizenId),
        apiService.getNotificationStats()
      ]);
      
      // Filter notifications
      let filtered = Array.isArray(notifData) ? notifData : [];
      if (filter === 'unread') {
        filtered = filtered.filter((n: Notification) => !n.read);
      } else if (filter === 'read') {
        filtered = filtered.filter((n: Notification) => n.read);
      }
      
      // Sort by created_at (most recent first)
      filtered.sort((a: Notification, b: Notification) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      
      setNotifications(filtered);
      setStats(statsData || { total_notifications: 0 });
    } catch (error) {
      console.error('Error fetching notifications:', error);
      setError('Error al cargar las notificaciones');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const unreadCount = notifications.filter((n) => !n.read).length;
  const readCount = notifications.length - unreadCount;

  const statsTiles = useMemo(
    () => [
      {
        label: 'Notificaciones recibidas',
        value: stats.total_notifications || notifications.length,
        icon: <Bell className="h-5 w-5" />,
        tone: 'primary' as const,
        helperText: 'Histórico total',
      },
      {
        label: 'Sin leer',
        value: unreadCount,
        icon: <Inbox className="h-5 w-5" />,
        tone: 'warning' as const,
        helperText: unreadCount > 0 ? 'Atención requerida' : 'Todo al día',
      },
      {
        label: 'Leídas',
        value: readCount,
        icon: <FileText className="h-5 w-5" />,
        tone: 'success' as const,
        helperText: 'Revisadas recientemente',
      },
    ],
    [notifications.length, readCount, stats.total_notifications, unreadCount]
  );

  const notificationMeta = {
    document_signed: {
      icon: <PenSquare className="h-5 w-5 text-success-600" />,
      badge: 'Documento firmado',
      tone: 'success' as const,
    },
    document_uploaded: {
      icon: <Upload className="h-5 w-5 text-primary-600" />,
      badge: 'Documento subido',
      tone: 'info' as const,
    },
    transfer_received: {
      icon: <Share2 className="h-5 w-5 text-primary-600" />,
      badge: 'Transferencia recibida',
      tone: 'info' as const,
    },
    transfer_sent: {
      icon: <Share2 className="h-5 w-5 text-primary-600" />,
      badge: 'Transferencia enviada',
      tone: 'info' as const,
    },
    document_shared: {
      icon: <Share2 className="h-5 w-5 text-primary-600" />,
      badge: 'Documento compartido',
      tone: 'info' as const,
    },
    default: {
      icon: <Bell className="h-5 w-5 text-primary-600" />,
      badge: 'Notificación',
      tone: 'info' as const,
    },
  };

  const filters: Array<{ value: 'all' | 'unread' | 'read'; label: string; count: number }> = [
    { value: 'all', label: 'Todas', count: notifications.length },
    { value: 'unread', label: 'Sin leer', count: unreadCount },
    { value: 'read', label: 'Leídas', count: readCount },
  ];

  return (
    <>
      <PageHeader
        breadcrumbs={[
          { label: 'Inicio', href: '/dashboard' },
          { label: 'Notificaciones' },
        ]}
        title="Notificaciones"
        description="Mantente al día con las alertas y novedades de tu Carpeta Ciudadana."
        actions={[
          <Button
            key="refresh"
            variant="ghost"
            onClick={fetchData}
          >
            Actualizar
          </Button>,
        ]}
      />

      {loading ? (
        <div className="flex min-h-[60vh] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="h-12 w-12 animate-spin rounded-full border-2 border-primary-100 border-t-primary-500" />
            <p className="text-sm text-[var(--text-tertiary)]">Cargando notificaciones…</p>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {error ? (
            <Card className="border-danger-100 bg-danger-50/80">
              <CardHeader>
                <CardTitle className="text-danger-600">Se produjo un error</CardTitle>
                <CardDescription className="text-danger-500">{error}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="ghost" onClick={fetchData}>Intentar de nuevo</Button>
              </CardContent>
            </Card>
          ) : null}

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            {statsTiles.map((tile) => (
              <StatTile key={tile.label} {...tile} />
            ))}
          </div>

          <Card className="border-[var(--primary-100)] bg-white/90">
            <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <CardTitle>Historial de notificaciones</CardTitle>
                <CardDescription>Filtra las alertas por estado y revisa su contenido.</CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                {filters.map((item) => (
                  <Button
                    key={item.value}
                    variant={filter === item.value ? 'primary' : 'secondary'}
                    size="sm"
                    onClick={() => setFilter(item.value)}
                  >
                    {item.label} ({item.count})
                  </Button>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              {notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center gap-3 rounded-[var(--radius-md)] border border-dashed border-info-100 bg-[var(--info-50)]/70 p-12 text-center">
                  <Bell className="h-8 w-8 text-info-500" />
                  <p className="text-sm font-medium text-[var(--text-primary)]">No hay notificaciones en este momento.</p>
                  <p className="text-xs text-[var(--text-secondary)]">Cuando tengas novedades aparecerán en este listado.</p>
                </div>
              ) : (
                <ul className="space-y-4">
                  {notifications.map((notification) => {
                    const meta = notificationMeta[notification.type as keyof typeof notificationMeta] ?? notificationMeta.default;
                    return (
                      <li
                        key={notification.id}
                        className={cn(
                          'flex items-start gap-4 rounded-[var(--radius-md)] border p-4 shadow-sm transition-colors backdrop-blur',
                          notification.read
                            ? 'border-[var(--border-subtle)] bg-white/70'
                            : 'border-info-200 bg-[var(--info-50)]'
                        )}
                      >
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-white shadow-sm">
                          {meta.icon}
                        </div>
                        <div className="flex-1 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="text-sm font-semibold text-[var(--text-primary)]">{notification.title}</p>
                            <Badge variant={meta.tone}>{meta.badge}</Badge>
                            {!notification.read ? (
                              <Badge variant="info">Nuevo</Badge>
                            ) : null}
                          </div>
                          <p className="text-sm text-[var(--text-secondary)]">{notification.message}</p>
                          <div className="flex flex-wrap items-center justify-between text-xs text-[var(--text-tertiary)]">
                            <span>{formatDate(notification.created_at)}</span>
                            {!notification.read ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setNotifications((prev) =>
                                    prev.map((n) =>
                                      n.id === notification.id ? { ...n, read: true } : n
                                    )
                                  );
                                }}
                              >
                                Marcar como leída
                              </Button>
                            ) : null}
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
