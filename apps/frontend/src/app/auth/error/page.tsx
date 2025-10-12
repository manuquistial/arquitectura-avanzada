/**
 * Auth Error Page
 * Display authentication errors
 */

"use client";

import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { AlertCircle, Home } from "lucide-react";

export default function AuthErrorPage() {
  const searchParams = useSearchParams();
  const error = searchParams?.get("error");

  const getErrorMessage = (errorCode: string | null): string => {
    switch (errorCode) {
      case "Configuration":
        return "Error de configuración del servidor. Contacte al administrador.";
      case "AccessDenied":
        return "Acceso denegado. No tiene permisos para acceder a este recurso.";
      case "Verification":
        return "Error de verificación. El token de verificación ha expirado o es inválido.";
      case "OAuthSignin":
      case "OAuthCallback":
      case "OAuthCreateAccount":
      case "EmailCreateAccount":
      case "Callback":
        return "Error durante el proceso de autenticación. Por favor, intente nuevamente.";
      case "OAuthAccountNotLinked":
        return "Esta cuenta de email ya está asociada con otro proveedor de autenticación.";
      case "EmailSignin":
        return "Error al enviar el email de inicio de sesión.";
      case "CredentialsSignin":
        return "Credenciales inválidas. Por favor, verifique su información.";
      case "SessionRequired":
        return "Debe iniciar sesión para acceder a esta página.";
      default:
        return "Ha ocurrido un error inesperado durante la autenticación.";
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-50 to-orange-100 px-4">
      <div className="max-w-md w-full">
        <div className="bg-white py-8 px-6 shadow-xl rounded-lg border border-red-200">
          <div className="text-center">
            {/* Error Icon */}
            <div className="mx-auto h-16 w-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
              <AlertCircle className="h-10 w-10 text-red-600" />
            </div>

            {/* Error Title */}
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Error de Autenticación
            </h2>

            {/* Error Message */}
            <p className="text-gray-600 mb-6">{getErrorMessage(error)}</p>

            {/* Error Code */}
            {error && (
              <div className="bg-gray-50 rounded-lg p-3 mb-6">
                <p className="text-xs text-gray-500 font-mono">
                  Código de error: {error}
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="space-y-3">
              <Link
                href="/login"
                className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-base font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 transition-colors"
              >
                <Home className="h-5 w-5 mr-2" />
                Volver a Iniciar Sesión
              </Link>

              <Link
                href="/"
                className="w-full inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-base font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 transition-colors"
              >
                Ir al Inicio
              </Link>
            </div>
          </div>
        </div>

        {/* Support Info */}
        <div className="mt-6 text-center text-sm text-gray-600">
          <p>
            Si el problema persiste, contacte al administrador del sistema.
          </p>
        </div>
      </div>
    </div>
  );
}

