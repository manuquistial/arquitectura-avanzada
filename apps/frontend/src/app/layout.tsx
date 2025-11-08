import type { Metadata } from 'next';
import { Providers } from './providers';
import { ToastProvider } from '@/components/ToastContainer';
import ErrorBoundary from '@/components/ErrorBoundary';
import Navigation from '@/components/Navigation';
import { cn } from '@/lib/utils';
import './globals.css';

// Use system fonts for Docker builds to avoid Google Fonts issues
const fontClass = 'font-sans';

export const metadata: Metadata = {
  title: 'Carpeta Ciudadana',
  description: 'Sistema de Carpeta Ciudadana',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es-CO">
      <body className={cn(fontClass, 'bg-[var(--surface-background)] text-[var(--text-secondary)]')}>
        <ErrorBoundary>
          <Providers>
            <ToastProvider>
              <Navigation />
              <main className="min-h-[calc(100vh-4rem)] bg-white px-4 py-10 sm:px-6 lg:px-8">
                <div className="mx-auto flex w-full max-w-7xl flex-col gap-10">
                  {children}
                </div>
              </main>
            </ToastProvider>
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}
