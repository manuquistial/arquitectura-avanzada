'use client';

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiService } from '@/lib/api';

interface User {
  id: string;
  email: string;
  name?: string;
  given_name?: string;
  family_name?: string;
  roles: string[];
  permissions: string[];
  is_active: boolean;
  is_verified: boolean;
  email_verified: boolean;
  operator_id?: string;
  created_at: string;
  last_login_at?: string;
}

export default function UsersAdminPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive' | 'admin'>('all');

  useEffect(() => {
    if (status === 'loading') return;
    
    if (!session) {
      router.push('/login');
      return;
    }

    if (!session.user?.roles?.includes('admin') && !session.user?.roles?.includes('mintic')) {
      router.push('/dashboard');
      return;
    }
  }, [session, status, router]);

  useEffect(() => {
    if (session?.user?.roles?.includes('admin') || session?.user?.roles?.includes('mintic')) {
      fetchUsers();
    }
  }, [session, filter]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getAllUsers(0, 100);
      setUsers(Array.isArray(data) ? data : []);
    } catch (error: any) {
      console.error('Error fetching users:', error);
      setError('Error al cargar los usuarios');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateUser = async (userId: string, updates: Partial<User>) => {
    try {
      await apiService.updateUser(userId, updates);
      await fetchUsers();
      setEditingUser(null);
    } catch (error: any) {
      console.error('Error updating user:', error);
      alert('Error al actualizar el usuario');
    }
  };

  const filteredUsers = users.filter(user => {
    if (filter === 'active') return user.is_active;
    if (filter === 'inactive') return !user.is_active;
    if (filter === 'admin') return user.roles.includes('admin');
    return true;
  });

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

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Cargando usuarios...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                👥 Gestión de Usuarios
              </h1>
              <p className="mt-2 text-gray-600">
                Administra los usuarios registrados en el sistema
              </p>
            </div>
            <button
              onClick={() => router.push('/admin')}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              ← Volver al Admin
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex items-center gap-4">
            <label className="block text-sm font-medium text-gray-700">
              Filtro:
            </label>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">Todos</option>
              <option value="active">Activos</option>
              <option value="inactive">Inactivos</option>
              <option value="admin">Administradores</option>
            </select>
            <div className="ml-auto text-sm text-gray-600">
              Total: {filteredUsers.length} usuario(s)
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Users List */}
        {filteredUsers.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <div className="text-6xl mb-4">👥</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No hay usuarios disponibles
            </h3>
            <p className="text-gray-600">
              No se encontraron usuarios con los filtros seleccionados
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Usuario
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Roles
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Estado
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Último Acceso
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredUsers.map((user) => (
                    <tr key={user.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {user.name || user.email}
                          </div>
                          <div className="text-sm text-gray-500">
                            {user.email}
                          </div>
                          {user.given_name && user.family_name && (
                            <div className="text-xs text-gray-400">
                              {user.given_name} {user.family_name}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-wrap gap-1">
                          {user.roles.map((role) => (
                            <span
                              key={role}
                              className={`px-2 py-1 text-xs font-medium rounded-full ${
                                role === 'admin'
                                  ? 'bg-purple-100 text-purple-800'
                                  : role === 'mintic'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-gray-100 text-gray-800'
                              }`}
                            >
                              {role}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="space-y-1">
                          {user.is_active ? (
                            <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                              ✅ Activo
                            </span>
                          ) : (
                            <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">
                              ❌ Inactivo
                            </span>
                          )}
                          {user.email_verified && (
                            <div className="text-xs text-gray-500">
                              ✓ Email verificado
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(user.last_login_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <button
                          onClick={() => setEditingUser(user)}
                          className="text-blue-600 hover:text-blue-900 mr-4"
                        >
                          Editar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Edit User Modal */}
        {editingUser && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
            <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
              <div className="mt-3">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Editar Usuario: {editingUser.email}
                </h3>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const formData = new FormData(e.target as HTMLFormElement);
                    handleUpdateUser(editingUser.id, {
                      name: formData.get('name') as string || undefined,
                      given_name: formData.get('given_name') as string || undefined,
                      family_name: formData.get('family_name') as string || undefined,
                      roles: (formData.get('roles') as string)?.split(',').map(r => r.trim()) || editingUser.roles,
                      is_active: formData.get('is_active') === 'true',
                    });
                  }}
                >
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Nombre
                      </label>
                      <input
                        type="text"
                        name="name"
                        defaultValue={editingUser.name || ''}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Nombre (Given Name)
                      </label>
                      <input
                        type="text"
                        name="given_name"
                        defaultValue={editingUser.given_name || ''}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Apellido (Family Name)
                      </label>
                      <input
                        type="text"
                        name="family_name"
                        defaultValue={editingUser.family_name || ''}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Roles (separados por coma)
                      </label>
                      <input
                        type="text"
                        name="roles"
                        defaultValue={editingUser.roles.join(', ')}
                        placeholder="admin, user, mintic"
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Estado
                      </label>
                      <select
                        name="is_active"
                        defaultValue={editingUser.is_active ? 'true' : 'false'}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="true">Activo</option>
                        <option value="false">Inactivo</option>
                      </select>
                    </div>
                  </div>
                  <div className="mt-6 flex justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => setEditingUser(null)}
                      className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
                    >
                      Guardar
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

