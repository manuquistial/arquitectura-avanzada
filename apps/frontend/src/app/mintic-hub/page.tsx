"use client";

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { apiService } from '@/lib/api';

interface SyncStatus {
  citizen_id: string;
  last_sync: string;
  sync_status: string;
  documents_synced: number;
  pending_sync: number;
  last_error?: string;
  next_sync?: string;
}

interface Operator {
  id: string;
  name: string;
  status: string;
  description?: string;
}

export default function MinTICHubPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [operators, setOperators] = useState<Operator[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<any>(null);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    if (session?.user?.id) {
      fetchData();
    }
  }, [session]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [syncData, operatorsData] = await Promise.all([
        apiService.getSyncStatus(session?.user?.id || ''),
        apiService.getOperators()
      ]);
      
      setSyncStatus(syncData);
      setOperators(operatorsData);
    } catch (error) {
      console.error('Error fetching MinTIC Hub data:', error);
      setError('Error al cargar datos del MinTIC Hub');
    } finally {
      setLoading(false);
    }
  };

  const handleSyncDocuments = async (syncType = 'full') => {
    try {
      setSyncing(true);
      setError(null);
      
      const result = await apiService.syncDocumentsWithHub(
        session?.user?.id || '',
        undefined, // Sync all documents
        syncType
      );
      
      setSyncResult(result);
      
      // Refresh sync status
      await fetchData();
    } catch (error) {
      console.error('Error syncing documents:', error);
      setError('Error al sincronizar documentos con MinTIC Hub');
    } finally {
      setSyncing(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('es-ES');
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'synced':
        return <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">✅ Sincronizado</span>;
      case 'pending':
        return <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">⏳ Pendiente</span>;
      case 'error':
        return <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">❌ Error</span>;
      case 'syncing':
        return <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">🔄 Sincronizando</span>;
      default:
        return <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">{status}</span>;
    }
  };

  const getOperatorStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">✅ Activo</span>;
      case 'inactive':
        return <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">❌ Inactivo</span>;
      case 'maintenance':
        return <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">🔧 Mantenimiento</span>;
      default:
        return <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">{status}</span>;
    }
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Cargando datos del MinTIC Hub...</p>
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
            🏛️ MinTIC Hub
          </h1>
          <p className="mt-2 text-gray-600">
            Integración con el ecosistema gubernamental de documentos digitales
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Sync Result */}
        {syncResult && (
          <div className="mb-6 bg-green-50 border border-green-200 text-green-600 px-4 py-3 rounded">
            <div className="font-medium">Sincronización completada</div>
            <div className="text-sm mt-1">
              Documentos sincronizados: {syncResult.synced_documents} | 
              Fallidos: {syncResult.failed_documents}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Sync Status */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">
                📊 Estado de Sincronización
              </h2>
              <div className="flex gap-2">
                <button
                  onClick={() => handleSyncDocuments('incremental')}
                  disabled={syncing}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {syncing ? 'Sincronizando...' : 'Sincronizar Incremental'}
                </button>
                <button
                  onClick={() => handleSyncDocuments('full')}
                  disabled={syncing}
                  className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {syncing ? 'Sincronizando...' : 'Sincronización Completa'}
                </button>
              </div>
            </div>

            {syncStatus ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Estado</p>
                    <div className="mt-1">{getStatusBadge(syncStatus.sync_status)}</div>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Última Sincronización</p>
                    <p className="text-sm font-medium">{formatDate(syncStatus.last_sync)}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Documentos Sincronizados</p>
                    <p className="text-2xl font-bold text-green-600">{syncStatus.documents_synced}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Pendientes</p>
                    <p className="text-2xl font-bold text-yellow-600">{syncStatus.pending_sync}</p>
                  </div>
                </div>

                {syncStatus.last_error && (
                  <div className="bg-red-50 border border-red-200 rounded p-3">
                    <p className="text-sm font-medium text-red-800">Último Error</p>
                    <p className="text-sm text-red-600">{syncStatus.last_error}</p>
                  </div>
                )}

                {syncStatus.next_sync && (
                  <div className="bg-blue-50 border border-blue-200 rounded p-3">
                    <p className="text-sm font-medium text-blue-800">Próxima Sincronización</p>
                    <p className="text-sm text-blue-600">{formatDate(syncStatus.next_sync)}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="text-4xl mb-4">📡</div>
                <p className="text-gray-600">No hay datos de sincronización disponibles</p>
                <button
                  onClick={() => handleSyncDocuments('full')}
                  disabled={syncing}
                  className="mt-4 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  {syncing ? 'Sincronizando...' : 'Iniciar Sincronización'}
                </button>
              </div>
            )}
          </div>

          {/* Operators */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              🏢 Operadores Disponibles
            </h2>

            {operators.length > 0 ? (
              <div className="space-y-3">
                {operators.map((operator) => (
                  <div key={operator.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-gray-900">{operator.name}</h3>
                        {getOperatorStatusBadge(operator.status)}
                      </div>
                      {operator.description && (
                        <p className="text-sm text-gray-600 mt-1">{operator.description}</p>
                      )}
                    </div>
                    <div className="text-xs text-gray-500">
                      ID: {operator.id}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="text-4xl mb-4">🏢</div>
                <p className="text-gray-600">No hay operadores disponibles</p>
              </div>
            )}
          </div>
        </div>

        {/* Integration Features */}
        <div className="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            🔗 Funcionalidades de Integración
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-3xl mb-2">📄</div>
              <h3 className="font-medium text-gray-900 mb-2">Autenticación de Documentos</h3>
              <p className="text-sm text-gray-600">
                Validación oficial de documentos con MinTIC Hub
              </p>
            </div>

            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-3xl mb-2">🔄</div>
              <h3 className="font-medium text-gray-900 mb-2">Sincronización Automática</h3>
              <p className="text-sm text-gray-600">
                Sincronización bidireccional de documentos
              </p>
            </div>

            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-3xl mb-2">🔒</div>
              <h3 className="font-medium text-gray-900 mb-2">Seguridad Gubernamental</h3>
              <p className="text-sm text-gray-600">
                Cumplimiento con estándares de seguridad gubernamental
              </p>
            </div>
          </div>
        </div>

        {/* Help Section */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">
            ℹ️ Información sobre MinTIC Hub
          </h3>
          <div className="text-sm text-blue-800 space-y-2">
            <p>
              MinTIC Hub es el ecosistema gubernamental que permite la interoperabilidad 
              de documentos digitales entre diferentes entidades del Estado.
            </p>
            <p>
              <strong>Beneficios:</strong> Autenticación oficial, transferencias seguras, 
              y cumplimiento normativo para documentos gubernamentales.
            </p>
            <p>
              <strong>Frecuencia de sincronización:</strong> Se recomienda sincronizar 
              al menos una vez al día para mantener los documentos actualizados.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
