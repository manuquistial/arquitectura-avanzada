"use client";

import { useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { apiService } from '@/lib/api';

interface SearchResult {
  id: string;
  title: string;
  description?: string;
  filename: string;
  created_at: string;
  score: number;
}

export default function SearchDocumentsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim()) {
      setError('Por favor ingresa un término de búsqueda');
      return;
    }

    setLoading(true);
    setError(null);
    setSearched(true);

    try {
      const citizenId = session?.user?.id;
      const searchResults = await apiService.searchDocuments(query, citizenId);
      
      if (searchResults.documents) {
        setResults(searchResults.documents);
      } else if (Array.isArray(searchResults)) {
        setResults(searchResults);
      } else {
        setResults([]);
      }
    } catch (err) {
      console.error('Error searching documents:', err);
      setError('Error al buscar documentos');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Cargando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            🔍 Buscar Documentos
          </h1>
          <p className="mt-2 text-gray-600">
            Busca documentos por título, descripción o contenido
          </p>
        </div>

        {/* Search Form */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <form onSubmit={handleSearch} className="flex gap-4">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar documentos..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md font-medium transition-colors disabled:opacity-50"
            >
              {loading ? 'Buscando...' : '🔍 Buscar'}
            </button>
          </form>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Results */}
        {searched && (
          <div>
            {loading ? (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <p className="mt-4 text-gray-600">Buscando documentos...</p>
              </div>
            ) : results.length === 0 ? (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
                <div className="text-6xl mb-4">🔍</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  No se encontraron documentos
                </h3>
                <p className="text-gray-600">
                  Intenta con otros términos de búsqueda
                </p>
              </div>
            ) : (
              <div>
                <div className="mb-4 text-sm text-gray-600">
                  Se encontraron {results.length} documento{results.length !== 1 ? 's' : ''}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {results.map((result) => (
                    <div
                      key={result.id}
                      className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => router.push(`/documents?highlight=${result.id}`)}
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div className="text-3xl">📄</div>
                        {result.score && (
                          <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                            {Math.round(result.score * 100)}% relevante
                          </span>
                        )}
                      </div>
                      
                      <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2">
                        {result.title}
                      </h3>
                      
                      {result.description && (
                        <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                          {result.description}
                        </p>
                      )}
                      
                      <p className="text-xs text-gray-500 mb-2">
                        {result.filename}
                      </p>
                      
                      <p className="text-xs text-gray-400">
                        {formatDate(result.created_at)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Empty State (before search) */}
        {!searched && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Busca tus documentos
            </h3>
            <p className="text-gray-600 mb-6">
              Ingresa un término de búsqueda para encontrar documentos
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

