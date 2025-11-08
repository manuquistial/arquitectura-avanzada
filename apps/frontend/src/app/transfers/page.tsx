"use client";

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  FilePlus2,
  Mail,
  ShieldCheck,
  Share2,
  Upload,
  X,
} from 'lucide-react';

import { apiService } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { StatTile } from '@/components/ui/StatTile';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableEmpty,
} from '@/components/ui/Table';
import { SearchField } from '@/components/ui/SearchField';

interface Transfer {
  id: string;
  document_id: string;
  document_title: string;
  from_citizen_id: string;
  to_citizen_id: string;
  to_email: string;
  status: 'pending' | 'accepted' | 'rejected' | 'expired';
  created_at: string;
  expires_at: string;
  message?: string;
}

const statusBadges: Record<Transfer['status'], { label: string; variant: 'info' | 'success' | 'danger' | 'secondary' }> = {
  pending: { label: 'Pendiente', variant: 'info' },
  accepted: { label: 'Aceptada', variant: 'success' },
  rejected: { label: 'Rechazada', variant: 'danger' },
  expired: { label: 'Expirada', variant: 'secondary' },
};

export default function TransfersPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [activeTab, setActiveTab] = useState<'sent' | 'received'>('sent');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    if (session?.user?.id) {
      fetchTransfers();
    }
  }, [session, activeTab]);

  const fetchTransfers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getTransfers(session?.user?.id, session?.user?.roles);

      if (activeTab === 'sent') {
        setTransfers(data.filter((t: Transfer) => t.from_citizen_id === session?.user?.id));
      } else {
        setTransfers(data.filter((t: Transfer) => t.to_citizen_id === session?.user?.id));
      }
    } catch (error) {
      console.error('Error fetching transfers:', error);
      setError('Error al cargar las transferencias');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTransfer = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreating(true);

    try {
      const formData = new FormData(event.currentTarget);
      const destinationOperatorId = 'mintic';
      const transferData = {
        destination_operator_id: destinationOperatorId,
        citizen_id: String(session?.user?.id || ''),
        citizen_email: String(session?.user?.email || ''),
        citizen_name: String(session?.user?.name || ''),
        document_id: String(formData.get('document_id') || ''),
        to_email: String(formData.get('to_email') || ''),
        message: String(formData.get('message') || ''),
      };

      await apiService.createTransfer(transferData);
      setShowCreateModal(false);
      await fetchTransfers();
    } catch (error) {
      console.error('Error creating transfer:', error);
      setError('Error al crear la transferencia');
    } finally {
      setCreating(false);
    }
  };

  const handleAcceptTransfer = async (transferId: string) => {
    try {
      await apiService.acceptTransfer(transferId);
      await fetchTransfers();
    } catch (error) {
      console.error('Error accepting transfer:', error);
      setError('Error al aceptar la transferencia');
    }
  };

  const handleRejectTransfer = async (transferId: string) => {
    if (!confirm('¿Estás seguro de que quieres rechazar esta transferencia?')) {
      return;
    }

    try {
      await apiService.rejectTransfer(transferId);
      await fetchTransfers();
    } catch (error) {
      console.error('Error rejecting transfer:', error);
      setError('Error al rechazar la transferencia');
    }
  };

  const filteredTransfers = useMemo(() => {
    if (!searchTerm.trim()) {
      return transfers;
    }

    const term = searchTerm.trim().toLowerCase();
    return transfers.filter((transfer) => {
      return (
        transfer.document_title?.toLowerCase().includes(term) ||
        transfer.to_email?.toLowerCase().includes(term) ||
        transfer.from_citizen_id?.toLowerCase().includes(term)
      );
    });
  }, [transfers, searchTerm]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('es-CO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (status === 'loading' || loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-12 w-12 animate-spin rounded-full border-2 border-primary-100 border-t-primary-500" />
          <p className="text-sm text-[var(--text-tertiary)]">Cargando transferencias...</p>
        </div>
      </div>
    );
  }

  const sentCount = transfers.filter((t) => t.from_citizen_id === session?.user?.id).length;
  const receivedCount = transfers.filter((t) => t.to_citizen_id === session?.user?.id).length;
  const pendingCount = transfers.filter((t) => t.status === 'pending').length;

  return (
    <>
      <PageHeader
        breadcrumbs={[
          { label: 'Inicio', href: '/dashboard' },
          { label: 'Transferencias' },
        ]}
        title="Gestor de transferencias"
        description="Envía y recibe documentos entre operadores de forma segura y con trazabilidad completa."
        actions={[
          <Button
            key="new-transfer"
            icon={<Share2 className="h-4 w-4" />}
            onClick={() => setShowCreateModal(true)}
          >
            Nueva transferencia
          </Button>,
        ]}
      />

      {error ? (
        <Card className="border-danger-100 bg-danger-50/80">
          <CardHeader>
            <CardTitle className="text-danger-600">Se produjo un error</CardTitle>
            <CardDescription className="text-danger-500">{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="ghost" onClick={fetchTransfers}>
              Intentar nuevamente
            </Button>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Transferencias enviadas"
          value={sentCount}
          icon={<Upload className="h-5 w-5" />}
          tone="primary"
          helperText="Histórico de envíos"
        />
        <StatTile
          label="Transferencias recibidas"
          value={receivedCount}
          icon={<FilePlus2 className="h-5 w-5" />}
          tone="info"
          helperText="Documentos recibidos"
        />
        <StatTile
          label="Pendientes"
          value={pendingCount}
          icon={<ShieldCheck className="h-5 w-5" />}
          tone="warning"
          helperText="Acciones por gestionar"
        />
        <StatTile
          label="Activas"
          value={filteredTransfers.filter((t) => t.status === 'accepted').length}
          icon={<ArrowRight className="h-5 w-5" />}
          tone="success"
          helperText="Listas para revisión"
        />
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <CardTitle>Historial de transferencias</CardTitle>
            <CardDescription>Filtra por tipo o estado para encontrar transferencias rápidamente.</CardDescription>
          </div>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-4">
            <div className="flex items-center gap-3">
              <Button
                variant={activeTab === 'sent' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setActiveTab('sent')}
              >
                <span className="inline-flex items-center gap-2">
                  <Upload className="h-4 w-4" /> Enviadas ({sentCount})
                </span>
              </Button>
              <Button
                variant={activeTab === 'received' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setActiveTab('received')}
              >
                <span className="inline-flex items-center gap-2">
                  <FilePlus2 className="h-4 w-4" /> Recibidas ({receivedCount})
                </span>
              </Button>
            </div>
            <SearchField
              id="transfer-search"
              label="Buscar transferencias"
              value={searchTerm}
              onChange={setSearchTerm}
              placeholder="Buscar por documento o correo"
              className="w-full md:w-72"
            />
          </div>
        </CardHeader>
        <CardContent>
          {filteredTransfers.length === 0 ? (
            <TableEmpty>
              <Share2 className="h-10 w-10 text-info-500" />
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                {activeTab === 'sent'
                  ? 'Aún no has enviado transferencias'
                  : 'Aún no has recibido transferencias'}
              </h3>
              <p className="max-w-md text-sm text-[var(--text-secondary)]">
                {activeTab === 'sent'
                  ? 'Selecciona un documento y comparte el acceso con otros operadores o ciudadanos.'
                  : 'Cuando recibas una transferencia aparecerá aquí para que la aceptes o rechaces.'}
              </p>
              {activeTab === 'sent' ? (
                <Button icon={<Share2 className="h-4 w-4" />} onClick={() => setShowCreateModal(true)}>
                  Crear mi primera transferencia
                </Button>
              ) : null}
            </TableEmpty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Documento</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>{activeTab === 'sent' ? 'Destinatario' : 'Remitente'}</TableHead>
                  <TableHead>Creada</TableHead>
                  <TableHead>Expira</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTransfers.map((transfer) => {
                  const statusInfo = statusBadges[transfer.status] ?? {
                    label: transfer.status,
                    variant: 'secondary' as const,
                  };

                  return (
                    <TableRow key={transfer.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--primary-50)] text-[var(--primary-600)] shadow-sm">
                            <Share2 className="h-5 w-5" />
                          </div>
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-[var(--text-primary)]">
                              {transfer.document_title || 'Documento sin título'}
                            </p>
                            <p className="text-xs text-[var(--text-tertiary)]">
                              ID: {transfer.document_id}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-[var(--text-secondary)]">
                        {activeTab === 'sent' ? transfer.to_email : transfer.from_citizen_id}
                      </TableCell>
                      <TableCell className="text-sm text-[var(--text-secondary)]">
                        {formatDate(transfer.created_at)}
                      </TableCell>
                      <TableCell className="text-sm text-[var(--text-secondary)]">
                        {transfer.expires_at ? formatDate(transfer.expires_at) : '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          {activeTab === 'received' && transfer.status === 'pending' ? (
                            <>
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => handleAcceptTransfer(transfer.id)}
                              >
                                Aceptar
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-danger-500 hover:bg-danger-100/60"
                                onClick={() => handleRejectTransfer(transfer.id)}
                              >
                                Rechazar
                              </Button>
                            </>
                          ) : null}

                          {transfer.status === 'accepted' ? (
                            <Button
                              variant="outline"
                              size="sm"
                              icon={<ArrowRight className="h-4 w-4" />}
                              iconPosition="right"
                              href={`/documents?highlight=${transfer.document_id}`}
                            >
                              Ver documento
                            </Button>
                          ) : null}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {showCreateModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6">
          <div className="w-full max-w-lg rounded-[var(--radius-lg)] border border-[var(--primary-100)] bg-white p-6 shadow-soft">
            <div className="mb-6 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold text-[var(--text-primary)]">Nueva transferencia</h2>
                <p className="text-sm text-[var(--text-secondary)]">
                  Completa los datos para compartir el documento con otro ciudadano u operador.
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                icon={<X className="h-4 w-4" />}
                aria-label="Cerrar"
                onClick={() => setShowCreateModal(false)}
              />
            </div>

            <form onSubmit={handleCreateTransfer} className="space-y-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-[var(--text-primary)]">Documento</label>
                <select
                  name="document_id"
                  required
                  className="w-full rounded-[var(--radius-sm)] border border-[var(--primary-100)] bg-white px-3 py-2 text-sm text-[var(--text-primary)] focus-visible:ring-2 focus-visible:ring-[var(--info-200)]"
                >
                  <option value="">Selecciona un documento…</option>
                  <option value="doc1">Cédula de ciudadanía</option>
                  <option value="doc2">Diploma universitario</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium text-[var(--text-primary)]">Email del destinatario</label>
                <div className="relative">
                  <input
                    type="email"
                    name="to_email"
                    required
                    placeholder="usuario@ejemplo.com"
                    className="w-full rounded-[var(--radius-sm)] border border-[var(--primary-100)] bg-white px-3 py-2 pl-10 text-sm text-[var(--text-primary)] focus-visible:ring-2 focus-visible:ring-[var(--info-200)]"
                  />
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-sm font-medium text-[var(--text-primary)]">Mensaje (opcional)</label>
                <textarea
                  name="message"
                  rows={3}
                  placeholder="Mensaje para el destinatario…"
                  className="w-full rounded-[var(--radius-sm)] border border-[var(--primary-100)] bg-white px-3 py-2 text-sm text-[var(--text-primary)] focus-visible:ring-2 focus-visible:ring-[var(--info-200)]"
                />
              </div>

              <div className="flex flex-wrap justify-end gap-3 pt-4">
                <Button variant="ghost" type="button" onClick={() => setShowCreateModal(false)} disabled={creating}>
                  Cancelar
                </Button>
                <Button type="submit" isLoading={creating}>
                  {creating ? 'Enviando…' : 'Enviar transferencia'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
