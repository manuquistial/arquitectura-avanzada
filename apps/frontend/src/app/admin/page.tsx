"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Cog,
  ShieldCheck,
  Shuffle,
  Users,
} from "lucide-react";

import { PageHeader } from "@/components/ui/PageHeader";
import { StatTile } from "@/components/ui/StatTile";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

const adminActions = [
  {
    title: "Gestión de usuarios",
    description: "Administra ciudadanos registrados y actualiza sus permisos.",
    href: "/admin/users",
    icon: "users",
  },
  {
    title: "Operadores MinTIC",
    description: "Registra y verifica operadores habilitados en el hub MinTIC.",
    href: "/admin/mintic-operators",
    icon: "shield",
  },
  {
    title: "Configuración del sistema",
    description: "Define Operator ID y parámetros globales de Carpeta Ciudadana.",
    href: "/admin/system-config",
    icon: "cog",
  },
];

export default function AdminPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "loading") {
      return;
    }
    if (!session) {
      router.push("/login");
      return;
    }

    const roles = session.user?.roles ?? [];
    if (!roles.includes("admin") && !roles.includes("mintic")) {
      router.push("/dashboard");
    }
  }, [router, session, status]);

  if (status === "loading") {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-12 w-12 animate-spin rounded-full border-2 border-primary-100 border-t-primary-500" />
      </div>
    );
  }

  return (
    <>
      <PageHeader
        breadcrumbs={[
          { label: 'Inicio', href: '/dashboard' },
          { label: 'Administración' },
        ]}
        title="Panel de administración"
        description="Coordina operadores, usuarios y configuraciones críticas de la Carpeta Ciudadana."
        actions={[]}
      />

      <Card className="mt-6 border-[var(--primary-100)] bg-white/90">
        <CardHeader>
          <CardTitle>Gestión administrativa</CardTitle>
          <CardDescription>
            Accede rápidamente a las áreas más usadas por los administradores y operadores.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {adminActions.map((action) => (
            <div
              key={action.title}
              className="flex flex-col gap-4 rounded-[var(--radius-md)] border border-[var(--primary-100)] bg-white/85 p-5 shadow-soft shadow-primary-900/5 transition-transform hover:-translate-y-1 hover:shadow-lg"
            >
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    'flex h-10 w-10 items-center justify-center rounded-xl text-white shadow-sm',
                    action.icon === 'users' && 'bg-[var(--info-500)]',
                    action.icon === 'shield' && 'bg-[var(--success-500)]',
                    action.icon === 'cog' && 'bg-[var(--primary-500)]'
                  )}
                >
                  {action.icon === "users" && <Users className="h-5 w-5" />}
                  {action.icon === "shield" && <ShieldCheck className="h-5 w-5" />}
                  {action.icon === "cog" && <Cog className="h-5 w-5" />}
                </div>
                <div>
                  <p className="text-sm font-semibold text-[var(--text-primary)]">{action.title}</p>
                  <p className="text-xs text-[var(--text-tertiary)]">{action.description}</p>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-[var(--text-tertiary)]" />
                <Button
                  variant="secondary"
                  size="sm"
                  href={action.href}
                  icon={<ArrowRight className="h-4 w-4" />}
                  iconPosition="right"
                  className="border-none bg-white/70 text-[var(--primary-600)] hover:bg-white"
                >
                  Abrir
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </>
  );
}
