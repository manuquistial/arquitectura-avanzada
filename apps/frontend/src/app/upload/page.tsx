'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import { Upload, X } from 'lucide-react';
import { useSession } from 'next-auth/react';
import { apiService } from '@/lib/api';

export default function UploadPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setError('');
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles: 1,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
  });

  const handleUpload = async () => {
    if (!file || !title || !session?.user?.id) {
      setError('Por favor selecciona un archivo, proporciona un título y asegúrate de estar autenticado');
      return;
    }

    setUploading(true);
    setError('');
    setProgress(0);

    try {
      setProgress(30);

      // Upload directly through backend to avoid CORS issues
      const result = await apiService.uploadDocumentDirect(
        file,
        session.user.id,
        title,
        description
      );

      setProgress(100);

      // Success
      setTimeout(() => {
        router.push('/documents');
      }, 1000);
    } catch (err) {
      console.error('Upload error:', err);
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(error.response?.data?.detail || error.message || 'Error al subir el documento');
      setProgress(0);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold text-gray-900">
            Subir Documento
          </h1>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="card space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
              isDragActive
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            {file ? (
              <div className="flex items-center justify-center gap-2">
                <p className="text-gray-700">{file.name}</p>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                  }}
                  className="text-red-600 hover:text-red-800"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <>
                <p className="text-gray-700 mb-2">
                  Arrastra un archivo aquí o haz clic para seleccionar
                </p>
                <p className="text-gray-500 text-sm">
                  PDF, imágenes, Word (máx. 10MB)
                </p>
              </>
            )}
          </div>

          {/* Title */}
          <div>
            <input
              type="text"
              placeholder="Título del documento"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full"
            />
          </div>

          {/* Description */}
          <div>
            <textarea
              placeholder="Descripción (opcional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full"
            />
          </div>

          {/* Progress */}
          {uploading && (
            <div>
              <div className="bg-gray-200 rounded-full h-2 mb-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-sm text-gray-600 text-center">
                Subiendo... {progress}%
              </p>
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-4">
            <button
              onClick={() => router.back()}
              className="flex-1 btn-secondary"
              disabled={uploading}
            >
              Cancelar
            </button>
            <button
              onClick={handleUpload}
              className="flex-1 btn-primary"
              disabled={!file || !title || uploading}
            >
              {uploading ? 'Subiendo...' : 'Subir Documento'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

