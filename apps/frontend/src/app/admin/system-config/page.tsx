'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';

import { apiService } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

export default function SystemConfigPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [config, setConfig] = useState({
    operator_id: '',
    operator_name: '',
  });
  const [isConfigured, setIsConfigured] = useState(false);

  useEffect(() => {
    if (status === 'loading') return;

    if (!session) {
      router.push('/login');
      return;
    }

    if (!session.user?.roles?.includes('admin') && !session.user?.roles?.includes('mintic')) {
      router.push('/dashboard');
      return;
    }

    fetchConfig();
  }, [session, status, router]);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getSystemOperatorConfig();
      setConfig({
        operator_id: data.operator_id || '',
        operator_name: data.operator_name || '',
      });
      setIsConfigured(Boolean(data.is_configured));
    } catch (err) {
      console.error('Error fetching config:', err);
      setError('Error al cargar la configuración del sistema');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      await apiService.updateSystemOperatorConfig(
        config.operator_id,
        config.operator_name,
        session?.user?.email || 'admin'
      );
      setSuccess('Configuración actualizada exitosamente');
      setIsConfigured(true);
      await fetchConfig();
    } catch (err: any) {
      console.error('Error updating config:', err);
      setError(err.response?.data?.detail || 'Error al actualizar la configuración');
    } finally {
      setSaving(false);
    }
  };

  if (status === 'loading' || loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-12 w-12 animate-spin rounded-full border-2 border-primary-100 border-t-primary-500" />
          <p className="text-sm text-[var(--text-tertiary)]">Cargando configuración…</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <PageHeader
        breadcrumbs={[
          { label: 'Inicio', href: '/dashboard' },
          { label: 'Administración', href: '/admin' },
          { label: 'Configuración del sistema' },
        ]}
        title="Configuración del sistema"
        description="Define el operator ID y name que se utilizarán en todas las integraciones con el Hub MinTIC."
      />

      {error ? (
        <div className="mb-6 rounded-[var(--radius-md)] border border-danger-200 bg-danger-100/60 px-4 py-3 text-danger-600">
          {error}
        </div>
      ) : null}

      {success ? (
        <div className="mb-6 rounded-[var(--radius-md)] border border-success-200 bg-success-100/70 px-4 py-3 text-success-600">
          {success}
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Datos del operador</CardTitle>
          <CardDescription>
            Asegúrate de que estos valores coincidan con los registrados en el Hub de MinTIC.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--text-primary)]">
                Operator ID
              </label>
              <input
                type="text"
                value={config.operator_id}
                onChange={(event) => setConfig({ ...config, operator_id: event.target.value })}
                required
                placeholder="Ej: OP-12345"
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border-subtle)] px-3 py-2"
              />
              <p className="text-xs text-[var(--text-tertiary)]">
                Identificador único proporcionado por MinTIC para el operador.
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--text-primary)]">
                Operator Name
              </label>
              <input
                type="text"
                value={config.operator_name}
                onChange={(event) => setConfig({ ...config, operator_name: event.target.value })}
                required
                placeholder="Ej: Carpeta Ciudadana"
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border-subtle)] px-3 py-2"
              />
              <p className="text-xs text-[var(--text-tertiary)]">
                Nombre del operador que se utilizará en las operaciones con MinTIC.
              </p>
            </div>

            {isConfigured ? (
              <div className="rounded-[var(--radius-md)] border border-success-200 bg-success-100/80 px-3 py-3 text-sm text-success-700">
                La configuración está activa y siendo utilizada por el sistema.
              </div>
            ) : null}

            <div className="flex justify-end gap-2">
              <Button variant="ghost" type="button" onClick={() => router.back()} disabled={saving}>
                Cancelar
              </Button>
              <Button type="submit" isLoading={saving} disabled={saving}>
                Guardar configuración
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {isConfigured ? (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Configuración actual</CardTitle>
            <CardDescription>Valores aplicados en todo el sistema.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
                Operator ID
              </p>
              <p className="mt-1 font-mono text-sm text-[var(--text-primary)]">{config.operator_id}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
                Operator Name
              </p>
              <p className="mt-1 text-sm text-[var(--text-primary)]">{config.operator_name}</p>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </>
  );
}

