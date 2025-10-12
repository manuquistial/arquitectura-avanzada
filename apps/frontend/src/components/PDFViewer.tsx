"use client";

import { useState } from 'react';

interface PDFViewerProps {
  url: string;
  filename: string;
  onClose?: () => void;
}

export default function PDFViewer({ url, filename, onClose }: PDFViewerProps) {
  const [zoom, setZoom] = useState(100);
  const [page, setPage] = useState(1);
  const [totalPages] = useState(1); // TODO: Get from PDF metadata

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handlePrint = () => {
    const printWindow = window.open(url, '_blank');
    if (printWindow) {
      printWindow.addEventListener('load', () => {
        printWindow.print();
      });
    }
  };

  const zoomIn = () => {
    setZoom(prev => Math.min(prev + 25, 200));
  };

  const zoomOut = () => {
    setZoom(prev => Math.max(prev - 25, 50));
  };

  const resetZoom = () => {
    setZoom(100);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 z-50 flex flex-col">
      {/* Header */}
      <div className="bg-gray-900 text-white p-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold truncate max-w-md">
            📄 {filename}
          </h2>
        </div>

        <div className="flex items-center gap-2">
          {/* Zoom Controls */}
          <div className="flex items-center gap-2 bg-gray-800 rounded-lg p-1">
            <button
              onClick={zoomOut}
              className="px-3 py-1 hover:bg-gray-700 rounded transition-colors"
              title="Alejar"
            >
              −
            </button>
            <span className="px-3 py-1 min-w-[60px] text-center">
              {zoom}%
            </span>
            <button
              onClick={zoomIn}
              className="px-3 py-1 hover:bg-gray-700 rounded transition-colors"
              title="Acercar"
            >
              +
            </button>
            <button
              onClick={resetZoom}
              className="px-3 py-1 hover:bg-gray-700 rounded transition-colors"
              title="Restablecer zoom"
            >
              ↻
            </button>
          </div>

          {/* Page Navigation */}
          {totalPages > 1 && (
            <div className="flex items-center gap-2 bg-gray-800 rounded-lg p-1">
              <button
                onClick={() => setPage(prev => Math.max(1, prev - 1))}
                disabled={page === 1}
                className="px-3 py-1 hover:bg-gray-700 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ←
              </button>
              <span className="px-3 py-1">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 hover:bg-gray-700 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                →
              </button>
            </div>
          )}

          {/* Action Buttons */}
          <button
            onClick={handleDownload}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2"
          >
            ⬇️ Descargar
          </button>

          <button
            onClick={handlePrint}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors flex items-center gap-2"
          >
            🖨️ Imprimir
          </button>

          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            >
              ✕ Cerrar
            </button>
          )}
        </div>
      </div>

      {/* PDF Content */}
      <div className="flex-1 overflow-auto bg-gray-700 p-4">
        <div className="max-w-5xl mx-auto">
          <div 
            className="bg-white shadow-2xl"
            style={{ 
              transform: `scale(${zoom / 100})`,
              transformOrigin: 'top center',
              transition: 'transform 0.2s'
            }}
          >
            <iframe
              src={url}
              className="w-full h-[800px] border-none"
              title={filename}
            />
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-gray-900 text-white px-4 py-2 text-sm text-center">
        💡 Consejo: Usa Ctrl + Rueda del ratón para hacer zoom
      </div>
    </div>
  );
}

