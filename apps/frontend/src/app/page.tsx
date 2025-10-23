"use client";

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import Link from 'next/link';

export default function HomePage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === 'loading') return; // Still loading
    if (session) router.push('/dashboard'); // Already authenticated
  }, [session, status, router]);

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando...</p>
        </div>
      </div>
    );
  }

  if (session) {
    return null; // Will redirect to dashboard
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            📁 Carpeta Ciudadana
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Sistema de gestión documental ciudadana
          </p>
          <div className="space-y-4">
            <Link
              href="/login"
              className="inline-block bg-blue-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              Iniciar Sesión
            </Link>
            <div className="mt-4">
              <p className="text-sm text-gray-500">
                Credenciales de prueba:
              </p>
              <p className="text-sm text-gray-500">
                admin@carpeta.com / admin123
              </p>
              <p className="text-sm text-gray-500">
                demo@carpeta.com / demo123
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}