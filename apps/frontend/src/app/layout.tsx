import type { Metadata } from 'next';
import { Montserrat } from 'next/font/google';
import { Providers } from './providers';
import { ToastProvider } from '@/components/ToastContainer';
import ErrorBoundary from '@/components/ErrorBoundary';
import Navigation from '@/components/Navigation';
import './globals.css';

const montserrat = Montserrat({ 
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-montserrat',
  preload: true,
});

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
      <body className={`${montserrat.variable} ${montserrat.className}`}>
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

