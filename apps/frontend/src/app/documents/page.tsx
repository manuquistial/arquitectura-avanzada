"use client";

import {
  FormEvent,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  CSSProperties,
} from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowDownToLine,
  FilePlus2,
  FileText,
  PenSquare,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";

import { apiService } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { StatTile } from "@/components/ui/StatTile";
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
import { Tooltip } from "@/components/ui/Tooltip";
import { cn } from "@/lib/utils";

interface Document {
  id: string;
  title: string;
  filename: string;
  content_type: string;
  status: string;
  state?: string;
  worm_locked?: boolean;
  signed_at?: string;
  size_bytes?: number;
  created_at: string;
  updated_at: string;
}

type StatusTone = "info" | "success" | "warning" | "danger" | "default";
type SignatureType = "PAdES" | "XAdES" | "CAdES";

const statusMap: Record<
  string,
  { label: string; tone: StatusTone; badgeStyle: CSSProperties; description?: string }
> = {
  signed: {
    label: 'Firmado',
    tone: 'success',
    badgeStyle: {
      backgroundColor: 'var(--success-200)',
      color: 'var(--success-700)',
      borderColor: 'var(--success-300)',
    },
  },
  authenticated: {
    label: 'Autenticado',
    tone: 'success',
    badgeStyle: {
      backgroundColor: 'var(--success-200)',
      color: 'var(--success-700)',
      borderColor: 'var(--success-300)',
    },
    description: 'Validado por entidad certificadora',
  },
  uploaded: {
    label: 'Subido',
    tone: 'info',
    badgeStyle: {
      backgroundColor: 'var(--info-200)',
      color: 'var(--info-700)',
      borderColor: 'var(--info-300)',
    },
  },
  pending: {
    label: 'Pendiente',
    tone: 'warning',
    badgeStyle: {
      backgroundColor: 'var(--accent-200)',
      color: 'var(--accent-600)',
      borderColor: 'var(--accent-300)',
    },
    description: 'Requiere revisión o firma',
  },
  processing: {
    label: 'Procesando',
    tone: 'info',
    badgeStyle: {
      backgroundColor: 'var(--info-100)',
      color: 'var(--info-600)',
      borderColor: 'var(--info-200)',
    },
    description: 'Estamos preparando tu documento',
  },
  in_progress: {
    label: 'En progreso',
    tone: 'info',
    badgeStyle: {
      backgroundColor: 'var(--info-100)',
      color: 'var(--info-600)',
      borderColor: 'var(--info-200)',
    },
  },
  queued: {
    label: 'En cola',
    tone: 'info',
    badgeStyle: {
      backgroundColor: 'var(--primary-100)',
      color: 'var(--primary-700)',
      borderColor: 'var(--primary-200)',
    },
  },
  draft: {
    label: 'Borrador',
    tone: 'default',
    badgeStyle: {
      backgroundColor: 'var(--surface-muted)',
      color: 'var(--text-secondary)',
      borderColor: 'var(--border-subtle)',
    },
  },
  revoked: {
    label: 'Revocado',
    tone: 'danger',
    badgeStyle: {
      backgroundColor: 'var(--danger-200)',
      color: 'var(--danger-700)',
      borderColor: 'var(--danger-300)',
    },
  },
  rejected: {
    label: 'Rechazado',
    tone: 'danger',
    badgeStyle: {
      backgroundColor: 'var(--danger-200)',
      color: 'var(--danger-700)',
      borderColor: 'var(--danger-300)',
    },
  },
  failed: {
    label: 'Fallido',
    tone: 'danger',
    badgeStyle: {
      backgroundColor: 'var(--danger-200)',
      color: 'var(--danger-700)',
      borderColor: 'var(--danger-300)',
    },
  },
  error: {
    label: 'Error',
    tone: 'danger',
    badgeStyle: {
      backgroundColor: 'var(--danger-200)',
      color: 'var(--danger-700)',
      borderColor: 'var(--danger-300)',
    },
  },
  deleted: {
    label: 'Eliminado',
    tone: 'default',
    badgeStyle: {
      backgroundColor: 'var(--surface-muted)',
      color: 'var(--text-secondary)',
      borderColor: 'var(--border-subtle)',
    },
  },
  expired: {
    label: 'Expirado',
    tone: 'warning',
    badgeStyle: {
      backgroundColor: 'var(--accent-200)',
      color: 'var(--accent-600)',
      borderColor: 'var(--accent-300)',
    },
  },
  shared: {
    label: 'Compartido',
    tone: 'info',
    badgeStyle: {
      backgroundColor: 'var(--info-200)',
      color: 'var(--info-700)',
      borderColor: 'var(--info-300)',
    },
  },
};

const fallbackStatus = {
  label: 'Estado desconocido',
  tone: 'info' as StatusTone,
  badgeStyle: {
    backgroundColor: 'var(--primary-100)',
    color: 'var(--primary-700)',
    borderColor: 'var(--primary-200)',
  },
};

function normalizeStatus(value?: string | null) {
  return value ? value.toLowerCase() : undefined;
}

function getStatus(doc: Document) {
  if (doc.worm_locked || doc.state === 'SIGNED') {
    return statusMap.signed;
  }

  const normalizedStatus = normalizeStatus(doc.status);
  if (normalizedStatus && statusMap[normalizedStatus]) {
    return statusMap[normalizedStatus];
  }

  const normalizedState = normalizeStatus(doc.state);
  if (normalizedState && statusMap[normalizedState]) {
    return statusMap[normalizedState];
  }

  return {
    ...fallbackStatus,
    label: doc.status || doc.state || fallbackStatus.label,
  };
}

function DocumentsPageContent() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const modalRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [showSignModal, setShowSignModal] = useState(false);
  const [signingDocumentId, setSigningDocumentId] = useState<string | null>(null);
  const [signatureType, setSignatureType] = useState<SignatureType>("PAdES");
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const signModalRef = useRef<HTMLDivElement | null>(null);
  const signatureSelectRef = useRef<HTMLSelectElement | null>(null);
  const [filter, setFilter] = useState<"all" | "pending" | "signed">("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [citizenDocumentId, setCitizenDocumentId] = useState<string | null>(
    session?.user?.citizen_id ?? null
  );
  const [resolvingCitizenId, setResolvingCitizenId] = useState(false);
  const userRoles = useMemo(() => session?.user?.roles ?? [], [session?.user?.roles]);
  const isAdmin = useMemo(() => userRoles.includes("admin"), [userRoles]);
  const effectiveCitizenId = useMemo(
    () => citizenDocumentId ?? session?.user?.citizen_id ?? null,
    [citizenDocumentId, session?.user?.citizen_id]
  );

  useEffect(() => {
    const filterParam = searchParams.get("filter");
    if (filterParam === "pending" || filterParam === "signed" || filterParam === "all") {
      if (filterParam !== filter) {
        setFilter(filterParam as typeof filter);
      }
    }

    const uploadParam = searchParams.get("upload");
    if (uploadParam === "new" && !showUploadModal) {
      setShowUploadModal(true);
    }
  }, [filter, searchParams, showUploadModal]);

  useEffect(() => {
    let cancelled = false;

    const resolveCitizenId = async () => {
      if (!session?.user?.id) {
        setCitizenDocumentId(null);
        return;
      }

      setResolvingCitizenId(true);
      try {
        const profile = await apiService.getCurrentUser();
        if (!cancelled) {
          const resolvedId = profile?.citizen_id ?? session.user?.citizen_id ?? null;
          setCitizenDocumentId(resolvedId);
        }
      } catch (err) {
        console.error("Error fetching current user profile:", err);
        if (!cancelled) {
          setCitizenDocumentId(session?.user?.citizen_id ?? null);
        }
      } finally {
        if (!cancelled) {
          setResolvingCitizenId(false);
        }
      }
    };

    resolveCitizenId();

    return () => {
      cancelled = true;
    };
  }, [session?.user?.id, session?.user?.citizen_id]);

  const fetchDocuments = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const targetCitizenId =
        effectiveCitizenId ?? (isAdmin ? "1234567890" : null);

      if (!targetCitizenId) {
        setDocuments([]);
        setError(
          "Tu cuenta no tiene un ciudadano asociado. Solicita a un administrador que complete la vinculación antes de gestionar documentos."
        );
        return;
      }

      const data = await apiService.getDocuments(
        targetCitizenId,
        userRoles
      );
      setDocuments(data);
    } catch (err) {
      console.error("Error fetching documents:", err);
      setError("Error al cargar los documentos. Intenta nuevamente.");
    } finally {
      setLoading(false);
    }
  }, [effectiveCitizenId, isAdmin, userRoles]);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    if (!session?.user?.id) {
      return;
    }
    if (resolvingCitizenId) {
      return;
    }
    if (!effectiveCitizenId && !isAdmin) {
      return;
    }
    fetchDocuments();
  }, [session?.user?.id, resolvingCitizenId, effectiveCitizenId, isAdmin, fetchDocuments]);

  const handleUpload = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setUploading(true);
    
    try {
      const formData = new FormData(event.currentTarget);
        const file = formData.get("file") as File | null;
        const title = (formData.get("title") as string) ?? "";
        const description = (formData.get("description") as string) ?? "";

      if (!file || !title) {
          throw new Error("Archivo y título son requeridos");
      }

      const citizenIdForUpload = effectiveCitizenId ?? session?.user?.citizen_id ?? null;
      if (!citizenIdForUpload) {
        throw new Error("Tu cuenta no tiene un ciudadano asociado para subir documentos.");
      }

      await apiService.uploadDocumentDirect(
        file,
        citizenIdForUpload,
        title,
        description
      );

      setShowUploadModal(false);
        await fetchDocuments();
      } catch (err) {
        console.error("Error uploading document:", err);
        setError(
          "Error al subir el documento. Por favor, intenta nuevamente."
        );
    } finally {
      setUploading(false);
    }
    },
    [effectiveCitizenId, fetchDocuments, session?.user?.citizen_id]
  );

  const handleDownload = useCallback(async (documentId: string, filename: string) => {
    try {
      await apiService.downloadDocument(documentId, filename);
    } catch (err) {
      console.error("Error downloading document:", err);
      setError("No pudimos descargar el documento. Intenta más tarde.");
    }
  }, []);

  const handleDelete = useCallback(
    async (documentId: string) => {
      const confirmed = window.confirm(
        "¿Estás seguro de que quieres eliminar este documento?"
      );
      if (!confirmed) return;

      try {
        const citizenIdForDelete = effectiveCitizenId ?? session?.user?.citizen_id ?? null;
        if (!citizenIdForDelete) {
          throw new Error("Tu cuenta no tiene un ciudadano asociado. No se puede eliminar el documento.");
        }
        await apiService.deleteDocument(documentId, citizenIdForDelete);
        await fetchDocuments();
      } catch (err) {
        console.error("Error deleting document:", err);
        setError("No pudimos eliminar el documento. Vuelve a intentarlo.");
      }
    },
    [effectiveCitizenId, fetchDocuments, session?.user?.citizen_id]
  );

  const formatFileSize = useCallback((bytes?: number) => {
    if (!bytes) return "Tamaño desconocido";
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const index = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, index)).toFixed(1)} ${sizes[index]}`;
  }, []);

  const totalSigned = useMemo(
    () =>
      documents.filter(
        (doc) => doc.state === 'SIGNED' || doc.status === 'signed'
      ).length,
    [documents]
  );
  const pendingDocuments = useMemo(
    () =>
      documents.filter(
        (doc) => doc.status !== "signed" && doc.state !== "SIGNED" && !doc.worm_locked
      ),
    [documents]
  );
  const signedDocuments = useMemo(
    () =>
      documents.filter((doc) => doc.status === "signed" || doc.state === "SIGNED"),
    [documents]
  );

  const filteredDocuments = useMemo(() => {
    const byStatus = (() => {
      if (filter === 'all') return documents;
      if (filter === 'pending') {
        return documents.filter(
          (doc) => doc.status !== 'signed' && doc.state !== 'SIGNED' && !doc.worm_locked
        );
      }
      if (filter === 'signed') {
        return documents.filter(
          (doc) => doc.status === 'signed' || doc.state === 'SIGNED' || doc.worm_locked
        );
      }
      return documents;
    })();

    if (!searchTerm.trim()) {
      return byStatus;
    }

    const normalizedTerm = searchTerm.trim().toLowerCase();
    return byStatus.filter((doc) => {
      const title = (doc.title || '').toLowerCase();
      const filename = (doc.filename || '').toLowerCase();
      return title.includes(normalizedTerm) || filename.includes(normalizedTerm);
    });
  }, [documents, filter, searchTerm]);

  useEffect(() => {
    if (!session?.user?.id) return;
    fetchDocuments();
  }, [session?.user?.id, fetchDocuments]);

  useEffect(() => {
    if (!showUploadModal) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setShowUploadModal(false);
      }
    };

    const previouslyFocused = document.activeElement as HTMLElement | null;

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    setTimeout(() => {
      fileInputRef.current?.focus();
    }, 20);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
      previouslyFocused?.focus();
    };
  }, [showUploadModal]);

  const closeModal = useCallback(() => {
    if (uploading) return;
    setShowUploadModal(false);
  }, [uploading]);

  const handleOverlayClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (
        modalRef.current &&
        !modalRef.current.contains(event.target as Node)
      ) {
        closeModal();
      }
    },
    [closeModal]
  );

  const closeSignModal = useCallback(() => {
    if (signingDocumentId) return;
    setShowSignModal(false);
    setSelectedDocument(null);
    setSignatureType("PAdES");
    setError(null);
  }, [signingDocumentId]);

  const openSignModal = useCallback((doc: Document) => {
    setSelectedDocument(doc);
    setSignatureType("PAdES");
    setShowSignModal(true);
    setError(null);
  }, []);

  const handleSignOverlayClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (
        signModalRef.current &&
        !signModalRef.current.contains(event.target as Node)
      ) {
        closeSignModal();
      }
    },
    [closeSignModal]
  );

  const handleSignDocument = useCallback(async () => {
    if (!selectedDocument) {
      setError("Selecciona un documento válido para firmar.");
      return;
    }
    const citizenIdForSign = effectiveCitizenId ?? session?.user?.citizen_id ?? null;
    if (!citizenIdForSign) {
      setError("Tu cuenta no tiene un ciudadano asociado. No es posible firmar documentos.");
      return;
    }
    setSigningDocumentId(selectedDocument.id);
    try {
      await apiService.signDocument(selectedDocument.id, {
        document_id: selectedDocument.id,
        citizen_id: citizenIdForSign,
        document_title: selectedDocument.title ?? selectedDocument.filename,
        signature_type: signatureType,
      });
      await fetchDocuments();
      closeSignModal();
    } catch (err) {
      console.error("Error signing document:", err);
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "No pudimos firmar el documento. Inténtalo nuevamente.";
      setError(message);
    } finally {
      setSigningDocumentId(null);
    }
  }, [closeSignModal, effectiveCitizenId, fetchDocuments, selectedDocument, session?.user?.citizen_id, signatureType]);

  useEffect(() => {
    if (!showSignModal) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeSignModal();
      }
    };

    const previousFocus = document.activeElement as HTMLElement | null;
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    setTimeout(() => signatureSelectRef.current?.focus(), 24);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
      previousFocus?.focus();
    };
  }, [closeSignModal, showSignModal]);

  if (status === "loading" || loading || resolvingCitizenId) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-12 w-12 animate-spin rounded-full border-2 border-primary-100 border-t-primary-500" />
          <p className="text-sm text-[var(--text-tertiary)]">
            Recuperando tus documentos...
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <PageHeader
        breadcrumbs={[
          { label: 'Inicio', href: '/dashboard' },
          { label: 'Documentos' },
        ]}
        title="Gestor de documentos"
        description="Carga, firma y consulta tus documentos oficiales en un solo lugar con la seguridad de Carpeta Ciudadana."
        actions={[
          <Button
            key="metadata"
            variant="secondary"
            icon={<FileText className="h-4 w-4" />}
            href="/documents/metadata"
          >
            Metadata
          </Button>,
          <Button
            key="upload"
            icon={<FilePlus2 className="h-4 w-4" />}
            onClick={() => setShowUploadModal(true)}
          >
            Subir documento
          </Button>,
        ]}
      />

      {error ? (
        <Card className="border-danger-200 bg-danger-100/40">
          <CardHeader>
            <CardTitle className="text-danger-600">Se produjo un error</CardTitle>
            <CardDescription className="text-danger-500">
              {error}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="ghost" onClick={fetchDocuments}>
              Intentar nuevamente
            </Button>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <StatTile
          label="Documentos cargados"
          value={documents.length}
          icon={<FileText className="h-5 w-5" />}
          tone="primary"
          helperText="Total disponibles en tu carpeta"
        />
        <StatTile
          label="Firmados"
          value={totalSigned}
          icon={<ShieldCheck className="h-5 w-5" />}
          tone="success"
          helperText="Con validez jurídica"
        />
        <StatTile
          label="Pendientes"
          value={pendingDocuments.length}
          icon={<FilePlus2 className="h-5 w-5" />}
          tone="warning"
          helperText="Requieren acción"
        />
        </div>

      <Card>
        <CardHeader className="flex flex-col gap-4 rounded-t-[var(--radius-lg)] bg-white/85 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <CardTitle>Mis documentos</CardTitle>
            <CardDescription>
              Administra tus archivos digitales y mantén su trazabilidad.
            </CardDescription>
          </div>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-4">
            <div className="flex flex-wrap gap-2">
              <Button
                variant={filter === 'all' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setFilter('all')}
              >
                Todos ({documents.length})
              </Button>
              <Button
                variant={filter === 'pending' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setFilter('pending')}
              >
                Pendientes ({pendingDocuments.length})
              </Button>
              <Button
                variant={filter === 'signed' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setFilter('signed')}
              >
                Firmados ({totalSigned})
              </Button>
          </div>
            <SearchField
              id="documents-search"
              label="Buscar documentos"
              value={searchTerm}
              onChange={setSearchTerm}
              placeholder="Buscar por título o nombre"
              className="w-full md:w-64"
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {filteredDocuments.length === 0 ? (
            <TableEmpty>
              <FilePlus2 className="h-10 w-10 text-primary-400" />
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                {filter === "pending"
                  ? "No tienes documentos pendientes por firmar"
                  : filter === "signed"
                  ? "Aún no tienes documentos firmados"
                  : "No has subido documentos todavía"}
            </h3>
              <p className="max-w-md text-sm text-[var(--text-secondary)]">
                Centraliza tus documentos digitales y firma los que necesites desde un solo lugar.
            </p>
              <Button
                variant="primary"
                icon={<FilePlus2 className="h-4 w-4" />}
              onClick={() => setShowUploadModal(true)}
              >
                Subir mi primer documento
              </Button>
            </TableEmpty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Documento</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Tamaño</TableHead>
                  <TableHead>Actualizado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDocuments.map((doc) => {
                  const statusInfo = getStatus(doc);
                  const updatedAt = new Date(doc.updated_at).toLocaleDateString("es-CO", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                  });
                  const isPendingSignature =
                    doc.status !== "signed" && doc.state !== "SIGNED" && !doc.worm_locked;

                  return (
                    <TableRow key={doc.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--primary-50)] text-[var(--primary-600)] shadow-sm">
                            <FileText className="h-5 w-5" />
                </div>
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-[var(--text-primary)]">
                              {doc.title || doc.filename}
                            </p>
                            <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">
                  {doc.filename}
                </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={statusInfo.tone === 'default' ? 'secondary' : statusInfo.tone}
                          style={statusInfo.badgeStyle}
                        >
                          {statusInfo.label}
                        </Badge>
                        {"description" in statusInfo && statusInfo.description ? (
                          <p className="mt-1 text-xs text-[var(--text-tertiary)]">
                            {statusInfo.description}
                          </p>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-sm font-medium text-[var(--text-primary)]">
                        {formatFileSize(doc.size_bytes)}
                      </TableCell>
                      <TableCell className="text-sm text-[var(--text-secondary)]">
                        {updatedAt}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Tooltip content="Descargar">
                            <Button
                              variant="ghost"
                              size="icon"
                              icon={<ArrowDownToLine className="h-4 w-4" />}
                              aria-label="Descargar documento"
                    onClick={() => handleDownload(doc.id, doc.filename)}
                            >
                              <span className="sr-only">Descargar</span>
                            </Button>
                          </Tooltip>
                          {isPendingSignature ? (
                            <Tooltip content="Firmar documento">
                              <Button
                                variant="ghost"
                                size="icon"
                                icon={<PenSquare className="h-4 w-4" />}
                                aria-label="Firmar documento"
                                onClick={() => openSignModal(doc)}
                              >
                                <span className="sr-only">Firmar</span>
                              </Button>
                            </Tooltip>
                          ) : null}
                          <Tooltip content="Eliminar">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-danger-500 hover:bg-danger-100/60"
                              icon={<Trash2 className="h-4 w-4" />}
                              aria-label="Eliminar documento"
                              onClick={() => handleDelete(doc.id)}
                            >
                              <span className="sr-only">Eliminar</span>
                            </Button>
                          </Tooltip>
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

      {showUploadModal ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6"
          role="presentation"
          onMouseDown={handleOverlayClick}
        >
          <div
            ref={modalRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="upload-title"
            aria-describedby="upload-description"
            className="relative w-full max-w-lg rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-white p-6 shadow-card focus:outline-none"
          >
                  <button
              type="button"
              onClick={closeModal}
              className="absolute right-5 top-5 inline-flex h-9 w-9 items-center justify-center rounded-full border border-[var(--border-subtle)] text-[var(--text-tertiary)] transition-colors hover:text-primary-600"
              aria-label="Cerrar modal de carga"
              disabled={uploading}
            >
              <X className="h-4 w-4" />
                  </button>

            <div className="mb-6 pr-10">
              <h2
                id="upload-title"
                className="text-2xl font-semibold text-[var(--text-primary)]"
              >
                Subir nuevo documento
              </h2>
              <p
                id="upload-description"
                className="mt-1 text-sm text-[var(--text-secondary)]"
              >
                El archivo se almacenará de forma segura y estará disponible para
                firmar y compartir.
              </p>
            </div>

            <form onSubmit={handleUpload} className="space-y-5">
              <div className="space-y-2">
                <label
                  htmlFor="file"
                  className="text-sm font-medium text-[var(--text-primary)]"
                >
                    Archivo
                  </label>
                  <input
                  ref={fileInputRef}
                  id="file"
                    type="file"
                    name="file"
                    required
                  className="block w-full rounded-[var(--radius-md)] border border-dashed border-primary-200 bg-primary-25 px-4 py-6 text-sm text-primary-600 transition hover:border-primary-300 file:hidden"
                  />
                <p className="text-xs text-[var(--text-tertiary)]">
                  Formatos compatibles: PDF, DOCX, PNG, JPG. Tamaño máximo 20 MB.
                </p>
                </div>
                
              <div className="space-y-2">
                <label
                  htmlFor="title"
                  className="text-sm font-medium text-[var(--text-primary)]"
                >
                    Título
                  </label>
                  <input
                  id="title"
                    type="text"
                    name="title"
                    required
                  placeholder="Ej: Certificado de antecedentes"
                  className="w-full rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-white px-4 py-2 text-[var(--text-primary)] focus-visible:ring-2 focus-visible:ring-primary-200"
                  />
                </div>
                
              <div className="space-y-2">
                <label
                  htmlFor="description"
                  className="text-sm font-medium text-[var(--text-primary)]"
                >
                    Descripción (opcional)
                  </label>
                  <textarea
                  id="description"
                    name="description"
                    rows={3}
                  placeholder="Añade un contexto para recordar la finalidad del documento."
                  className="w-full rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-white px-4 py-2 text-[var(--text-primary)] focus-visible:ring-2 focus-visible:ring-primary-200"
                  />
                </div>
                
              <div className="flex flex-wrap items-center justify-end gap-3 pt-2">
                <Button
                  variant="ghost"
                    type="button"
                  onClick={closeModal}
                    disabled={uploading}
                  >
                    Cancelar
                </Button>
                <Button type="submit" isLoading={uploading}>
                  {uploading ? "Subiendo..." : "Guardar documento"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {showSignModal && selectedDocument ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-6"
          onMouseDown={handleSignOverlayClick}
          role="presentation"
        >
          <div
            ref={signModalRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="sign-modal-title"
            aria-describedby="sign-modal-description"
            className="relative w-full max-w-lg rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-white p-6 shadow-card focus:outline-none"
          >
            <button
              type="button"
              onClick={closeSignModal}
              className="absolute right-5 top-5 inline-flex h-9 w-9 items-center justify-center rounded-full border border-[var(--border-subtle)] text-[var(--text-tertiary)] transition-colors hover:text-primary-600"
              aria-label="Cerrar modal de firma"
              disabled={Boolean(signingDocumentId)}
            >
              <X className="h-4 w-4" />
                  </button>
                  
            <div className="mb-6 pr-10">
              <h2
                id="sign-modal-title"
                className="text-2xl font-semibold text-[var(--text-primary)]"
              >
                Firmar documento
              </h2>
              <p
                id="sign-modal-description"
                className="mt-1 text-sm text-[var(--text-secondary)]"
              >
                Confirma el tipo de firma que deseas aplicar al documento seleccionado.
              </p>
            </div>

            <div className="space-y-5">
              <div>
                <label className="text-sm font-medium text-[var(--text-primary)]">
                  Documento
                </label>
                <p className="mt-1 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-muted)] px-3 py-2 text-sm text-[var(--text-primary)]">
                  {selectedDocument.title || selectedDocument.filename}
                </p>
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="signature-type"
                  className="text-sm font-medium text-[var(--text-primary)]"
                >
                  Tipo de firma
                </label>
                <select
                  ref={signatureSelectRef}
                  id="signature-type"
                  value={signatureType}
                  onChange={(event) =>
                    setSignatureType(event.target.value as SignatureType)
                  }
                  className="w-full rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-white px-4 py-2 text-[var(--text-primary)] focus-visible:ring-2 focus-visible:ring-primary-200"
                >
                  <option value="PAdES">
                    PAdES — Firma avanzada para documentos PDF
                  </option>
                  <option value="XAdES">
                    XAdES — Firma avanzada para contenidos XML
                  </option>
                  <option value="CAdES">
                    CAdES — Firma avanzada basada en CMS
                  </option>
                </select>
                <p className="text-xs text-[var(--text-tertiary)]">
                  PAdES es el estándar recomendado para documentos PDF oficiales.
                </p>
              </div>
                </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <Button
                variant="ghost"
                type="button"
                onClick={closeSignModal}
                disabled={Boolean(signingDocumentId)}
              >
                Cancelar
              </Button>
              <Button
                onClick={handleSignDocument}
                isLoading={signingDocumentId === selectedDocument.id}
                disabled={Boolean(signingDocumentId)}
              >
                {signingDocumentId === selectedDocument.id ? "Firmando..." : "Firmar"}
              </Button>
            </div>
          </div>
      </div>
      ) : null}
    </>
  );
}

function DocumentsPageFallback() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-12 w-12 animate-spin rounded-full border-2 border-primary-100 border-t-primary-500" />
        <p className="text-sm text-[var(--text-tertiary)]">
          Cargando documentos...
        </p>
      </div>
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <Suspense fallback={<DocumentsPageFallback />}>
      <DocumentsPageContent />
    </Suspense>
  );
}
