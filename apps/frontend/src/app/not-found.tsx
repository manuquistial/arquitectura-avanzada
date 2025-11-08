import Link from 'next/link';
import { Breadcrumbs } from '@/components/ui/Breadcrumbs';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-6 py-12">
      <div className="max-w-md w-full space-y-6 text-center">
        <div className="flex justify-center">
          <Breadcrumbs
            items={[
              { label: 'Inicio', href: '/' },
              { label: 'Página no encontrada' },
            ]}
          />
        </div>
        <h1 className="text-6xl font-bold text-gray-900">404</h1>
        <p className="text-xl text-gray-600">
          No pudimos encontrar la página que buscabas.
        </p>
        <div className="space-y-4">
          <Link
            href="/"
            className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
          >
            Ir al inicio
          </Link>
        </div>
      </div>
    </div>
  );
}

