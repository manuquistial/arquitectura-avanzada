import type { Metadata } from 'next';
import { Providers } from './providers';
import { ToastProvider } from '@/components/ToastContainer';
import ErrorBoundary from '@/components/ErrorBoundary';
import Navigation from '@/components/Navigation';
import './globals.css';

// Use system fonts for Docker builds to avoid Google Fonts issues
const fontClass = 'font-sans';

export const metadata: Metadata = {
  title: 'Carpeta Ciudadana',
  description: 'Sistema de Carpeta Ciudadana - Operador Azure',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es-CO">
      <body className={fontClass}>
        <ErrorBoundary>
          <Providers>
            <ToastProvider>
              <Navigation />
              <main>{children}</main>
            </ToastProvider>
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}

