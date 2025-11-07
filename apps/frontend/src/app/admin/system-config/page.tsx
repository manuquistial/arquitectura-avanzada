'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { apiService } from '@/lib/api';

export default function SystemConfigPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [config, setConfig] = useState({
    operator_id: '',
    operator_name: '',
  });
  const [isConfigured, setIsConfigured] = useState(false);

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

    fetchConfig();
  }, [session, status, router]);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getSystemOperatorConfig();
      setConfig({
        operator_id: data.operator_id || '',
        operator_name: data.operator_name || '',
      });
      setIsConfigured(data.is_configured || false);
    } catch (err: any) {
      console.error('Error fetching config:', err);
      setError('Error al cargar la configuración del sistema');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      await apiService.updateSystemOperatorConfig(
        config.operator_id,
        config.operator_name,
        session?.user?.email || 'admin'
      );
      setSuccess('Configuración actualizada exitosamente');
      setIsConfigured(true);
      await fetchConfig();
    } catch (err: any) {
      console.error('Error updating config:', err);
      setError(err.response?.data?.detail || 'Error al actualizar la configuración');
    } finally {
      setSaving(false);
    }
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Cargando configuración...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            ⚙️ Configuración del Sistema
          </h1>
          <p className="mt-2 text-gray-600">
            Configura el operador MinTIC que se usará en todo el sistema
          </p>
        </div>

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">
                Información Importante
              </h3>
              <div className="mt-2 text-sm text-blue-700">
                <p>
                  El <strong>Operator ID</strong> y <strong>Operator Name</strong> configurados aquí 
                  se utilizarán en todas las interacciones con el Hub de MinTIC, incluyendo:
                </p>
                <ul className="list-disc list-inside mt-2 space-y-1">
                  <li>Registro de ciudadanos</li>
                  <li>Autenticación de documentos</li>
                  <li>Transferencias entre operadores</li>
                  <li>Todas las operaciones con MinTIC Hub</li>
                </ul>
                <p className="mt-2">
                  <strong>Nota:</strong> Estos valores deben coincidir con los que recibiste al registrar 
                  el operador "Carpeta Ciudadana" en el Hub de MinTIC.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="mb-6 bg-green-50 border border-green-200 text-green-600 px-4 py-3 rounded">
            {success}
          </div>
        )}

        {/* Configuration Form */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="operator_id" className="block text-sm font-medium text-gray-700 mb-2">
                Operator ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="operator_id"
                value={config.operator_id}
                onChange={(e) => setConfig({ ...config, operator_id: e.target.value })}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ej: OP-12345"
              />
              <p className="mt-1 text-sm text-gray-500">
                ID único del operador recibido al registrarse en el Hub de MinTIC
              </p>
            </div>

            <div>
              <label htmlFor="operator_name" className="block text-sm font-medium text-gray-700 mb-2">
                Operator Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="operator_name"
                value={config.operator_name}
                onChange={(e) => setConfig({ ...config, operator_name: e.target.value })}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ej: Carpeta Ciudadana"
              />
              <p className="mt-1 text-sm text-gray-500">
                Nombre del operador que se usará en todas las interacciones con MinTIC Hub
              </p>
            </div>

            {isConfigured && (
              <div className="bg-green-50 border border-green-200 rounded-md p-3">
                <div className="flex items-center">
                  <svg className="h-5 w-5 text-green-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm text-green-700 font-medium">
                    Configuración activa - Estos valores se están usando en todo el sistema
                  </span>
                </div>
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={() => router.back()}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
                disabled={saving}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Guardando...' : 'Guardar Configuración'}
              </button>
            </div>
          </form>
        </div>

        {/* Current Configuration Display */}
        {isConfigured && (
          <div className="mt-6 bg-gray-50 rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Configuración Actual del Sistema
            </h2>
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <dt className="text-sm font-medium text-gray-500">Operator ID</dt>
                <dd className="mt-1 text-sm text-gray-900 font-mono">{config.operator_id}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Operator Name</dt>
                <dd className="mt-1 text-sm text-gray-900">{config.operator_name}</dd>
              </div>
            </dl>
          </div>
        )}
      </div>
    </div>
  );
}

