'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { api } from '@/lib/api';
import { FileText, Download, Share2, Trash2 } from 'lucide-react';

interface Document {
  id: string;
  title: string;
  description?: string;
  filename: string;
  content_type: string;
  size: number;
  status: string;
  created_at: string;
}

export default function DocumentsPage() {
  const router = useRouter();
  const { isAuthenticated, user } = useAuthStore();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadDocuments = useCallback(async () => {
    try {
      // Call metadata service to get citizen's documents
      const response = await api.get(`/api/metadata/documents?citizen_id=${user?.id}`);
      setDocuments(response.data.documents || []);
    } catch (err) {
      console.error('Error loading documents:', err);
      setError('Error al cargar documentos');
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    loadDocuments();
  }, [isAuthenticated, router, loadDocuments]);

  const handleDownload = async (documentId: string) => {
    try {
      // Get presigned download URL
      const response = await api.post('/api/documents/download-url', {
        document_id: documentId,
      });
      
      // Open download URL in new tab
      window.open(response.data.download_url, '_blank');
    } catch (err) {
      alert('Error al descargar documento');
      console.error('Download error:', err);
    }
  };

  const handleShare = (documentId: string) => {
    router.push(`/share?document=${documentId}`);
  };

  const handleDelete = async (documentId: string) => {
    if (!confirm('¿Estás seguro de eliminar este documento?')) {
      return;
    }

    try {
      await api.delete(`/api/metadata/documents/${documentId}`);
      // Reload documents after deletion
      await loadDocuments();
    } catch (err) {
      alert('Error al eliminar documento');
      console.error('Delete error:', err);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-CO', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'authenticated':
        return 'bg-green-100 text-green-800';
      case 'signed':
        return 'bg-blue-100 text-blue-800';
      case 'uploaded':
        return 'bg-gray-100 text-gray-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Mis Documentos</h1>
          <div className="flex gap-4">
            <button
              onClick={() => router.push('/upload')}
              className="btn-primary"
            >
              Subir Documento
            </button>
            <button
              onClick={() => router.push('/dashboard')}
              className="btn-secondary"
            >
              Volver
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-600">Cargando documentos...</p>
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-16 h-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">
              No tienes documentos
            </h3>
            <p className="text-gray-600 mb-6">
              Comienza subiendo tu primer documento
            </p>
            <button
              onClick={() => router.push('/upload')}
              className="btn-primary"
            >
              Subir Documento
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6">
            {documents.map((doc) => (
              <div key={doc.id} className="card">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    <FileText className="w-12 h-12 text-blue-600 flex-shrink-0" />
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {doc.title}
                      </h3>
                      {doc.description && (
                        <p className="text-gray-600 mt-1">{doc.description}</p>
                      )}
                      <div className="flex flex-wrap gap-4 mt-2 text-sm text-gray-500">
                        <span>{doc.filename}</span>
                        <span>{formatSize(doc.size)}</span>
                        <span>{formatDate(doc.created_at)}</span>
                      </div>
                      <div className="mt-2">
                        <span
                          className={`inline-block px-3 py-1 rounded-full text-sm ${getStatusColor(
                            doc.status
                          )}`}
                        >
                          {doc.status}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => handleDownload(doc.id)}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                      title="Descargar"
                    >
                      <Download className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => handleShare(doc.id)}
                      className="p-2 text-green-600 hover:bg-green-50 rounded"
                      title="Compartir"
                    >
                      <Share2 className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded"
                      title="Eliminar"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

