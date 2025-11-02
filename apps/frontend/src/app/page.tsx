"use client";

import { useState, useEffect } from 'react';
import { signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import Link from 'next/link';

export default function HomePage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();
  const { data: session, status } = useSession();

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (status === 'loading') return;
    if (session) {
      router.push('/dashboard');
    }
  }, [session, status, router]);

  const handleCredentialsLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const result = await signIn('credentials', {
        email,
        password,
        redirect: false,
      });

      if (result?.error) {
        setError('Credenciales inválidas. Por favor, verifica tu email y contraseña.');
      } else if (result?.ok) {
        router.push('/dashboard');
      } else {
        setError('Error inesperado en el login');
      }
    } catch (error) {
      setError('Error al iniciar sesión');
      console.error('Login error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading state while checking session
  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-white mx-auto"></div>
          <p className="mt-4 text-white text-lg">Cargando...</p>
        </div>
      </div>
    );
  }

  // If already authenticated, return null (will redirect)
  if (session) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        {/* Logo and Title */}
        <div className="text-center mb-8">
          <div className="mx-auto flex items-center justify-center h-20 w-20 rounded-full bg-white bg-opacity-20 mb-4">
            <span className="text-4xl">📁</span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">
            Carpeta Ciudadana
          </h1>
          <p className="text-blue-100 text-lg">
            Sistema de gestión documental ciudadana
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8 space-y-6">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-900">
              Iniciar Sesión
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              Ingresa tus credenciales para acceder
            </p>
          </div>

          <form onSubmit={handleCredentialsLogin} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-semibold text-gray-700 mb-2">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors text-gray-900 placeholder-gray-400"
                placeholder="tu@email.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-semibold text-gray-700 mb-2">
                Contraseña
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors text-gray-900 placeholder-gray-400"
                placeholder="Tu contraseña"
              />
            </div>

            {error && (
              <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-base font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-[1.02]"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Iniciando sesión...
                </>
              ) : (
                'Iniciar Sesión'
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">o</span>
            </div>
          </div>

          {/* Register Link */}
          <div className="text-center">
            <p className="text-sm text-gray-600">
              ¿No tienes una cuenta?{' '}
              <Link
                href="/register"
                className="font-semibold text-blue-600 hover:text-blue-700 transition-colors"
              >
                Regístrate aquí
              </Link>
            </p>
          </div>

          {/* Demo Credentials */}
          <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-100">
            <h4 className="text-sm font-semibold text-gray-900 mb-3">
              💡 Credenciales de demostración
            </h4>
            <div className="text-xs text-gray-700 space-y-2">
              <div className="flex justify-between items-center py-1">
                <span className="font-medium">Admin:</span>
                <span className="font-mono text-gray-600">admin@carpeta.com / admin123</span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="font-medium">Usuario:</span>
                <span className="font-mono text-gray-600">demo@carpeta.com / demo123</span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="font-medium">MinTIC:</span>
                <span className="font-mono text-gray-600">mintic@carpeta.com / mintic123</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center">
          <p className="text-sm text-blue-100">
            Sistema seguro de gestión documental
          </p>
        </div>
      </div>
    </div>
  );
}
