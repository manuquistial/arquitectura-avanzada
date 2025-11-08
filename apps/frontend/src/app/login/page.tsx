"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { z } from "zod";

import { AuthShell } from "@/components/auth/AuthShell";
import { Button } from "@/components/ui/Button";

const loginSchema = z.object({
  email: z.string().email("Correo inválido"),
  password: z.string().min(6, "La contraseña debe tener al menos 6 caracteres"),
});

export default function LoginPage() {
  const router = useRouter();
  const [formState, setFormState] = useState({ email: "", password: "" });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleChange = (field: "email" | "password") => (value: string) => {
    setFormState((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: "" }));
    setError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    const result = loginSchema.safeParse(formState);
    if (!result.success) {
      const errors = result.error.formErrors.fieldErrors;
      setFieldErrors({
        email: errors.email?.[0] ?? "",
        password: errors.password?.[0] ?? "",
      });
      setIsLoading(false);
      return;
    }

    try {
      const response = await signIn("credentials", {
        ...formState,
        redirect: false,
      });

      if (response?.error) {
        setError("Credenciales inválidas. Verifica tu correo y contraseña.");
        return;
      }

      router.push("/dashboard");
    } catch (err) {
      console.error("Login error", err);
      setError("No pudimos iniciar sesión. Intenta nuevamente.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthShell
      breadcrumbs={[
        { label: "Inicio", href: "/" },
        { label: "Iniciar sesión" },
      ]}
      title="Iniciar sesión"
      subtitle="Ingresa tus credenciales para acceder a tu Carpeta Ciudadana."
      footer={
        <div className="space-y-2 text-center">
          <p>
            ¿No tienes cuenta?{" "}
            <Link
              href="/register"
              className="font-semibold text-primary-600 hover:text-primary-700"
            >
              Regístrate aquí
            </Link>
          </p>
        </div>
      }
    >
      <form className="space-y-5" onSubmit={handleSubmit} noValidate>
        <div className="space-y-1.5">
          <label
            htmlFor="email"
            className="text-sm font-medium text-[var(--text-primary)]"
          >
            Correo electrónico
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="tuciudadano@correo.com"
            value={formState.email}
            onChange={(event) => handleChange("email")(event.target.value)}
            aria-invalid={Boolean(fieldErrors.email)}
            aria-describedby={fieldErrors.email ? "email-error" : undefined}
            className="w-full"
          />
          {fieldErrors.email ? (
            <p id="email-error" className="text-xs text-danger-500">
              {fieldErrors.email}
            </p>
          ) : null}
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label
              htmlFor="password"
              className="text-sm font-medium text-[var(--text-primary)]"
            >
              Contraseña
            </label>
            <Link
              href="/auth/error"
              className="text-xs font-medium text-primary-600 hover:text-primary-700"
            >
              ¿Olvidaste tu contraseña?
            </Link>
          </div>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={formState.password}
            onChange={(event) => handleChange("password")(event.target.value)}
            aria-invalid={Boolean(fieldErrors.password)}
            aria-describedby={
              fieldErrors.password ? "password-error" : undefined
            }
            className="w-full"
          />
          {fieldErrors.password ? (
            <p id="password-error" className="text-xs text-danger-500">
              {fieldErrors.password}
            </p>
          ) : null}
        </div>

        {error ? (
          <div className="rounded-[var(--radius-md)] border border-danger-200 bg-danger-100/60 px-4 py-3 text-sm text-danger-600">
            {error}
          </div>
        ) : null}

        <Button
          type="submit"
          className="w-full"
          isLoading={isLoading}
          disabled={isLoading}
        >
          {isLoading ? "Iniciando sesión..." : "Iniciar sesión"}
        </Button>

        <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-muted)] px-4 py-4 text-xs text-[var(--text-secondary)]">
          <p className="mb-2 font-semibold text-[var(--text-primary)]">
            Credenciales de demostración
          </p>
          <ul className="space-y-1">
            <li>
              <strong>Admin:</strong> admin@carpeta.com / admin123
            </li>
            <li>
              <strong>Usuario:</strong> demo@carpeta.com / demo123
            </li>
            <li>
              <strong>MinTIC:</strong> mintic@carpeta.com / mintic123
            </li>
          </ul>
        </div>
      </form>
    </AuthShell>
  );
}