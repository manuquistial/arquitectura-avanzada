"use client";

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';

interface UserSettings {
  notifications: {
    email: boolean;
    push: boolean;
    documentSigned: boolean;
    transferReceived: boolean;
    shareRequest: boolean;
    documentExpiring: boolean;
  };
  privacy: {
    profileVisible: boolean;
    showEmail: boolean;
    allowSharing: boolean;
  };
  appearance: {
    theme: 'light' | 'dark' | 'system';
    language: 'es' | 'en';
  };
}

export default function SettingsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [settings, setSettings] = useState<UserSettings>({
    notifications: {
      email: true,
      push: true,
      documentSigned: true,
      transferReceived: true,
      shareRequest: true,
      documentExpiring: true,
    },
    privacy: {
      profileVisible: true,
      showEmail: false,
      allowSharing: true,
    },
    appearance: {
      theme: 'light',
      language: 'es',
    },
  });
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<'profile' | 'notifications' | 'privacy' | 'appearance' | 'account'>('profile');

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  const handleSave = async () => {
    try {
      setLoading(true);
      // TODO: API call to save settings
      // await fetch('/api/settings', {
      //   method: 'PUT',
      //   body: JSON.stringify(settings),
      // });
      
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Error saving settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = (category: keyof UserSettings, key: string, value: unknown) => {
    setSettings({
      ...settings,
      [category]: {
        ...settings[category],
        [key]: value,
      },
    });
  };

  if (status === 'loading') {
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
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            ⚙️ Configuración
          </h1>
          <p className="mt-2 text-gray-600">
            Personaliza tu experiencia en Carpeta Ciudadana
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar Navigation */}
          <div className="lg:col-span-1">
            <nav className="bg-white rounded-lg shadow-sm border border-gray-200 p-2">
              {[
                { id: 'notifications', icon: '🔔', label: 'Notificaciones' },
                { id: 'privacy', icon: '🔒', label: 'Privacidad' },
                { id: 'appearance', icon: '🎨', label: 'Apariencia' },
                { id: 'account', icon: '👤', label: 'Cuenta' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as 'profile' | 'notifications' | 'privacy' | 'appearance' | 'account')}
                  className={`w-full text-left px-4 py-3 rounded-lg transition-colors mb-1 ${
                    activeTab === tab.id
                      ? 'bg-blue-50 text-blue-700 font-semibold'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              {/* Notifications Tab */}
              {activeTab === 'notifications' && (
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-6">
                    🔔 Notificaciones
                  </h2>

                  <div className="space-y-6">
                    {/* Email Notifications */}
                    <div className="border-b border-gray-200 pb-6">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">
                        Canales de notificación
                      </h3>
                      
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium text-gray-900">📧 Correo electrónico</div>
                            <div className="text-sm text-gray-600">Recibir notificaciones por email</div>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={settings.notifications.email}
                              onChange={(e) => updateSetting('notifications', 'email', e.target.checked)}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                          </label>
                        </div>

                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium text-gray-900">📱 Notificaciones push</div>
                            <div className="text-sm text-gray-600">Recibir notificaciones en el navegador</div>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={settings.notifications.push}
                              onChange={(e) => updateSetting('notifications', 'push', e.target.checked)}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                          </label>
                        </div>
                      </div>
                    </div>

                    {/* Event Notifications */}
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">
                        Eventos
                      </h3>
                      
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium text-gray-900">✅ Documento firmado</div>
                            <div className="text-sm text-gray-600">Cuando un documento sea firmado exitosamente</div>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={settings.notifications.documentSigned}
                              onChange={(e) => updateSetting('notifications', 'documentSigned', e.target.checked)}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                          </label>
                        </div>

                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium text-gray-900">📥 Transferencia recibida</div>
                            <div className="text-sm text-gray-600">Cuando recibas un documento transferido</div>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={settings.notifications.transferReceived}
                              onChange={(e) => updateSetting('notifications', 'transferReceived', e.target.checked)}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                          </label>
                        </div>

                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium text-gray-900">🔗 Solicitud para compartir</div>
                            <div className="text-sm text-gray-600">Cuando alguien solicite acceso a un documento</div>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={settings.notifications.shareRequest}
                              onChange={(e) => updateSetting('notifications', 'shareRequest', e.target.checked)}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                          </label>
                        </div>

                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium text-gray-900">⏰ Documento por vencer</div>
                            <div className="text-sm text-gray-600">Recordatorios de documentos próximos a vencer</div>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={settings.notifications.documentExpiring}
                              onChange={(e) => updateSetting('notifications', 'documentExpiring', e.target.checked)}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                          </label>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Privacy Tab */}
              {activeTab === 'privacy' && (
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-6">
                    🔒 Privacidad
                  </h2>

                  <div className="space-y-6">
                    <div className="flex items-center justify-between py-4 border-b border-gray-200">
                      <div>
                        <div className="font-medium text-gray-900">Perfil visible</div>
                        <div className="text-sm text-gray-600">Otros usuarios pueden ver tu perfil público</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.privacy.profileVisible}
                          onChange={(e) => updateSetting('privacy', 'profileVisible', e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between py-4 border-b border-gray-200">
                      <div>
                        <div className="font-medium text-gray-900">Mostrar correo electrónico</div>
                        <div className="text-sm text-gray-600">Tu email será visible en tu perfil</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.privacy.showEmail}
                          onChange={(e) => updateSetting('privacy', 'showEmail', e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between py-4">
                      <div>
                        <div className="font-medium text-gray-900">Permitir compartir</div>
                        <div className="text-sm text-gray-600">Otros pueden compartir documentos contigo</div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.privacy.allowSharing}
                          onChange={(e) => updateSetting('privacy', 'allowSharing', e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                  </div>
                </div>
              )}

              {/* Appearance Tab */}
              {activeTab === 'appearance' && (
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-6">
                    🎨 Apariencia
                  </h2>

                  <div className="space-y-6">
                    <div>
                      <label className="block font-medium text-gray-900 mb-3">
                        Tema
                      </label>
                      <div className="grid grid-cols-3 gap-4">
                        {['light', 'dark', 'system'].map((theme) => (
                          <button
                            key={theme}
                            onClick={() => updateSetting('appearance', 'theme', theme)}
                            className={`p-4 border-2 rounded-lg transition-all ${
                              settings.appearance.theme === theme
                                ? 'border-blue-600 bg-blue-50'
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <div className="text-3xl mb-2">
                              {theme === 'light' && '☀️'}
                              {theme === 'dark' && '🌙'}
                              {theme === 'system' && '💻'}
                            </div>
                            <div className="font-medium capitalize">{theme}</div>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block font-medium text-gray-900 mb-3">
                        Idioma
                      </label>
                      <select
                        value={settings.appearance.language}
                        onChange={(e) => updateSetting('appearance', 'language', e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="es">🇪🇸 Español</option>
                        <option value="en">🇬🇧 English</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {/* Account Tab */}
              {activeTab === 'account' && (
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-6">
                    👤 Cuenta
                  </h2>

                  <div className="space-y-6">
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center gap-4">
                        <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center text-white text-2xl font-bold">
                          {session?.user?.name?.charAt(0) || 'U'}
                        </div>
                        <div>
                          <div className="font-semibold text-gray-900">{session?.user?.name || 'Usuario'}</div>
                          <div className="text-sm text-gray-600">{session?.user?.email || 'user@example.com'}</div>
                        </div>
                      </div>
                    </div>

                    <div className="border-t border-gray-200 pt-6">
                      <h3 className="font-semibold text-gray-900 mb-4">Zona de peligro</h3>
                      <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">
                        🗑️ Eliminar cuenta
                      </button>
                      <p className="mt-2 text-sm text-gray-600">
                        Esta acción es permanente y no se puede deshacer.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Save Button */}
              <div className="mt-8 pt-6 border-t border-gray-200 flex justify-end gap-4">
                <button
                  onClick={() => router.back()}
                  className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSave}
                  disabled={loading}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Guardando...
                    </>
                  ) : saved ? (
                    <>
                      ✓ Guardado
                    </>
                  ) : (
                    <>
                      💾 Guardar cambios
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

