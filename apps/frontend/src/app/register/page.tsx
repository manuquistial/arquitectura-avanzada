'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    address: '',
    email: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Validate all fields are filled
    if (!formData.id.trim() || !formData.name.trim() || !formData.address.trim() || !formData.email.trim()) {
      setError('Todos los campos son obligatorios');
      setLoading(false);
      return;
    }

    // Validate citizen ID has exactly 10 digits
    if (formData.id.length !== 10) {
      setError('El número de cédula debe tener exactamente 10 dígitos');
      setLoading(false);
      return;
    }

    if (!/^\d{10}$/.test(formData.id)) {
      setError('El número de cédula debe contener solo dígitos');
      setLoading(false);
      return;
    }

    // Validate name and address are not empty
    if (formData.name.trim().length === 0) {
      setError('El nombre no puede estar vacío');
      setLoading(false);
      return;
    }

    if (formData.address.trim().length === 0) {
      setError('La dirección no puede estar vacía');
      setLoading(false);
      return;
    }

    try {
      // Register citizen (trim all fields)
      await api.post('/api/citizens/register', {
        id: parseInt(formData.id),
        name: formData.name.trim(),
        address: formData.address.trim(),
        email: formData.email.trim(),
        operatorId: process.env.NEXT_PUBLIC_OPERATOR_ID || '',
        operatorName: process.env.NEXT_PUBLIC_OPERATOR_NAME || '',
      });

      setSuccess(true);
      setTimeout(() => {
        router.push('/login');
      }, 2000);
    } catch (err) {
      const error = err as { response?: { status?: number; data?: { detail?: string } } };
      const errorDetail = error.response?.data?.detail;
      
      // Handle specific error cases
      if (error.response?.status === 409) {
        setError(errorDetail || 'Este número de cédula ya está registrado');
      } else if (error.response?.status === 400) {
        setError(errorDetail || 'Error de validación. Verifica los datos ingresados');
      } else if (error.response?.status === 502 || error.response?.status === 503) {
        setError('El servicio de registro no está disponible. Intenta más tarde');
      } else {
        setError(errorDetail || 'Error al registrar ciudadano');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900">
            Registro de Ciudadano
          </h1>
          <p className="mt-2 text-gray-600">
            Completa tus datos para registrarte
          </p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          {success && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
              ¡Registro exitoso! Redirigiendo...
            </div>
          )}

          <div>
            <input
              type="text"
              placeholder="Número de cédula (10 dígitos)"
              value={formData.id}
              onChange={(e) => {
                // Only allow digits and max 10 characters
                const value = e.target.value.replace(/\D/g, '').slice(0, 10);
                setFormData({ ...formData, id: value });
              }}
              required
              maxLength={10}
              pattern="\d{10}"
              className="w-full"
            />
            {formData.id.length > 0 && formData.id.length < 10 && (
              <p className="text-sm text-gray-500 mt-1">
                {10 - formData.id.length} dígitos restantes
              </p>
            )}
          </div>

          <div>
            <input
              type="text"
              placeholder="Nombre completo"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              className="w-full"
            />
          </div>

          <div>
            <input
              type="text"
              placeholder="Dirección"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              required
              className="w-full"
            />
          </div>

          <div>
            <input
              type="email"
              placeholder="Correo electrónico"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              className="w-full"
            />
          </div>

          <button
            type="submit"
            disabled={loading || success}
            className="w-full btn-primary"
          >
            {loading ? 'Registrando...' : 'Registrarse'}
          </button>

          <div className="text-center">
            <a href="/login" className="text-blue-600 hover:text-blue-800">
              ¿Ya tienes cuenta? Inicia sesión
            </a>
          </div>
        </form>
      </div>
    </div>
  );
}

