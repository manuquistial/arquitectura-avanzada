"use client";

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { apiService } from '@/lib/api';
import type { SignDocumentRequest } from '@/types/api';

interface Document {
  id: string;
  title: string;
  filename: string;
  content_type: string;
  status: string;
  state?: string;  // 'SIGNED' or 'UNSIGNED'
  worm_locked?: boolean;
  signed_at?: string;
  created_at: string;
}

export default function SignDocumentPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [signing, setSigning] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [showSignModal, setShowSignModal] = useState(false);
  const [signatureType, setSignatureType] = useState<"PAdES" | "XAdES" | "CAdES">("PAdES");

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    if (session?.user?.id) {
      fetchDocuments();
    }
  }, [session]);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const citizenId = session?.user?.id || '1234567890';
      const data = await apiService.getDocuments(citizenId, session?.user?.roles);
      
      // Filter only unsigned documents (not signed and not WORM-locked)
      const unsignedDocs = data.filter((doc: Document) => 
        doc.status !== 'signed' && doc.state !== 'SIGNED' && !doc.worm_locked
      );
      
      setDocuments(unsignedDocs);
    } catch (error) {
      console.error('Error fetching documents:', error);
      setError('Error al cargar los documentos');
    } finally {
      setLoading(false);
    }
  };

  const handleSignDocument = async () => {
    if (!selectedDocument || !session?.user?.id) {
      setError('Documento o usuario no válido');
      return;
    }

    setSigning(selectedDocument.id);
    setError(null);

    try {
      const signatureData: SignDocumentRequest = {
        document_id: selectedDocument.id,
        citizen_id: session.user.id,
        signature_type: signatureType,
        document_title: selectedDocument.title || selectedDocument.filename,
      };

      await apiService.signDocument(selectedDocument.id, signatureData);
      
      // Success - refresh documents list
      await fetchDocuments();
      setShowSignModal(false);
      setSelectedDocument(null);
    } catch (err) {
      console.error('Error signing document:', err);
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Error al firmar el documento');
    } finally {
      setSigning(null);
    }
  };

  const openSignModal = (doc: Document) => {
    setSelectedDocument(doc);
    setShowSignModal(true);
    setError(null);
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Cargando documentos...</p>
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
            ✍️ Firmar Documentos
          </h1>
          <p className="mt-2 text-gray-600">
            Selecciona un documento para firmarlo digitalmente
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Documents List */}
        {documents.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <div className="text-6xl mb-4">📝</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No hay documentos para firmar
            </h3>
            <p className="text-gray-600 mb-6">
              Todos tus documentos ya están firmados o no tienes documentos
            </p>
            <button
              onClick={() => router.push('/documents')}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
            >
              Ver Mis Documentos
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {documents.map((doc) => (
              <div key={doc.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-4">
                  <div className="text-3xl">📄</div>
                  <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">
                    Sin Firmar
                  </span>
                </div>
                
                <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2">
                  {doc.title || doc.filename}
                </h3>
                
                <p className="text-sm text-gray-600 mb-2">
                  {doc.filename}
                </p>
                
                <p className="text-xs text-gray-500 mb-4">
                  {new Date(doc.created_at).toLocaleDateString('es-ES')}
                </p>
                
                <button
                  onClick={() => openSignModal(doc)}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  ✍️ Firmar Documento
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Sign Modal */}
        {showSignModal && selectedDocument && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-md w-full p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                ✍️ Firmar Documento
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Documento
                  </label>
                  <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">
                    {selectedDocument.title || selectedDocument.filename}
                  </p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Tipo de Firma
                  </label>
                  <select
                    value={signatureType}
                    onChange={(e) => setSignatureType(e.target.value as "PAdES" | "XAdES" | "CAdES")}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="PAdES">PAdES (PDF Advanced Electronic Signature)</option>
                    <option value="XAdES">XAdES (XML Advanced Electronic Signature)</option>
                    <option value="CAdES">CAdES (CMS Advanced Electronic Signature)</option>
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    PAdES es recomendado para documentos PDF
                  </p>
                </div>
                
                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-600 px-3 py-2 rounded text-sm">
                    {error}
                  </div>
                )}
                
                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowSignModal(false);
                      setSelectedDocument(null);
                      setError(null);
                    }}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
                    disabled={signing !== null}
                  >
                    Cancelar
                  </button>
                  
                  <button
                    onClick={handleSignDocument}
                    disabled={signing !== null}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors disabled:opacity-50"
                  >
                    {signing === selectedDocument.id ? 'Firmando...' : 'Firmar'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

