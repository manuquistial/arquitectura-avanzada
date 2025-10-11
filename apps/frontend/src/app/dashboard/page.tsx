'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { FileText, Upload, Search, Share2, ArrowRightLeft } from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, user, logout } = useAuthStore();
  const [stats] = useState({
    documents: 0,
    shared: 0,
    transfers: 0,
  });
  
  // TODO: Load actual stats from API
  // const loadStats = async () => {
  //   const response = await api.get(`/api/metadata/stats?citizen_id=${user?.id}`);
  //   setStats(response.data);
  // };

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">
            Carpeta Ciudadana
          </h1>
          <div className="flex items-center gap-4">
            <span className="text-gray-700">{user?.name || 'Usuario'}</span>
            <button onClick={handleLogout} className="btn-secondary">
              Cerrar sesión
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Welcome */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900">
            Bienvenido, {user?.name || 'Usuario'}
          </h2>
          <p className="text-gray-600 mt-2">
            Gestiona tus documentos de forma segura
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600">Documentos</p>
                <p className="text-3xl font-bold">{stats.documents}</p>
              </div>
              <FileText className="w-12 h-12 text-blue-500" />
            </div>
          </div>

          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600">Compartidos</p>
                <p className="text-3xl font-bold">{stats.shared}</p>
              </div>
              <Share2 className="w-12 h-12 text-green-500" />
            </div>
          </div>

          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600">Transferencias</p>
                <p className="text-3xl font-bold">{stats.transfers}</p>
              </div>
              <ArrowRightLeft className="w-12 h-12 text-purple-500" />
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Link href="/upload" className="card hover:shadow-lg transition-shadow cursor-pointer">
            <Upload className="w-10 h-10 text-blue-600 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Subir Documento</h3>
            <p className="text-gray-600">
              Sube nuevos documentos a tu carpeta
            </p>
          </Link>

          <Link href="/documents" className="card hover:shadow-lg transition-shadow cursor-pointer">
            <FileText className="w-10 h-10 text-green-600 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Mis Documentos</h3>
            <p className="text-gray-600">
              Ver y gestionar tus documentos
            </p>
          </Link>

          <Link href="/search" className="card hover:shadow-lg transition-shadow cursor-pointer">
            <Search className="w-10 h-10 text-purple-600 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Buscar</h3>
            <p className="text-gray-600">
              Busca documentos por nombre o contenido
            </p>
          </Link>

          <Link href="/transfer" className="card hover:shadow-lg transition-shadow cursor-pointer">
            <ArrowRightLeft className="w-10 h-10 text-orange-600 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Transferir</h3>
            <p className="text-gray-600">
              Transfiere tu carpeta a otro operador
            </p>
          </Link>
        </div>
      </main>
    </div>
  );
}

