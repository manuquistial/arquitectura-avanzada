"use client";

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { apiService } from '@/lib/api';

interface Notification {
  id: string;
  citizen_id: string;
  type: string;
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  metadata?: any;
}

export default function NotificationsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'unread' | 'read'>('all');
  const [stats, setStats] = useState({ total_notifications: 0 });

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    if (session?.user?.id) {
      fetchData();
    }
  }, [session, filter]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const citizenId = session?.user?.id || '1234567890';
      
      // Fetch notifications and stats
      const [notifData, statsData] = await Promise.all([
        apiService.getUserNotifications(citizenId),
        apiService.getNotificationStats()
      ]);
      
      // Filter notifications
      let filtered = Array.isArray(notifData) ? notifData : [];
      if (filter === 'unread') {
        filtered = filtered.filter((n: Notification) => !n.read);
      } else if (filter === 'read') {
        filtered = filtered.filter((n: Notification) => n.read);
      }
      
      // Sort by created_at (most recent first)
      filtered.sort((a: Notification, b: Notification) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      
      setNotifications(filtered);
      setStats(statsData || { total_notifications: 0 });
    } catch (error) {
      console.error('Error fetching notifications:', error);
      setError('Error al cargar las notificaciones');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'document_signed':
        return '✍️';
      case 'document_uploaded':
        return '📄';
      case 'transfer_received':
        return '📥';
      case 'transfer_sent':
        return '📤';
      case 'document_shared':
        return '🔗';
      default:
        return '🔔';
    }
  };

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'document_signed':
        return 'bg-green-100 text-green-800';
      case 'document_uploaded':
        return 'bg-blue-100 text-blue-800';
      case 'transfer_received':
        return 'bg-purple-100 text-purple-800';
      case 'transfer_sent':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Cargando notificaciones...</p>
        </div>
      </div>
    );
  }

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              🔔 Notificaciones
            </h1>
            <p className="mt-2 text-gray-600">
              Gestiona tus notificaciones y alertas
            </p>
          </div>
          
          <div className="text-right">
            <div className="text-sm text-gray-500">Total</div>
            <div className="text-2xl font-bold text-gray-900">
              {stats.total_notifications || notifications.length}
            </div>
            {unreadCount > 0 && (
              <div className="text-sm text-blue-600 font-medium">
                {unreadCount} sin leer
              </div>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex gap-4">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${
                filter === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Todas ({notifications.length})
            </button>
            <button
              onClick={() => setFilter('unread')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${
                filter === 'unread'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Sin Leer ({unreadCount})
            </button>
            <button
              onClick={() => setFilter('read')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${
                filter === 'read'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Leídas ({notifications.length - unreadCount})
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Notifications List */}
        {notifications.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <div className="text-6xl mb-4">🔔</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              {filter === 'unread' ? 'No hay notificaciones sin leer' : 'No hay notificaciones'}
            </h3>
            <p className="text-gray-600">
              {filter === 'unread' 
                ? 'Todas tus notificaciones han sido leídas' 
                : 'No tienes notificaciones en este momento'
              }
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {notifications.map((notification) => (
              <div
                key={notification.id}
                className={`bg-white rounded-lg shadow-sm border ${
                  notification.read 
                    ? 'border-gray-200' 
                    : 'border-blue-300 bg-blue-50'
                } p-6 hover:shadow-md transition-shadow`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    <div className={`text-3xl ${notification.read ? 'opacity-50' : ''}`}>
                      {getNotificationIcon(notification.type)}
                    </div>
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className={`font-semibold ${notification.read ? 'text-gray-700' : 'text-gray-900'}`}>
                          {notification.title}
                        </h3>
                        {!notification.read && (
                          <span className="px-2 py-1 text-xs font-medium bg-blue-600 text-white rounded-full">
                            Nuevo
                          </span>
                        )}
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getNotificationColor(notification.type)}`}>
                          {notification.type}
                        </span>
                      </div>
                      
                      <p className={`text-sm mb-3 ${notification.read ? 'text-gray-600' : 'text-gray-700'}`}>
                        {notification.message}
                      </p>
                      
                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span>{formatDate(notification.created_at)}</span>
                        {notification.metadata && (
                          <span className="text-gray-400">
                            {JSON.stringify(notification.metadata)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {!notification.read && (
                    <button
                      onClick={() => {
                        // TODO: Implementar marcar como leída
                        console.log('Marcar como leída:', notification.id);
                      }}
                      className="ml-4 px-3 py-1 text-sm font-medium text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors"
                    >
                      Marcar como leída
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

