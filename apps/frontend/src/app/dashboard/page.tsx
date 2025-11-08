/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { useSession } from 'next-auth/react';
import {
  Clock3,
  FileText,
  PenSquare,
  ShieldCheck,
  Shuffle,
  ArrowRight,
} from 'lucide-react';

import { apiService } from '@/lib/api';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/Card';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatTile } from '@/components/ui/StatTile';
import { Badge } from '@/components/ui/Badge';

interface DashboardStats {
  totalDocuments: number;
  signedDocuments: number;
  pendingTransfers: number;
  sharedDocuments: number;
}

interface Activity {
  description: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats>({
    totalDocuments: 0,
    signedDocuments: 0,
    pendingTransfers: 0,
    sharedDocuments: 0,
  });
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status === 'loading') return;
    if (!session) {
      router.push('/login');
    }
  }, [session, status]);

  useEffect(() => {
    async function loadDashboard() {
      if (!session?.user?.id) return;

        try {
          setLoading(true);
        const citizenId = session.user.id;
        const [dashboardStats, recentActivities] = await Promise.all([
            apiService.getDashboardStats(citizenId),
          apiService.getRecentActivities(citizenId),
          ]);

        setStats(dashboardStats);
        setActivities(recentActivities);
        } catch (error) {
          console.error('Error loading dashboard data:', error);
        } finally {
          setLoading(false);
        }
      }

    loadDashboard();
  }, [session?.user?.id]);

  const pendingSignatures = Math.max(stats.totalDocuments - stats.signedDocuments, 0);

  const statTiles = [
    {
      label: 'Documentos totales',
      value: loading ? '—' : stats.totalDocuments,
      icon: <FileText className="h-5 w-5" />,
      tone: 'primary' as const,
      helperText: loading ? 'Actualizando…' : `${stats.signedDocuments} firmados`,
      href: '/documents',
    },
    {
      label: 'Pendientes por firmar',
      value: loading ? '—' : pendingSignatures,
      icon: <PenSquare className="h-5 w-5" />,
      tone: 'warning' as const,
      helperText: pendingSignatures > 0 ? 'Atiéndelos hoy' : 'Todo al día',
      href: '/documents?filter=pending',
    },
    {
      label: 'Documentos firmados',
      value: loading ? '—' : stats.signedDocuments,
      icon: <ShieldCheck className="h-5 w-5" />,
      tone: 'success' as const,
      helperText: loading ? ' ' : 'Firmas vigentes',
      href: '/documents?filter=signed',
    },
    {
      label: 'Transferencias pendientes',
      value: loading ? '—' : stats.pendingTransfers,
      icon: <Shuffle className="h-5 w-5" />,
      tone: 'info' as const,
      helperText:
        stats.pendingTransfers > 0 ? 'Revisa los movimientos' : 'Sin transferencias pendientes',
      href: '/transfers',
    },
  ];

  const recommendations = useMemo(() => {
    const items: Array<{
      title: string;
      description?: string;
      href?: string;
      cta?: string;
      tone: 'warning' | 'success' | 'info';
    }> = [];

    if (pendingSignatures > 0) {
      items.push({
        title: `${pendingSignatures} documentos esperan tu firma`,
        description: 'Revisa y firma para mantener tu carpeta al día.',
        href: '/documents?filter=pending',
        cta: 'Revisar pendientes',
        tone: 'warning',
      });
    }

    if (stats.pendingTransfers > 0) {
      items.push({
        title: `${stats.pendingTransfers} transferencias necesitan seguimiento`,
        description: 'Confirma o rechaza las solicitudes para que no caduquen.',
        href: '/transfers',
        cta: 'Gestionar transferencias',
        tone: 'info',
      });
    }

    if (stats.sharedDocuments > 0) {
      items.push({
        title: `${stats.sharedDocuments} documentos están compartidos`,
        description: 'Verifica quién tiene acceso y revoca permisos si es necesario.',
        href: '/documents',
        cta: 'Revisar documentos compartidos',
        tone: 'success',
      });
    }

    if (items.length === 0) {
      items.push({
        title: '¡Todo en orden!',
        description: 'No tienes tareas pendientes por ahora. Consulta tus documentos cuando lo necesites.',
        tone: 'success',
      });
    }

    return items;
  }, [pendingSignatures, stats.pendingTransfers, stats.sharedDocuments]);

  if (status === 'loading' || !session) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-12 w-12 animate-spin rounded-full border-2 border-primary-100 border-t-primary-500" />
          <p className="text-sm text-[var(--text-tertiary)]">
            Preparando tu espacio de trabajo...
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <PageHeader
        breadcrumbs={[{ label: 'Inicio' }]}
        title={`Hola, ${session.user?.name ?? 'Usuario'}`}
        description="Mantén tu carpeta al día y accede rápidamente a tus trámites más frecuentes."
      />

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        {statTiles.map((tile) => (
          <Link key={tile.label} href={tile.href ?? '#'} className="transition-transform hover:-translate-y-1">
            <StatTile
              label={tile.label}
              value={tile.value}
              icon={tile.icon}
              tone={tile.tone}
              helperText={tile.helperText}
              className="h-full"
            />
          </Link>
        ))}
          </div>

      <div className="grid grid-cols-1 gap-6">
        <Card className="border-[var(--primary-100)] bg-white/90">
          <CardHeader>
            <CardTitle>Acciones recomendadas</CardTitle>
            <CardDescription>
              Prioriza las tareas que mantienen tu carpeta ciudadana al día.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {recommendations.map((item, index) => {
              const toneStyles = {
                warning: 'border-[var(--accent-200)] bg-[var(--accent-50)] text-[var(--accent-600)]',
                success: 'border-success-100 bg-[var(--success-50)] text-success-600',
                info: 'border-info-100 bg-[var(--info-50)] text-info-600',
              };

              return (
                <div
                  key={`${item.title}-${index}`}
                  className={cn(
                    'rounded-[var(--radius-md)] border px-4 py-4 shadow-sm backdrop-blur',
                    toneStyles[item.tone]
                  )}
                >
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div className="max-w-lg">
                      <p className="text-sm font-semibold">{item.title}</p>
                      {item.description ? (
                        <p className="text-xs opacity-80">{item.description}</p>
                      ) : null}
                    </div>
                    {item.cta && item.href ? (
                      <Button
                        variant="secondary"
                        size="sm"
                        href={item.href}
                        icon={<ArrowRight className="h-4 w-4" />}
                        iconPosition="right"
                        className="border-none bg-white/60 text-[inherit] hover:bg-white/80"
                      >
                        {item.cta}
                      </Button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      <Card className="border-[var(--primary-100)] bg-white/90">
        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
            <CardTitle>Actividades recientes</CardTitle>
            <CardDescription>
              Últimas interacciones realizadas en la plataforma.
            </CardDescription>
                            </div>
          <Badge variant="info" className="gap-1">
            <Clock3 className="mr-2 h-3.5 w-3.5" />
            {activities.length} actividades
          </Badge>
        </CardHeader>
        <CardContent>
          {activities.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-[var(--radius-md)] border border-dashed border-[var(--primary-100)] bg-[var(--primary-25)]/60 p-8 text-center">
              <Clock3 className="h-6 w-6 text-info-500" />
              <p className="text-sm font-medium text-[var(--text-primary)]">
                Aún no registramos actividades recientes.
              </p>
              <p className="text-xs text-[var(--text-secondary)]">
                Las actualizaciones aparecerán aquí tan pronto como interactúes
                con tus documentos.
              </p>
                              </div>
          ) : (
            <ul className="space-y-4">
              {activities.slice(0, 6).map((activity, index) => (
                <li
                  key={`${activity.timestamp}-${index}`}
                  className="flex items-start gap-4 rounded-[var(--radius-md)] border border-[var(--primary-100)] bg-white/70 p-4 shadow-sm"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--primary-50)] text-[var(--primary-600)]">
                    <FileText className="h-5 w-5" />
                              </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-[var(--text-primary)]">
                      {activity.description}
                    </p>
                    <p className="mt-1 text-xs text-[var(--text-tertiary)]">
                      {new Date(activity.timestamp).toLocaleString('es-CO', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                        </div>
                      </li>
                    ))}
                  </ul>
          )}
        </CardContent>
      </Card>
    </>
  );
}
