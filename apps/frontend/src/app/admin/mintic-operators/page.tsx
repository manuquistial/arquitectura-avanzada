'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { apiService } from '@/lib/api';

interface MinTICOperator {
  id: number;
  mintic_operator_id: string;
  name: string;
  address: string;
  contact_mail: string;
  participants: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface RegisterOperatorForm {
  name: string;
  address: string;
  contactMail: string;
  participants: string[];
}

export default function MinTICOperatorsPage() {
  const { data: session } = useSession();
  const [operators, setOperators] = useState<MinTICOperator[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRegisterForm, setShowRegisterForm] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [formData, setFormData] = useState<RegisterOperatorForm>({
    name: '',
    address: '',
    contactMail: '',
    participants: ['']
  });

  // Check if user is mintic
  const isMintic = session?.user?.roles?.includes('mintic');

  useEffect(() => {
    if (isMintic) {
      fetchOperators();
    }
  }, [isMintic]);

  const fetchOperators = async () => {
    try {
      setLoading(true);
      const response = await apiService.getMinTICOperators();
      setOperators(response.operators || []);
    } catch (err) {
      console.error('Error fetching operators:', err);
      setError('Error al cargar los operadores');
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterOperator = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegistering(true);
    setError(null);

    try {
      // Filter out empty participants
      const participants = formData.participants.filter(p => p.trim() !== '');
      
      await apiService.registerMinTICOperator({
        name: formData.name,
        address: formData.address,
        contactMail: formData.contactMail,
        participants
      });

      // Reset form and refresh list
      setFormData({
        name: '',
        address: '',
        contactMail: '',
        participants: ['']
      });
      setShowRegisterForm(false);
      await fetchOperators();
    } catch (err: any) {
      console.error('Error registering operator:', err);
      setError(err.response?.data?.detail || 'Error al registrar el operador');
    } finally {
      setRegistering(false);
    }
  };

  const handleDeactivateOperator = async (operatorId: number) => {
    if (!confirm('¿Estás seguro de que quieres desactivar este operador?')) {
      return;
    }

    try {
      await apiService.deactivateMinTICOperator(operatorId);
      await fetchOperators();
    } catch (err) {
      console.error('Error deactivating operator:', err);
      setError('Error al desactivar el operador');
    }
  };

  const handleDeleteOperator = async (operatorId: number) => {
    if (!confirm('¿Estás seguro de que quieres eliminar este operador? Esta acción no se puede deshacer.')) {
      return;
    }

    try {
      await apiService.deleteMinTICOperator(operatorId);
      await fetchOperators();
    } catch (err) {
      console.error('Error deleting operator:', err);
      setError('Error al eliminar el operador');
    }
  };

  const addParticipant = () => {
    setFormData(prev => ({
      ...prev,
      participants: [...prev.participants, '']
    }));
  };

  const removeParticipant = (index: number) => {
    setFormData(prev => ({
      ...prev,
      participants: prev.participants.filter((_, i) => i !== index)
    }));
  };

  const updateParticipant = (index: number, value: string) => {
    setFormData(prev => ({
      ...prev,
      participants: prev.participants.map((p, i) => i === index ? value : p)
    }));
  };

  if (!isMintic) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Acceso Denegado</h1>
          <p className="text-gray-600">No tienes permisos para acceder a esta página.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Gestión de Operadores MinTIC</h1>
          <p className="mt-2 text-gray-600">
            Administra los operadores registrados en el Hub MinTIC
          </p>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <div className="mt-2 text-sm text-red-700">{error}</div>
              </div>
            </div>
          </div>
        )}

        <div className="mb-6">
          <button
            onClick={() => setShowRegisterForm(!showRegisterForm)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium"
          >
            {showRegisterForm ? 'Cancelar' : 'Registrar Nuevo Operador'}
          </button>
        </div>

        {showRegisterForm && (
          <div className="bg-white shadow rounded-lg p-6 mb-8">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Registrar Operador en MinTIC</h2>
            <form onSubmit={handleRegisterOperator} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Nombre del Operador</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Dirección</label>
                <input
                  type="text"
                  value={formData.address}
                  onChange={(e) => setFormData(prev => ({ ...prev, address: e.target.value }))}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Email de Contacto</label>
                <input
                  type="email"
                  value={formData.contactMail}
                  onChange={(e) => setFormData(prev => ({ ...prev, contactMail: e.target.value }))}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Participantes</label>
                {formData.participants.map((participant, index) => (
                  <div key={index} className="flex gap-2 mt-2">
                    <input
                      type="text"
                      value={participant}
                      onChange={(e) => updateParticipant(index, e.target.value)}
                      className="flex-1 border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Nombre del participante"
                    />
                    {formData.participants.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeParticipant(index)}
                        className="px-3 py-2 text-red-600 hover:text-red-800"
                      >
                        Eliminar
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addParticipant}
                  className="mt-2 text-blue-600 hover:text-blue-800 text-sm"
                >
                  + Agregar Participante
                </button>
              </div>

              <div className="flex gap-4">
                <button
                  type="submit"
                  disabled={registering}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-md font-medium"
                >
                  {registering ? 'Registrando...' : 'Registrar Operador'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowRegisterForm(false)}
                  className="bg-gray-300 hover:bg-gray-400 text-gray-700 px-4 py-2 rounded-md font-medium"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Operadores Registrados</h2>
          </div>

          {loading ? (
            <div className="p-6 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Cargando operadores...</p>
            </div>
          ) : operators.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No hay operadores registrados
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Nombre
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      ID MinTIC
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Email
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Participantes
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Estado
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Fecha
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {operators.map((operator) => (
                    <tr key={operator.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{operator.name}</div>
                        <div className="text-sm text-gray-500">{operator.address}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {operator.mintic_operator_id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {operator.contact_mail}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {operator.participants.length} participante(s)
                        </div>
                        <div className="text-xs text-gray-500">
                          {operator.participants.slice(0, 2).join(', ')}
                          {operator.participants.length > 2 && '...'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          operator.is_active 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {operator.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(operator.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                        {operator.is_active && (
                          <button
                            onClick={() => handleDeactivateOperator(operator.id)}
                            className="text-yellow-600 hover:text-yellow-900"
                          >
                            Desactivar
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteOperator(operator.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Eliminar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
