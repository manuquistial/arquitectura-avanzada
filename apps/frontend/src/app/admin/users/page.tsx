'use client';

import { useEffect, useMemo, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { Users, ShieldCheck, Cog, Pencil, Trash2 } from 'lucide-react';

import { apiService } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Tooltip } from '@/components/ui/Tooltip';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableEmpty,
} from '@/components/ui/Table';

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

type FilterValue = 'all' | 'active' | 'inactive' | 'admin';

export default function UsersAdminPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [filter, setFilter] = useState<FilterValue>('all');

  useEffect(() => {
    if (status === 'loading') return;

    if (!session) {
      router.push('/login');
      return;
    }

    const roles = session.user?.roles ?? [];
    if (!roles.includes('admin') && !roles.includes('mintic')) {
      router.push('/dashboard');
    }
  }, [router, session, status]);

  useEffect(() => {
    if (session?.user?.roles?.includes('admin') || session?.user?.roles?.includes('mintic')) {
      fetchUsers();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  useEffect(() => {
    if (!loading && users.length === 0) return;
    // Trigger re-render for filter changes without refetching
  }, [filter, loading, users.length]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getAllUsers(0, 100);
      setUsers(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error fetching users:', err);
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
    } catch (err) {
      console.error('Error updating user:', err);
      alert('Error al actualizar el usuario');
    }
  };

  const handleUnregisterCitizen = async (userId: string, userEmail: string) => {
    if (
      !confirm(
        `¿Seguro que quieres desregistrar al ciudadano ${userEmail}? Esta acción eliminará completamente el usuario y no se puede deshacer.`
      )
    ) {
      return;
    }

    try {
      await apiService.unregisterCitizen({ id: userId });
      await fetchUsers();
      alert('Ciudadano desregistrado correctamente');
    } catch (err: any) {
      console.error('Error unregistering citizen:', err);
      const message = err?.response?.data?.detail || err?.message || 'Error al desregistrar el ciudadano';
      alert(message);
    }
  };

  const counts = useMemo(() => {
    const all = users.length;
    const active = users.filter((user) => user.is_active).length;
    const inactive = users.filter((user) => !user.is_active).length;
    const admin = users.filter((user) => user.roles.includes('admin')).length;
    return { all, active, inactive, admin };
  }, [users]);

  const filteredUsers = useMemo(() => {
    return users.filter((user) => {
      if (filter === 'active') return user.is_active;
      if (filter === 'inactive') return !user.is_active;
      if (filter === 'admin') return user.roles.includes('admin');
      return true;
    });
  }, [filter, users]);

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
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-12 w-12 animate-spin rounded-full border-2 border-primary-100 border-t-primary-500" />
          <p className="text-sm text-[var(--text-tertiary)]">Cargando usuarios…</p>
        </div>
      </div>
    );
  }

  const filterOptions: Array<{ value: FilterValue; label: string; count: number }> = [
    { value: 'all', label: 'Todos', count: counts.all },
    { value: 'active', label: 'Activos', count: counts.active },
    { value: 'inactive', label: 'Inactivos', count: counts.inactive },
    { value: 'admin', label: 'Administradores', count: counts.admin },
  ];

  return (
    <>
      <PageHeader
        breadcrumbs={[
          { label: 'Inicio', href: '/dashboard' },
          { label: 'Administración', href: '/admin' },
          { label: 'Gestión de usuarios' },
        ]}
        title="Gestión de usuarios"
        description="Administra ciudadanos registrados y controla sus accesos dentro de la Carpeta Ciudadana."
      />

      <Card>
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>Usuarios registrados</CardTitle>
            <CardDescription>Selecciona un filtro para revisar el estado actual de los usuarios.</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            {filterOptions.map((option) => (
              <Button
                key={option.value}
                variant={filter === option.value ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setFilter(option.value)}
              >
                {option.label} ({option.count})
              </Button>
            ))}
          </div>
        </CardHeader>

        <CardContent>
          {error ? (
            <div className="rounded-[var(--radius-md)] border border-danger-200 bg-danger-100/60 px-4 py-3 text-danger-600">
              {error}
            </div>
          ) : null}

          {filteredUsers.length === 0 ? (
            <TableEmpty>
              <div className="text-5xl">👥</div>
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                No se encontraron usuarios para el filtro seleccionado
              </h3>
              <p className="text-sm text-[var(--text-secondary)]">
                Ajusta el filtro o verifica si existen ciudadanos registrados con ese estado.
              </p>
            </TableEmpty>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Usuario</TableHead>
                  <TableHead>Roles</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Último acceso</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div>
                        <p className="text-sm font-semibold text-[var(--text-primary)]">
                          {user.name || user.email}
                        </p>
                        <p className="text-xs text-[var(--text-tertiary)]">{user.email}</p>
                        {user.given_name && user.family_name ? (
                          <p className="text-xs text-[var(--text-tertiary)]/80">
                            {user.given_name} {user.family_name}
                          </p>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        {user.roles.map((role) => (
                          <Badge
                            key={`${user.id}-${role}`}
                            variant={role === 'admin' ? 'info' : 'secondary'}
                          >
                            {role}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <Badge variant={user.is_active ? 'success' : 'danger'}>
                          {user.is_active ? 'Activo' : 'Inactivo'}
                        </Badge>
                        {user.email_verified ? (
                          <p className="text-xs text-[var(--text-tertiary)]">Correo verificado</p>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-[var(--text-secondary)]">
                      {formatDate(user.last_login_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Tooltip content="Editar usuario">
                          <Button
                            variant="ghost"
                            size="icon"
                            icon={<Pencil className="h-4 w-4" />}
                            aria-label="Editar usuario"
                            onClick={() => setEditingUser(user)}
                          >
                            <span className="sr-only">Editar</span>
                          </Button>
                        </Tooltip>
                        {user.id !== session.user?.id ? (
                          <Tooltip content="Desregistrar ciudadano">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-danger-500 hover:bg-danger-100/60"
                              icon={<Trash2 className="h-4 w-4" />}
                              aria-label="Desregistrar ciudadano"
                              onClick={() => handleUnregisterCitizen(user.id, user.email)}
                            >
                              <span className="sr-only">Desregistrar</span>
                            </Button>
                          </Tooltip>
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

      {editingUser ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Editar usuario</CardTitle>
              <CardDescription>{editingUser.email}</CardDescription>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  const formData = new FormData(event.currentTarget);
                  handleUpdateUser(editingUser.id, {
                    name: formData.get('name') as string || undefined,
                    given_name: formData.get('given_name') as string || undefined,
                    family_name: formData.get('family_name') as string || undefined,
                    roles:
                      (formData.get('roles') as string)
                        ?.split(',')
                        .map((role) => role.trim()) || editingUser.roles,
                    is_active: formData.get('is_active') === 'true',
                  });
                }}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[var(--text-primary)]">Nombre</label>
                  <input
                    type="text"
                    name="name"
                    defaultValue={editingUser.name || ''}
                    className="w-full rounded-[var(--radius-sm)] border border-[var(--border-subtle)] px-3 py-2"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[var(--text-primary)]">Nombre (Given Name)</label>
                  <input
                    type="text"
                    name="given_name"
                    defaultValue={editingUser.given_name || ''}
                    className="w-full rounded-[var(--radius-sm)] border border-[var(--border-subtle)] px-3 py-2"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[var(--text-primary)]">Apellido (Family Name)</label>
                  <input
                    type="text"
                    name="family_name"
                    defaultValue={editingUser.family_name || ''}
                    className="w-full rounded-[var(--radius-sm)] border border-[var(--border-subtle)] px-3 py-2"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[var(--text-primary)]">Roles (separados por coma)</label>
                  <input
                    type="text"
                    name="roles"
                    defaultValue={editingUser.roles.join(', ')}
                    className="w-full rounded-[var(--radius-sm)] border border-[var(--border-subtle)] px-3 py-2"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[var(--text-primary)]">Estado</label>
                  <select
                    name="is_active"
                    defaultValue={editingUser.is_active ? 'true' : 'false'}
                    className="w-full rounded-[var(--radius-sm)] border border-[var(--border-subtle)] px-3 py-2"
                  >
                    <option value="true">Activo</option>
                    <option value="false">Inactivo</option>
                  </select>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="ghost" type="button" onClick={() => setEditingUser(null)}>
                    Cancelar
                  </Button>
                  <Button type="submit">Guardar</Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </>
  );
}

