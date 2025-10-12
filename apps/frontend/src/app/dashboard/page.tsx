"use client";

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';

interface Activity {
  id: string;
  type: 'upload' | 'sign' | 'transfer' | 'share' | 'download';
  title: string;
  description: string;
  timestamp: string;
  status: 'success' | 'pending' | 'failed';
  link?: string;
}

interface Stats {
  totalDocuments: number;
  signedDocuments: number;
  pendingTransfers: number;
  sharedDocuments: number;
}

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [stats, setStats] = useState<Stats>({
    totalDocuments: 0,
    signedDocuments: 0,
    pendingTransfers: 0,
    sharedDocuments: 0,
  });
  const [loading, setLoading] = useState(true);
  const [timeFilter, setTimeFilter] = useState<'today' | 'week' | 'month' | 'all'>('week');

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    fetchDashboardData();
  }, [timeFilter]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      // TODO: Replace with actual API calls
      
      // Mock stats
      setStats({
        totalDocuments: 24,
        signedDocuments: 18,
        pendingTransfers: 3,
        sharedDocuments: 7,
      });

      // Mock activities
      const mockActivities: Activity[] = [
        {
          id: '1',
          type: 'sign',
          title: 'Documento firmado',
          description: 'Cédula.pdf fue firmado exitosamente',
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          status: 'success',
          link: '/documents'
        },
        {
          id: '2',
          type: 'transfer',
          title: 'Transferencia enviada',
          description: 'Diploma.pdf enviado a juan@example.com',
          timestamp: new Date(Date.now() - 7200000).toISOString(),
          status: 'pending',
          link: '/transfers'
        },
        {
          id: '3',
          type: 'upload',
          title: 'Documento cargado',
          description: 'Certificado_Laboral.pdf subido correctamente',
          timestamp: new Date(Date.now() - 10800000).toISOString(),
          status: 'success',
          link: '/documents'
        },
        {
          id: '4',
          type: 'share',
          title: 'Documento compartido',
          description: 'Compartiste Acta_Nacimiento.pdf vía shortlink',
          timestamp: new Date(Date.now() - 14400000).toISOString(),
          status: 'success',
          link: '/documents'
        },
        {
          id: '5',
          type: 'download',
          title: 'Descarga realizada',
          description: 'Descargaste Certificado_Estudios.pdf',
          timestamp: new Date(Date.now() - 18000000).toISOString(),
          status: 'success'
        },
        {
          id: '6',
          type: 'transfer',
          title: 'Transferencia recibida',
          description: 'Recibiste Contrato.pdf de maria@example.com',
          timestamp: new Date(Date.now() - 86400000).toISOString(),
          status: 'success',
          link: '/transfers'
        },
      ];

      setActivities(mockActivities);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getActivityIcon = (type: Activity['type']) => {
    switch (type) {
      case 'upload': return '⬆️';
      case 'sign': return '✍️';
      case 'transfer': return '🔄';
      case 'share': return '🔗';
      case 'download': return '⬇️';
      default: return '📄';
    }
  };

  const getStatusBadge = (status: Activity['status']) => {
    switch (status) {
      case 'success':
        return <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">✓ Exitoso</span>;
      case 'pending':
        return <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">⏳ Pendiente</span>;
      case 'failed':
        return <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">✗ Fallido</span>;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'Hace un momento';
    if (minutes < 60) return `Hace ${minutes} minuto${minutes > 1 ? 's' : ''}`;
    if (hours < 24) return `Hace ${hours} hora${hours > 1 ? 's' : ''}`;
    if (days < 7) return `Hace ${days} día${days > 1 ? 's' : ''}`;
    
    return date.toLocaleDateString('es-ES', { 
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
          <p className="mt-4 text-gray-600">Cargando dashboard...</p>
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
            📊 Dashboard
          </h1>
          <p className="mt-2 text-gray-600">
            Bienvenido, {session?.user?.name || 'Usuario'}
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total Documentos</p>
                <p className="text-3xl font-bold text-gray-900">{stats.totalDocuments}</p>
              </div>
              <div className="text-4xl">📄</div>
            </div>
            <div className="mt-4">
              <button
                onClick={() => router.push('/documents')}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                Ver todos →
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Firmados</p>
                <p className="text-3xl font-bold text-green-600">{stats.signedDocuments}</p>
              </div>
              <div className="text-4xl">✅</div>
            </div>
            <div className="mt-4">
              <div className="text-sm text-gray-600">
                {((stats.signedDocuments / stats.totalDocuments) * 100).toFixed(0)}% del total
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Transferencias</p>
                <p className="text-3xl font-bold text-orange-600">{stats.pendingTransfers}</p>
              </div>
              <div className="text-4xl">🔄</div>
            </div>
            <div className="mt-4">
              <button
                onClick={() => router.push('/transfers')}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                Ver pendientes →
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Compartidos</p>
                <p className="text-3xl font-bold text-purple-600">{stats.sharedDocuments}</p>
              </div>
              <div className="text-4xl">🔗</div>
            </div>
            <div className="mt-4">
              <div className="text-sm text-gray-600">
                Activos y accesibles
              </div>
            </div>
          </div>
        </div>

        {/* Activity Timeline */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">
                ⏱️ Actividad Reciente
              </h2>
              
              <div className="flex gap-2">
                {['today', 'week', 'month', 'all'].map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setTimeFilter(filter as any)}
                    className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                      timeFilter === filter
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {filter === 'today' && 'Hoy'}
                    {filter === 'week' && 'Semana'}
                    {filter === 'month' && 'Mes'}
                    {filter === 'all' && 'Todo'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="p-6">
            {activities.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">📭</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  No hay actividad reciente
                </h3>
                <p className="text-gray-600">
                  Tus acciones aparecerán aquí
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {activities.map((activity, index) => (
                  <div key={activity.id} className="flex items-start gap-4">
                    {/* Timeline Line */}
                    <div className="relative flex flex-col items-center">
                      <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-xl">
                        {getActivityIcon(activity.type)}
                      </div>
                      {index < activities.length - 1 && (
                        <div className="w-0.5 h-16 bg-gray-200 mt-2"></div>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold text-gray-900">
                              {activity.title}
                            </h3>
                            {getStatusBadge(activity.status)}
                          </div>
                          
                          <p className="text-gray-600 mb-2">
                            {activity.description}
                          </p>
                          
                          <div className="flex items-center gap-4 text-sm text-gray-500">
                            <span>🕒 {formatTimestamp(activity.timestamp)}</span>
                            
                            {activity.link && (
                              <button
                                onClick={() => router.push(activity.link!)}
                                className="text-blue-600 hover:text-blue-800 font-medium"
                              >
                                Ver detalles →
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
          <button
            onClick={() => router.push('/documents')}
            className="bg-white border-2 border-blue-600 rounded-lg p-6 hover:bg-blue-50 transition-colors text-left"
          >
            <div className="text-3xl mb-3">📤</div>
            <h3 className="font-semibold text-gray-900 mb-2">Subir Documento</h3>
            <p className="text-sm text-gray-600">Carga un nuevo documento a tu carpeta</p>
          </button>

          <button
            onClick={() => router.push('/transfers')}
            className="bg-white border-2 border-green-600 rounded-lg p-6 hover:bg-green-50 transition-colors text-left"
          >
            <div className="text-3xl mb-3">🔄</div>
            <h3 className="font-semibold text-gray-900 mb-2">Transferir</h3>
            <p className="text-sm text-gray-600">Envía documentos a otros usuarios</p>
          </button>

          <button
            onClick={() => router.push('/notifications')}
            className="bg-white border-2 border-purple-600 rounded-lg p-6 hover:bg-purple-50 transition-colors text-left"
          >
            <div className="text-3xl mb-3">🔔</div>
            <h3 className="font-semibold text-gray-900 mb-2">Notificaciones</h3>
            <p className="text-sm text-gray-600">Revisa tus notificaciones recientes</p>
          </button>
        </div>
      </div>
    </div>
  );
}
