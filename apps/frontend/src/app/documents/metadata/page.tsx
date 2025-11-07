"use client";

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { apiService } from '@/lib/api';

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

export default function MetadataPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [metadata, setMetadata] = useState<DocumentMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'signed' | 'unsigned' | 'worm_locked'>('all');
  const [sortBy, setSortBy] = useState<'created_at' | 'updated_at' | 'title'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    if (session?.user?.id) {
      fetchMetadata();
    }
  }, [session, filter, sortBy, sortOrder]);

  const fetchMetadata = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const citizenId = session?.user?.id || '1234567890';
      const data = await apiService.getDocumentMetadata(citizenId);
      
      // Ensure data is an array
      const dataArray = Array.isArray(data) ? data : [];
      
      // Filter data
      let filtered = dataArray;
      if (filter === 'signed') {
        filtered = dataArray.filter((doc: DocumentMetadata) => 
          doc.state === 'SIGNED' || doc.status === 'signed'
        );
      } else if (filter === 'unsigned') {
        filtered = dataArray.filter((doc: DocumentMetadata) => 
          doc.state !== 'SIGNED' && doc.status !== 'signed'
        );
      } else if (filter === 'worm_locked') {
        filtered = dataArray.filter((doc: DocumentMetadata) => doc.worm_locked);
      }
      
      // Sort data - ensure filtered is an array before sorting
      if (!Array.isArray(filtered)) {
        filtered = [];
      }
      
      filtered.sort((a: DocumentMetadata, b: DocumentMetadata) => {
        let aValue: any;
        let bValue: any;
        
        if (sortBy === 'created_at') {
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
        } else if (sortBy === 'updated_at') {
          aValue = new Date(a.updated_at || a.created_at).getTime();
          bValue = new Date(b.updated_at || b.created_at).getTime();
        } else {
          aValue = (a.title || a.filename).toLowerCase();
          bValue = (b.title || b.filename).toLowerCase();
        }
        
        if (sortOrder === 'asc') {
          return aValue > bValue ? 1 : -1;
        } else {
          return aValue < bValue ? 1 : -1;
        }
      });
      
      setMetadata(filtered);
    } catch (error) {
      console.error('Error fetching metadata:', error);
      setError('Error al cargar los metadatos');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A';
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  const getStateBadge = (state: string) => {
    switch (state) {
      case 'SIGNED':
        return <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">Firmado</span>;
      case 'UNSIGNED':
        return <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">Sin Firmar</span>;
      default:
        return <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">{state}</span>;
    }
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Cargando metadatos...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            📊 Metadata de Documentos
          </h1>
          <p className="mt-2 text-gray-600">
            Información detallada de tus documentos digitales
          </p>
        </div>

        {/* Filters and Sort */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-center">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Filtro
              </label>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as any)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">Todos</option>
                <option value="signed">Firmados</option>
                <option value="unsigned">Sin Firmar</option>
                <option value="worm_locked">WORM Locked</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Ordenar por
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="created_at">Fecha de Creación</option>
                <option value="updated_at">Fecha de Actualización</option>
                <option value="title">Título</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Orden
              </label>
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as any)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="desc">Descendente</option>
                <option value="asc">Ascendente</option>
              </select>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Metadata List */}
        {metadata.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <div className="text-6xl mb-4">📊</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No hay metadatos disponibles
            </h3>
            <p className="text-gray-600">
              No se encontraron documentos con metadatos
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Documento
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Estado
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tamaño
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      WORM
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Retención
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Fechas
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {metadata.map((doc) => (
                    <tr key={doc.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {doc.title || doc.filename}
                          </div>
                          <div className="text-sm text-gray-500">
                            {doc.filename}
                          </div>
                          {doc.sha256_hash && (
                            <div className="text-xs text-gray-400 font-mono">
                              {doc.sha256_hash.substring(0, 16)}...
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="space-y-1">
                          {getStateBadge(doc.state)}
                          <div className="text-xs text-gray-500">
                            {doc.is_uploaded ? '✅ Subido' : '⏳ Pendiente'}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatFileSize(doc.size_bytes)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {doc.worm_locked ? (
                          <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">
                            🔒 Bloqueado
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">No bloqueado</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {doc.retention_until ? (
                          <div>
                            <div>Hasta: {formatDate(doc.retention_until)}</div>
                            {doc.state === 'SIGNED' && (
                              <div className="text-xs text-green-600">Eterno</div>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-400">Sin retención</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div>Creado: {formatDate(doc.created_at)}</div>
                        {doc.updated_at && (
                          <div>Actualizado: {formatDate(doc.updated_at)}</div>
                        )}
                        {doc.signed_at && (
                          <div className="text-green-600">Firmado: {formatDate(doc.signed_at)}</div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

