'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, FileText } from 'lucide-react';
import { api } from '@/lib/api';

interface SearchResult {
  id: string;
  title: string;
  description?: string;
  filename: string;
  created_at: string;
  score: number;
}

export default function SearchPage() {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setSearched(true);

    try {
      // TODO: Implement OpenSearch integration
      // const response = await api.get(`/api/metadata/search?q=${encodeURIComponent(query)}`);
      // setResults(response.data.results);

      // Mock data for now
      setResults([
        {
          id: '1',
          title: 'Diploma de Grado',
          description: 'Universidad Nacional de Colombia',
          filename: 'diploma.pdf',
          created_at: new Date().toISOString(),
          score: 0.95,
        },
      ]);
    } catch (err) {
      console.error('Search error:', err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">
            Buscar Documentos
          </h1>
          <button
            onClick={() => router.push('/dashboard')}
            className="btn-secondary"
          >
            Volver
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Search Form */}
        <form onSubmit={handleSearch} className="card mb-8">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-3 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Buscar por título, descripción o contenido..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full pl-10"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="btn-primary"
            >
              {loading ? 'Buscando...' : 'Buscar'}
            </button>
          </div>

          <div className="mt-4 text-sm text-gray-600">
            <p>Ejemplos de búsqueda:</p>
            <ul className="list-disc list-inside mt-2">
              <li>diploma</li>
              <li>cédula ciudadanía</li>
              <li>certificado laboral</li>
            </ul>
          </div>
        </form>

        {/* Results */}
        {searched && (
          <div>
            <h2 className="text-lg font-semibold mb-4">
              {loading
                ? 'Buscando...'
                : `${results.length} resultado${results.length !== 1 ? 's' : ''} encontrado${results.length !== 1 ? 's' : ''}`}
            </h2>

            {results.length === 0 && !loading && (
              <div className="text-center py-12">
                <FileText className="w-16 h-16 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600">
                  No se encontraron documentos que coincidan con tu búsqueda
                </p>
              </div>
            )}

            <div className="space-y-4">
              {results.map((result) => (
                <div
                  key={result.id}
                  className="card hover:shadow-lg transition-shadow cursor-pointer"
                  onClick={() => router.push(`/documents?highlight=${result.id}`)}
                >
                  <div className="flex items-start gap-4">
                    <FileText className="w-10 h-10 text-blue-600 flex-shrink-0" />
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {result.title}
                      </h3>
                      {result.description && (
                        <p className="text-gray-600 mt-1">
                          {result.description}
                        </p>
                      )}
                      <div className="flex gap-4 mt-2 text-sm text-gray-500">
                        <span>{result.filename}</span>
                        <span>
                          {new Date(result.created_at).toLocaleDateString(
                            'es-CO'
                          )}
                        </span>
                        <span>Relevancia: {(result.score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

