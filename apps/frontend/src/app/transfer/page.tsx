'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { ArrowRightLeft, AlertTriangle } from 'lucide-react';

interface Operator {
  OperatorId: string;
  OperatorName: string;
  transferAPIURL: string;
}

export default function TransferPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [operators, setOperators] = useState<Operator[]>([]);
  const [selectedOperator, setSelectedOperator] = useState('');
  const [error, setError] = useState('');
  const [step, setStep] = useState<'select' | 'confirm' | 'processing' | 'success'>('select');

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    loadOperators();
  }, [isAuthenticated, router]);

  const loadOperators = async () => {
    try {
      // TODO: Implement actual API call to MinTIC
      // const response = await api.get('/api/mintic/operators');
      // setOperators(response.data);

      // Mock data
      setOperators([
        {
          OperatorId: 'operator-1',
          OperatorName: 'Operador Nacional',
          transferAPIURL: 'https://operador1.com/api/transferCitizen',
        },
        {
          OperatorId: 'operator-2',
          OperatorName: 'Operador Regional',
          transferAPIURL: 'https://operador2.com/api/transferCitizen',
        },
      ]);
    } catch (err) {
      setError('Error al cargar operadores');
    }
  };

  const handleTransfer = async () => {
    if (!selectedOperator) return;

    setStep('processing');
    setError('');

    try {
      // TODO: Implement transfer initiation
      // const response = await api.post('/api/transfer/initiate', {
      //   destination_operator_id: selectedOperator,
      //   citizen_id: user?.id,
      // });

      // Simulate transfer process
      await new Promise(resolve => setTimeout(resolve, 2000));

      setStep('success');
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Error al transferir carpeta');
      setStep('select');
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  const selectedOperatorData = operators.find(op => op.OperatorId === selectedOperator);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">
            Transferir Carpeta
          </h1>
          <button
            onClick={() => router.push('/dashboard')}
            className="btn-secondary"
          >
            Volver
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {step === 'select' && (
          <div className="card space-y-6">
            <div className="flex items-center gap-4">
              <ArrowRightLeft className="w-12 h-12 text-orange-600" />
              <div>
                <h2 className="text-2xl font-bold">
                  Transferir tu carpeta ciudadana
                </h2>
                <p className="text-gray-600 mt-1">
                  Selecciona el operador al que deseas transferir tu carpeta
                </p>
              </div>
            </div>

            <div className="bg-yellow-50 border border-yellow-200 p-4 rounded flex gap-3">
              <AlertTriangle className="w-6 h-6 text-yellow-600 flex-shrink-0" />
              <div className="text-sm text-yellow-800">
                <p className="font-semibold mb-1">Advertencia:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Esta acción es irreversible</li>
                  <li>Todos tus documentos serán transferidos</li>
                  <li>Tu cuenta en este operador será desactivada</li>
                  <li>El proceso puede tomar varios minutos</li>
                </ul>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Selecciona el operador destino:
              </label>
              <select
                value={selectedOperator}
                onChange={(e) => setSelectedOperator(e.target.value)}
                className="w-full"
              >
                <option value="">-- Selecciona un operador --</option>
                {operators.map((op) => (
                  <option key={op.OperatorId} value={op.OperatorId}>
                    {op.OperatorName}
                  </option>
                ))}
              </select>
            </div>

            {selectedOperator && (
              <div className="bg-blue-50 border border-blue-200 p-4 rounded">
                <h3 className="font-semibold text-blue-900 mb-2">
                  Operador seleccionado:
                </h3>
                <p className="text-blue-800">{selectedOperatorData?.OperatorName}</p>
                <p className="text-sm text-blue-600 mt-1">
                  {selectedOperatorData?.transferAPIURL}
                </p>
              </div>
            )}

            <div className="flex gap-4">
              <button
                onClick={() => router.back()}
                className="flex-1 btn-secondary"
              >
                Cancelar
              </button>
              <button
                onClick={() => setStep('confirm')}
                disabled={!selectedOperator}
                className="flex-1 btn-primary"
              >
                Continuar
              </button>
            </div>
          </div>
        )}

        {step === 'confirm' && (
          <div className="card space-y-6">
            <h2 className="text-2xl font-bold">Confirmar transferencia</h2>

            <div className="bg-red-50 border border-red-200 p-4 rounded">
              <p className="text-red-800 font-semibold">
                ¿Estás seguro de que deseas transferir tu carpeta ciudadana a{' '}
                {selectedOperatorData?.OperatorName}?
              </p>
              <p className="text-red-700 mt-2">
                Esta acción no se puede deshacer.
              </p>
            </div>

            <div className="flex gap-4">
              <button
                onClick={() => setStep('select')}
                className="flex-1 btn-secondary"
              >
                Volver
              </button>
              <button
                onClick={handleTransfer}
                className="flex-1 btn-danger"
              >
                Confirmar Transferencia
              </button>
            </div>
          </div>
        )}

        {step === 'processing' && (
          <div className="card text-center space-y-6">
            <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <h2 className="text-2xl font-bold">Procesando transferencia...</h2>
            <p className="text-gray-600">
              Estamos transfiriendo tu carpeta. Por favor no cierres esta página.
            </p>
          </div>
        )}

        {step === 'success' && (
          <div className="card text-center space-y-6">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
              <svg
                className="w-10 h-10 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-bold">¡Transferencia exitosa!</h2>
            <p className="text-gray-600">
              Tu carpeta ha sido transferida exitosamente a{' '}
              {selectedOperatorData?.OperatorName}.
            </p>
            <p className="text-gray-600">
              Tu sesión se cerrará automáticamente en 10 segundos.
            </p>
            <button
              onClick={() => {
                useAuthStore.getState().logout();
                router.push('/login');
              }}
              className="btn-primary"
            >
              Cerrar Sesión
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

