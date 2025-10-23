"use client";

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { apiService } from '@/lib/api';

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

export default function TransfersPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [activeTab, setActiveTab] = useState<'sent' | 'received'>('sent');

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
      
      // Filter transfers based on active tab
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

  const handleCreateTransfer = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreating(true);
    
    try {
      const formData = new FormData(event.currentTarget);
      const transferData = {
        document_id: formData.get('document_id') as string,
        to_email: formData.get('to_email') as string,
        message: formData.get('message') as string,
      };

      await apiService.createTransfer(transferData);
      setShowCreateModal(false);
      await fetchTransfers(); // Refresh the list
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
      await fetchTransfers(); // Refresh the list
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
      await fetchTransfers(); // Refresh the list
    } catch (error) {
      console.error('Error rejecting transfer:', error);
      setError('Error al rechazar la transferencia');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">⏳ Pendiente</span>;
      case 'accepted':
        return <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">✅ Aceptada</span>;
      case 'rejected':
        return <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">❌ Rechazada</span>;
      case 'expired':
        return <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">⏰ Expirada</span>;
      default:
        return <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">{status}</span>;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Cargando transferencias...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              🔄 Transferencias
            </h1>
            <p className="mt-2 text-gray-600">
              Envía y recibe documentos digitales
            </p>
          </div>
          
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            📤 Nueva Transferencia
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('sent')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'sent'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                📤 Enviadas ({transfers.filter(t => t.from_citizen_id === session?.user?.id).length})
              </button>
              <button
                onClick={() => setActiveTab('received')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'received'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                📥 Recibidas ({transfers.filter(t => t.to_citizen_id === session?.user?.id).length})
              </button>
            </nav>
          </div>
        </div>

        {/* Transfers List */}
        {transfers.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <div className="text-6xl mb-4">
              {activeTab === 'sent' ? '📤' : '📥'}
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              {activeTab === 'sent' ? 'No has enviado transferencias' : 'No has recibido transferencias'}
            </h3>
            <p className="text-gray-600 mb-6">
              {activeTab === 'sent' 
                ? 'Envía documentos a otros usuarios para comenzar' 
                : 'Las transferencias que recibas aparecerán aquí'
              }
            </p>
            {activeTab === 'sent' && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
              >
                📤 Crear Primera Transferencia
              </button>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="divide-y divide-gray-200">
              {transfers.map((transfer) => (
                <div key={transfer.id} className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">
                          {transfer.document_title}
                        </h3>
                        {getStatusBadge(transfer.status)}
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
                        <div>
                          <span className="font-medium">
                            {activeTab === 'sent' ? 'Para:' : 'De:'}
                          </span>{' '}
                          {activeTab === 'sent' ? transfer.to_email : transfer.from_citizen_id}
                        </div>
                        
                        <div>
                          <span className="font-medium">Creada:</span>{' '}
                          {formatDate(transfer.created_at)}
                        </div>
                        
                        {transfer.expires_at && (
                          <div>
                            <span className="font-medium">Expira:</span>{' '}
                            {formatDate(transfer.expires_at)}
                          </div>
                        )}
                        
                        {transfer.message && (
                          <div className="md:col-span-2">
                            <span className="font-medium">Mensaje:</span>{' '}
                            {transfer.message}
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {/* Action Buttons */}
                    <div className="flex gap-2 ml-4">
                      {activeTab === 'received' && transfer.status === 'pending' && (
                        <>
                          <button
                            onClick={() => handleAcceptTransfer(transfer.id)}
                            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                          >
                            ✅ Aceptar
                          </button>
                          <button
                            onClick={() => handleRejectTransfer(transfer.id)}
                            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                          >
                            ❌ Rechazar
                          </button>
                        </>
                      )}
                      
                      {transfer.status === 'accepted' && (
                        <button
                          onClick={() => router.push(`/documents?highlight=${transfer.document_id}`)}
                          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                        >
                          📄 Ver Documento
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Create Transfer Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-md w-full p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                📤 Nueva Transferencia
              </h2>
              
              <form onSubmit={handleCreateTransfer} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Documento
                  </label>
                  <select
                    name="document_id"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">Selecciona un documento...</option>
                    {/* TODO: Load user's documents */}
                    <option value="doc1">Cédula de Ciudadanía</option>
                    <option value="doc2">Diploma Universitario</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Email del destinatario
                  </label>
                  <input
                    type="email"
                    name="to_email"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="usuario@ejemplo.com"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Mensaje (opcional)
                  </label>
                  <textarea
                    name="message"
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Mensaje para el destinatario..."
                  />
                </div>
                
                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
                    disabled={creating}
                  >
                    Cancelar
                  </button>
                  
                  <button
                    type="submit"
                    disabled={creating}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors disabled:opacity-50"
                  >
                    {creating ? 'Enviando...' : 'Enviar'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
