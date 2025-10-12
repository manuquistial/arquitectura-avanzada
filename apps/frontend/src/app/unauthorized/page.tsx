/**
 * Unauthorized Page
 * Displayed when user lacks required permissions
 */

"use client";

import { useSession } from "next-auth/react";
import Link from "next/link";
import { ShieldAlert, Home, LogOut } from "lucide-react";
import { signOut } from "next-auth/react";

export default function UnauthorizedPage() {
  const { data: session } = useSession();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-orange-50 to-red-100 px-4">
      <div className="max-w-md w-full">
        <div className="bg-white py-8 px-6 shadow-xl rounded-lg border border-orange-200">
          <div className="text-center">
            {/* Icon */}
            <div className="mx-auto h-16 w-16 bg-orange-100 rounded-full flex items-center justify-center mb-4">
              <ShieldAlert className="h-10 w-10 text-orange-600" />
            </div>

            {/* Title */}
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Acceso No Autorizado
            </h2>

            {/* Message */}
            <p className="text-gray-600 mb-6">
              No tienes los permisos necesarios para acceder a esta página.
            </p>

            {/* User Info */}
            {session?.user && (
              <div className="bg-gray-50 rounded-lg p-4 mb-6 text-left">
                <p className="text-sm text-gray-600 mb-2">
                  <span className="font-semibold">Usuario:</span>{" "}
                  {session.user.email}
                </p>
                <p className="text-sm text-gray-600">
                  <span className="font-semibold">Roles:</span>{" "}
                  {session.user.roles?.length > 0
                    ? session.user.roles.join(", ")
                    : "Sin roles asignados"}
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="space-y-3">
              <Link
                href="/dashboard"
                className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-base font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 transition-colors"
              >
                <Home className="h-5 w-5 mr-2" />
                Ir al Dashboard
              </Link>

              <button
                onClick={() => signOut({ callbackUrl: "/login" })}
                className="w-full inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-base font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 transition-colors"
              >
                <LogOut className="h-5 w-5 mr-2" />
                Cerrar Sesión
              </button>
            </div>
          </div>
        </div>

        {/* Support Info */}
        <div className="mt-6 text-center text-sm text-gray-600">
          <p>
            Si crees que deberías tener acceso, contacta al administrador del
            sistema.
          </p>
        </div>
      </div>
    </div>
  );
}

