"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { z } from "zod";

import { apiService } from "@/lib/api";
import { AuthShell } from "@/components/auth/AuthShell";
import { Button } from "@/components/ui/Button";

const registerSchema = z
  .object({
    id: z
      .string()
      .regex(/^\d{10}$/, "La cédula debe tener 10 dígitos numéricos"),
    name: z.string().min(3, "Ingresa tu nombre completo"),
    address: z.string().min(5, "Incluye tu dirección completa"),
    email: z.string().email("Correo electrónico inválido"),
    password: z
      .string()
      .min(8, "La contraseña debe tener al menos 8 caracteres"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Las contraseñas no coinciden",
    path: ["confirmPassword"],
  });

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();

  const [formState, setFormState] = useState<RegisterForm>({
    id: "",
    name: "",
    address: "",
    email: "",
    password: "",
    confirmPassword: "",
  });

  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<keyof RegisterForm, string>>
  >({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const remainingDigits = useMemo(() => 10 - formState.id.length, [formState.id]);

  const handleChange =
    (field: keyof RegisterForm) => (value: string) => {
      setFormState((prev) => ({ ...prev, [field]: value }));
      setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
      setServerError(null);
    };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setServerError(null);
    setFieldErrors({});

    const result = registerSchema.safeParse(formState);
    if (!result.success) {
      const errors = result.error.flatten().fieldErrors;
      setFieldErrors({
        id: errors.id?.[0],
        name: errors.name?.[0],
        address: errors.address?.[0],
        email: errors.email?.[0],
        password: errors.password?.[0],
        confirmPassword: errors.confirmPassword?.[0],
      });
      setIsSubmitting(false);
      return;
    }

    try {
      await apiService.registerCitizen({
        id: formState.id,
        name: formState.name.trim(),
        address: formState.address.trim(),
        email: formState.email.trim(),
        password: formState.password,
      });

      setSuccess(true);
      setTimeout(() => router.push("/login"), 1600);
    } catch (error) {
      const message =
        (error as { response?: { data?: { detail?: string }; status?: number } })
          ?.response?.data?.detail;
      setServerError(
        message ??
          "No pudimos completar el registro en este momento. Intenta de nuevo."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthShell
      breadcrumbs={[
        { label: "Inicio", href: "/" },
        { label: "Crear cuenta" },
      ]}
      title="Crear cuenta ciudadana"
      subtitle="Completa el formulario con tus datos para acceder a la Carpeta Ciudadana."
      footer={
        <div className="space-y-2 text-center">
          <p>
            ¿Ya tienes cuenta?{" "}
            <Link
              href="/login"
              className="font-semibold text-primary-600 hover:text-primary-700"
            >
              Inicia sesión
            </Link>
          </p>
          <p className="text-xs text-[var(--text-tertiary)]">
            Tus datos están protegidos según los estándares de seguridad del
            Gobierno Digital.
          </p>
        </div>
      }
    >
      <form className="space-y-4" onSubmit={handleSubmit} noValidate>
        {serverError ? (
          <div className="rounded-[var(--radius-md)] border border-danger-200 bg-danger-100/60 px-4 py-3 text-sm text-danger-600">
            {serverError}
          </div>
        ) : null}

        {success ? (
          <div className="rounded-[var(--radius-md)] border border-success-300 bg-success-100/80 px-4 py-3 text-sm text-success-600">
            Registro exitoso. Te redirigiremos en un momento...
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label htmlFor="id" className="text-sm font-medium text-[var(--text-primary)]">
              Número de cédula
            </label>
            <input
              id="id"
              name="id"
              inputMode="numeric"
              maxLength={10}
              placeholder="0000000000"
              value={formState.id}
              onChange={(event) =>
                handleChange("id")(event.target.value.replace(/\D/g, "").slice(0, 10))
              }
              aria-invalid={Boolean(fieldErrors.id)}
              aria-describedby={fieldErrors.id ? "id-error" : undefined}
              className="w-full"
            />
            <div className="flex items-center justify-between text-xs text-[var(--text-tertiary)]">
              <span>
                {remainingDigits > 0
                  ? `${remainingDigits} dígitos restantes`
                  : "10 dígitos completos"}
              </span>
              {fieldErrors.id ? (
                <span id="id-error" className="text-danger-500">
                  {fieldErrors.id}
                </span>
              ) : null}
            </div>
          </div>

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
              placeholder="tu@correo.com"
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
        </div>

        <div className="space-y-1.5">
          <label
            htmlFor="name"
            className="text-sm font-medium text-[var(--text-primary)]"
          >
            Nombre completo
          </label>
          <input
            id="name"
            name="name"
            placeholder="Tu nombre y apellidos"
            value={formState.name}
            onChange={(event) => handleChange("name")(event.target.value)}
            aria-invalid={Boolean(fieldErrors.name)}
            aria-describedby={fieldErrors.name ? "name-error" : undefined}
            className="w-full"
          />
          {fieldErrors.name ? (
            <p id="name-error" className="text-xs text-danger-500">
              {fieldErrors.name}
            </p>
          ) : null}
        </div>

        <div className="space-y-1.5">
          <label
            htmlFor="address"
            className="text-sm font-medium text-[var(--text-primary)]"
          >
            Dirección de residencia
          </label>
          <input
            id="address"
            name="address"
            placeholder="Calle, número y ciudad"
            value={formState.address}
            onChange={(event) => handleChange("address")(event.target.value)}
            aria-invalid={Boolean(fieldErrors.address)}
            aria-describedby={fieldErrors.address ? "address-error" : undefined}
            className="w-full"
          />
          {fieldErrors.address ? (
            <p id="address-error" className="text-xs text-danger-500">
              {fieldErrors.address}
            </p>
          ) : null}
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label
              htmlFor="password"
              className="text-sm font-medium text-[var(--text-primary)]"
            >
              Contraseña
            </label>
            <input
              id="password"
              name="password"
              type="password"
              placeholder="••••••••"
              minLength={8}
              value={formState.password}
              onChange={(event) => handleChange("password")(event.target.value)}
              aria-invalid={Boolean(fieldErrors.password)}
              aria-describedby={fieldErrors.password ? "password-error" : undefined}
              className="w-full"
            />
            {fieldErrors.password ? (
              <p id="password-error" className="text-xs text-danger-500">
                {fieldErrors.password}
              </p>
            ) : (
              <p className="text-xs text-[var(--text-tertiary)]">
                Debe tener al menos 8 caracteres y combinar letras y números.
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="confirmPassword"
              className="text-sm font-medium text-[var(--text-primary)]"
            >
              Confirmar contraseña
            </label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              placeholder="Repite tu contraseña"
              value={formState.confirmPassword}
              onChange={(event) =>
                handleChange("confirmPassword")(event.target.value)
              }
              aria-invalid={Boolean(fieldErrors.confirmPassword)}
              aria-describedby={
                fieldErrors.confirmPassword ? "confirmPassword-error" : undefined
              }
              className="w-full"
            />
            {fieldErrors.confirmPassword ? (
              <p id="confirmPassword-error" className="text-xs text-danger-500">
                {fieldErrors.confirmPassword}
              </p>
            ) : null}
          </div>
        </div>

        <Button
          type="submit"
          className="w-full"
          disabled={isSubmitting || success}
          isLoading={isSubmitting}
        >
          {isSubmitting ? "Registrando..." : "Crear cuenta"}
        </Button>
      </form>
    </AuthShell>
  );
}

