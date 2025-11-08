"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import {
  Layers,
  ShieldCheck,
  Lock,
  FileClock,
  Filter,
  RefreshCcw,
} from "lucide-react";

import { apiService } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatTile } from "@/components/ui/StatTile";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableEmpty,
} from "@/components/ui/Table";
import { SearchField } from "@/components/ui/SearchField";

interface DocumentMetadata {
  id: string;
  citizen_id: string;
  title: string;
  filename: string;
  content_type: string;
  size_bytes?: number;
  sha256_hash?: string;
  blob_name: string;
  storage_provider: string;
  status: string;
  is_uploaded: boolean;
  state: string;
  worm_locked: boolean;
  signed_at?: string;
  retention_until?: string;
  hub_signature_ref?: string;
  legal_hold: boolean;
  lifecycle_tier: string;
  description?: string;
  tags?: string;
  is_deleted: boolean;
  created_at: string;
  updated_at?: string;
}

type FilterValue = "all" | "signed" | "unsigned" | "worm_locked";
type SortField = "created_at" | "updated_at" | "title";
type SortOrder = "asc" | "desc";

export default function MetadataPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [metadata, setMetadata] = useState<DocumentMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [quickFilter, setQuickFilter] = useState<
    "all" | "worm_locked" | "retention" | "legal_hold"
  >("all");
  const [sortBy, setSortBy] = useState<SortField>("created_at");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [searchTerm, setSearchTerm] = useState("");
  const [providerFilter, setProviderFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  const fetchMetadata = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const citizenId = session?.user?.id || "1234567890";
      const data = await apiService.getDocumentMetadata(citizenId);
      const dataArray = Array.isArray(data) ? data : [];
      setMetadata(dataArray);
    } catch (err) {
      console.error("Error fetching metadata:", err);
      setError("Error al cargar los metadatos");
    } finally {
      setLoading(false);
    }
  }, [session?.user?.id]);

  useEffect(() => {
    if (session?.user?.id) {
      fetchMetadata();
    }
  }, [session?.user?.id, fetchMetadata]);

  const sortedAndFilteredMetadata = useMemo(() => {
    const filteredByQuick = metadata.filter((doc) => {
      if (quickFilter === "worm_locked") {
        return doc.worm_locked;
      }
      if (quickFilter === "retention") {
        return Boolean(doc.retention_until);
      }
      if (quickFilter === "legal_hold") {
        return doc.legal_hold;
      }
      return true;
    });

    const filteredByProvider = filteredByQuick.filter((doc) => {
      if (providerFilter === "all") return true;
      return doc.storage_provider?.toLowerCase() === providerFilter;
    });

    const filteredByType = filteredByProvider.filter((doc) => {
      if (typeFilter === "all") return true;
      return doc.content_type?.toLowerCase() === typeFilter;
    });

    const filteredBySearch = filteredByType.filter((doc) => {
      if (!searchTerm.trim()) return true;
      const term = searchTerm.trim().toLowerCase();
      const title = (doc.title || "").toLowerCase();
      const filename = (doc.filename || "").toLowerCase();
      const hash = (doc.sha256_hash || "").toLowerCase();
      return (
        title.includes(term) || filename.includes(term) || hash.includes(term)
      );
    });

    const sorted = [...filteredBySearch].sort((a, b) => {
      let aValue: string | number = 0;
      let bValue: string | number = 0;

      switch (sortBy) {
        case "title":
          aValue = (a.title || a.filename).toLowerCase();
          bValue = (b.title || b.filename).toLowerCase();
          break;
        case "updated_at":
          aValue = new Date(a.updated_at || a.created_at).getTime();
          bValue = new Date(b.updated_at || b.created_at).getTime();
          break;
        case "created_at":
        default:
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
      }

      if (sortOrder === "asc") {
          return aValue > bValue ? 1 : -1;
      }
          return aValue < bValue ? 1 : -1;
    });

    return sorted;
  }, [metadata, quickFilter, providerFilter, typeFilter, searchTerm, sortBy, sortOrder]);

  const stats = useMemo(() => {
    const total = metadata.length;
    const worm = metadata.filter((doc) => doc.worm_locked).length;
    const retention = metadata.filter((doc) => Boolean(doc.retention_until)).length;
    const legalHold = metadata.filter((doc) => doc.legal_hold).length;

    return { total, worm, retention, legalHold };
  }, [metadata]);

  const providerOptions = useMemo(() => {
    const providers = new Set<string>();
    metadata.forEach((doc) => {
      if (doc.storage_provider) {
        providers.add(doc.storage_provider.toLowerCase());
      }
    });
    return Array.from(providers).sort();
  }, [metadata]);

  const typeOptions = useMemo(() => {
    const types = new Set<string>();
    metadata.forEach((doc) => {
      if (doc.content_type) {
        types.add(doc.content_type.toLowerCase());
      }
    });
    return Array.from(types).sort();
  }, [metadata]);

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleString("es-ES", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "N/A";
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const index = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, index)).toFixed(1)} ${sizes[index]}`;
  };

  const getStatusBadge = (doc: DocumentMetadata) => {
    if (doc.state === "SIGNED" || doc.status === "signed" || doc.status === "authenticated") {
      return <Badge variant="success">Firmado</Badge>;
    }
    if (doc.worm_locked) {
      return <Badge variant="info">Bloqueado (WORM)</Badge>;
    }
    if (!doc.is_uploaded) {
      return <Badge variant="warning">Pendiente de carga</Badge>;
    }
    return <Badge variant="secondary">{doc.state || doc.status || "Desconocido"}</Badge>;
  };

  const filterOptions: Array<{ value: FilterValue; label: string; count: number }> = [
    { value: "all", label: "Todos", count: stats.total },
    { value: "signed", label: "Firmados", count: stats.signed },
    { value: "unsigned", label: "Sin firmar", count: stats.unsigned },
    { value: "worm_locked", label: "WORM", count: stats.worm },
  ];

  if (status === "loading" || loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-12 w-12 animate-spin rounded-full border-2 border-primary-100 border-t-primary-500" />
          <p className="text-sm text-[var(--text-tertiary)]">Cargando metadatos…</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <PageHeader
        breadcrumbs={[
          { label: 'Inicio', href: '/dashboard' },
          { label: 'Documentos', href: '/documents' },
          { label: 'Metadatos' },
        ]}
        title="Metadatos de documentos"
        description="Consulta información técnica de cada documento: hashes, retenciones, estados WORM y trazabilidad completa."
        actions={[
          <Button key="refresh" variant="ghost" icon={<RefreshCcw className="h-4 w-4" />} onClick={fetchMetadata}>
            Actualizar
          </Button>,
        ]}
      />

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Documentos indexados"
          value={stats.total}
          icon={<Layers className="h-5 w-5" />}
          tone="primary"
          helperText="Total de registros con metadatos"
        />
        <StatTile
          label="Bloqueados WORM"
          value={stats.worm}
          icon={<Lock className="h-5 w-5" />}
          tone="info"
          helperText="No admiten modificaciones"
        />
        <StatTile
          label="Con retención"
          value={stats.retention}
          icon={<FileClock className="h-5 w-5" />}
          tone="warning"
          helperText="Tienen fecha de custodia"
        />
        <StatTile
          label="Legal hold activo"
          value={stats.legalHold}
          icon={<ShieldCheck className="h-5 w-5" />}
          tone="success"
          helperText="Sujetos a retención legal"
        />
        </div>

      {error ? (
        <Card className="border-danger-100 bg-danger-50/80">
          <CardHeader>
            <CardTitle className="text-danger-600">Se produjo un error</CardTitle>
            <CardDescription className="text-danger-500">{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="ghost" onClick={fetchMetadata} icon={<RefreshCcw className="h-4 w-4" />}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      ) : null}

      <Card className="border-[var(--primary-100)] bg-white/90">
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
            <CardTitle>Filtros y orden</CardTitle>
            <CardDescription>Refina por políticas de retención, proveedor o tipo de contenido.</CardDescription>
          </div>
          <div className="flex items-center gap-2 text-sm text-[var(--text-tertiary)]">
            <Filter className="h-4 w-4" />
            {sortedAndFilteredMetadata.length} resultados
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap gap-2">
              {[
                { value: "all", label: "Todos", count: stats.total },
                { value: "worm_locked", label: "Bloqueados WORM", count: stats.worm },
                { value: "retention", label: "Con retención", count: stats.retention },
                { value: "legal_hold", label: "Legal hold", count: stats.legalHold },
              ].map((option) => (
                <Button
                  key={option.value}
                  variant={quickFilter === option.value ? "primary" : "secondary"}
                  size="sm"
                  onClick={() => setQuickFilter(option.value as typeof quickFilter)}
                >
                  {option.label} ({option.count})
                </Button>
              ))}
            </div>
            <SearchField
              id="metadata-search"
              label="Buscar en metadatos"
              value={searchTerm}
              onChange={setSearchTerm}
              placeholder="Buscar por título, archivo o hash"
              className="w-full md:w-72"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
                Proveedor de almacenamiento
              </span>
              <select
                value={providerFilter}
                onChange={(event) => setProviderFilter(event.target.value)}
                className="rounded-[var(--radius-sm)] border border-[var(--primary-100)] bg-white/85 px-3 py-2 text-sm text-[var(--text-primary)] shadow-sm focus-visible:ring-2 focus-visible:ring-[var(--info-200)]"
              >
                <option value="all">Todos</option>
                {providerOptions.map((provider) => (
                  <option key={provider} value={provider}>
                    {provider}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
                Tipo de contenido
              </span>
              <select
                value={typeFilter}
                onChange={(event) => setTypeFilter(event.target.value)}
                className="rounded-[var(--radius-sm)] border border-[var(--primary-100)] bg-white/85 px-3 py-2 text-sm text-[var(--text-primary)] shadow-sm focus-visible:ring-2 focus-visible:ring-[var(--info-200)]"
              >
                <option value="all">Todos</option>
                {typeOptions.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
                Ordenar por
              </span>
              <select
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value as SortField)}
                className="rounded-[var(--radius-sm)] border border-[var(--primary-100)] bg-white/85 px-3 py-2 text-sm text-[var(--text-primary)] shadow-sm focus-visible:ring-2 focus-visible:ring-[var(--info-200)]"
              >
                <option value="created_at">Fecha de creación</option>
                <option value="updated_at">Última actualización</option>
                <option value="title">Título</option>
              </select>
            </div>
            
            <div className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
                Orden
              </span>
              <select
                value={sortOrder}
                onChange={(event) => setSortOrder(event.target.value as SortOrder)}
                className="rounded-[var(--radius-sm)] border border-[var(--primary-100)] bg-white/85 px-3 py-2 text-sm text-[var(--text-primary)] shadow-sm focus-visible:ring-2 focus-visible:ring-[var(--info-200)]"
              >
                <option value="desc">Descendente</option>
                <option value="asc">Ascendente</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-[var(--primary-100)] bg-white/90">
        <CardHeader>
          <CardTitle>Listado de metadatos</CardTitle>
          <CardDescription>
            Información técnica y jurídica asociada a cada documento almacenado.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sortedAndFilteredMetadata.length === 0 ? (
            <TableEmpty>
              <div className="text-5xl">📊</div>
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                No se encontraron metadatos con los filtros aplicados
            </h3>
              <p className="text-sm text-[var(--text-secondary)]">
                Ajusta los filtros o verifica que existan documentos registrados.
              </p>
            </TableEmpty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Documento</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Tamaño</TableHead>
                  <TableHead>WORM</TableHead>
                  <TableHead>Retención</TableHead>
                  <TableHead>Trazabilidad</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedAndFilteredMetadata.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <span className="text-sm font-semibold text-[var(--text-primary)]">
                            {doc.title || doc.filename}
                        </span>
                        <span className="text-xs text-[var(--text-tertiary)]">{doc.filename}</span>
                        {doc.sha256_hash ? (
                          <span className="font-mono text-xs text-[var(--text-tertiary)]/80">
                            SHA-256: {doc.sha256_hash.slice(0, 16)}…
                          </span>
                        ) : null}
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="secondary">{doc.content_type || "Tipo desconocido"}</Badge>
                          <Badge variant="secondary">Blob: {doc.blob_name}</Badge>
                        </div>
                            </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-2">
                        {getStatusBadge(doc)}
                        {doc.hub_signature_ref ? (
                          <p className="text-xs text-[var(--text-tertiary)]">
                            Hub Ref: {doc.hub_signature_ref}
                          </p>
                        ) : null}
                        {doc.is_deleted ? (
                          <Badge variant="danger">Marcado para eliminación</Badge>
                        ) : null}
                        </div>
                    </TableCell>
                    <TableCell className="text-sm text-[var(--text-secondary)]">
                        {formatFileSize(doc.size_bytes)}
                    </TableCell>
                    <TableCell>
                        {doc.worm_locked ? (
                        <Badge variant="danger">Bloqueado</Badge>
                      ) : (
                        <Badge variant="secondary">No bloqueado</Badge>
                      )}
                      {doc.legal_hold ? (
                        <p className="text-xs text-[var(--text-tertiary)]">Legal hold activo</p>
                      ) : null}
                      {doc.lifecycle_tier ? (
                        <p className="text-xs text-[var(--text-tertiary)]">
                          Tier: {doc.lifecycle_tier}
                        </p>
                      ) : null}
                    </TableCell>
                    <TableCell className="text-sm text-[var(--text-secondary)]">
                        {doc.retention_until ? (
                          <div>
                          <p>Hasta: {formatDate(doc.retention_until)}</p>
                          {doc.worm_locked ? (
                            <p className="text-xs text-[var(--text-tertiary)]">
                              Bloqueo indefinido tras la fecha
                            </p>
                          ) : null}
                          </div>
                        ) : (
                        <span className="text-[var(--text-tertiary)]">Sin retención</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-[var(--text-secondary)]">
                      <div className="space-y-1">
                        <p>Creado: {formatDate(doc.created_at)}</p>
                        {doc.updated_at ? <p>Actualizado: {formatDate(doc.updated_at)}</p> : null}
                        {doc.signed_at ? (
                          <p className="text-success-600">Firmado: {formatDate(doc.signed_at)}</p>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}

