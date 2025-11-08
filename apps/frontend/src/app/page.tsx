"use client";

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';

import LoginPage from './login/page';

export default function HomePage() {
  const router = useRouter();
  const { status } = useSession();

  useEffect(() => {
    if (status === 'authenticated') {
      router.replace('/dashboard');
    }
  }, [status, router]);

  if (status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--surface-background)]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-12 w-12 animate-spin rounded-full border-2 border-primary-100 border-t-primary-500" />
          <p className="text-sm text-[var(--text-tertiary)]">Preparando tu sesión…</p>
        </div>
      </div>
    );
  }

  if (status === 'authenticated') {
    return null;
  }

  return <LoginPage />;
}
