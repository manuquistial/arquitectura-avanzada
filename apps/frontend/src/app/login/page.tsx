/**
 * Login Page
 * Azure AD B2C Sign In with NextAuth
 */

"use client";

import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LogIn, Shield, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Redirect if already authenticated
  useEffect(() => {
    if (status === "authenticated") {
      router.push("/dashboard");
    }
  }, [status, router]);

  const handleSignIn = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Trigger Azure AD B2C sign in
      await signIn("azure-ad-b2c", {
        callbackUrl: "/dashboard",
        redirect: true,
      });
    } catch (err) {
      console.error("Sign in error:", err);
      setError("Error al iniciar sesión. Por favor, intente nuevamente.");
      setIsLoading(false);
    }
  };

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Cargando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
      <div className="max-w-md w-full space-y-8">
        {/* Logo and Title */}
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-blue-600 rounded-full flex items-center justify-center mb-4">
            <Shield className="h-10 w-10 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-gray-900">Carpeta Ciudadana</h2>
          <p className="mt-2 text-sm text-gray-600">
            Portal de Operador - Azure AD B2C
          </p>
        </div>

        {/* Sign In Card */}
        <div className="bg-white py-8 px-6 shadow-xl rounded-lg border border-gray-200">
          <div className="space-y-6">
            {/* Info Message */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <Shield className="h-5 w-5 text-blue-600" />
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">
                    Autenticación Segura
                  </h3>
                  <p className="mt-1 text-sm text-blue-700">
                    Utiliza Azure AD B2C para iniciar sesión de forma segura con
                    autenticación de múltiples factores.
                  </p>
                </div>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex">
                  <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
                  <div className="ml-3">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Sign In Button */}
            <button
              onClick={handleSignIn}
              disabled={isLoading}
              className="w-full flex items-center justify-center px-4 py-3 border border-transparent text-base font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-3"></div>
                  Iniciando sesión...
                </>
              ) : (
                <>
                  <LogIn className="h-5 w-5 mr-2" />
                  Iniciar Sesión con Azure AD
                </>
              )}
            </button>

            {/* Additional Info */}
            <div className="text-center text-sm text-gray-600">
              <p>
                ¿Primera vez? Tu cuenta será creada automáticamente al iniciar
                sesión.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-sm text-gray-500">
          <p>
            Carpeta Ciudadana - Operador Azure
            <br />
            {process.env.NEXT_PUBLIC_OPERATOR_NAME || "Demo Operator"}
          </p>
        </div>
      </div>
    </div>
  );
}
