"use client";

import { useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import {
  CalendarClock,
  Mail,
  User,
} from "lucide-react";

import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { StatTile } from "@/components/ui/StatTile";

export default function AccountPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [router, status]);

  if (status === "loading" || !session) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-12 w-12 animate-spin rounded-full border-2 border-primary-100 border-t-primary-500" />
          <p className="text-sm text-[var(--text-tertiary)]">Cargando detalles de tu cuenta…</p>
        </div>
      </div>
    );
  }

  const user = session.user ?? {};
  const initials =
    user.name
      ?.split(" ")
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || user.email?.[0]?.toUpperCase() || "CC";

  const roles = user.roles ?? ["usuario"];
  const citizenId = user.citizen_id ?? user.id ?? "—";

  return (
    <>
      <PageHeader
        breadcrumbs={[
          { label: 'Inicio', href: '/dashboard' },
          { label: 'Mi cuenta' },
        ]}
        title="Mi cuenta"
        description="Consulta la información relacionada con tu perfil y revisa tus accesos en Carpeta Ciudadana."
        actions={[]}
      />

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <StatTile
          label="Último acceso"
          value={
            user.lastLogin
              ? new Date(user.lastLogin).toLocaleString("es-CO")
              : "Sin registro"
          }
          icon={<CalendarClock className="h-5 w-5" />}
          tone="info"
          helperText="Mantén tu cuenta protegida"
        />
      </div>

      <div className="grid grid-cols-1 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Información personal</CardTitle>
            <CardDescription>Estos datos se utilizan para personalizar la experiencia.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div className="flex items-center gap-4 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-muted)] px-4 py-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-500 text-lg font-semibold text-white">
                {initials}
              </div>
              <div>
                <p className="text-sm font-semibold text-[var(--text-primary)]">
                  {user.name ?? "Usuario"}
                </p>
                <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                  <Mail className="h-4 w-4" />
                  {user.email ?? "user@example.com"}
                </div>
              </div>
            </div>

            <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-muted)] px-4 py-4">
              <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
                Identificador ciudadano
              </span>
              <p className="mt-2 text-base font-semibold text-[var(--text-primary)]">
                {citizenId}
              </p>
            </div>

            <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--surface-muted)] px-4 py-4">
              <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
                Roles
              </span>
              <div className="mt-2 flex flex-wrap gap-2">
                {roles.map((role) => (
                  <Badge key={role} variant="info">
                    {role}
                  </Badge>
                ))}
              </div>
            </div>

          </CardContent>
        </Card>
      </div>
    </>
  );
}

