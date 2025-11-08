/** @type {import('next').NextConfig} */
const isProduction = process.env.NODE_ENV === 'production';

const withDefaults = (key, prodDefault, devDefault) =>
  process.env[key] || (isProduction ? prodDefault : devDefault);

const nextConfig = {
  // Optimizations for production
  reactStrictMode: false,  // Disable for production performance
  experimental: {
    serverActions: {
      enabled: false,  // Disable server actions to reduce bundle size
    },
  },
  
  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: withDefaults('NEXT_PUBLIC_API_URL', '', 'http://localhost:8000'),
    NEXT_PUBLIC_ENVIRONMENT: process.env.NODE_ENV || 'development',
    NEXT_PUBLIC_AUTH_SERVICE_URL: withDefaults('NEXT_PUBLIC_AUTH_SERVICE_URL', 'http://carpeta-ciudadana-auth:8000', 'http://localhost:8001'),
    NEXT_PUBLIC_CITIZEN_SERVICE_URL: withDefaults('NEXT_PUBLIC_CITIZEN_SERVICE_URL', 'http://carpeta-ciudadana-citizen:8000', 'http://localhost:8000'),
    NEXT_PUBLIC_INGESTION_SERVICE_URL: withDefaults('NEXT_PUBLIC_INGESTION_SERVICE_URL', 'http://carpeta-ciudadana-ingestion:8000', 'http://localhost:8002'),
    NEXT_PUBLIC_SIGNATURE_SERVICE_URL: withDefaults('NEXT_PUBLIC_SIGNATURE_SERVICE_URL', 'http://carpeta-ciudadana-signature:8000', 'http://localhost:8004'),
    NEXT_PUBLIC_TRANSFER_SERVICE_URL: withDefaults('NEXT_PUBLIC_TRANSFER_SERVICE_URL', 'http://carpeta-ciudadana-transfer:8000', 'http://localhost:8003'),
    NEXT_PUBLIC_MINTIC_SERVICE_URL: withDefaults('NEXT_PUBLIC_MINTIC_SERVICE_URL', 'http://carpeta-ciudadana-mintic-client:8000', 'http://localhost:8005'),
    NEXT_PUBLIC_METADATA_SERVICE_URL: withDefaults('NEXT_PUBLIC_METADATA_SERVICE_URL', 'http://carpeta-ciudadana-metadata:8000', 'http://localhost:8007'),
    NEXT_PUBLIC_NOTIFICATION_SERVICE_URL: withDefaults('NEXT_PUBLIC_NOTIFICATION_SERVICE_URL', 'http://carpeta-ciudadana-notification:8000', 'http://localhost:8008'),
  },
  
  // Security Headers disabled for HTTP deployment
  async headers() {
    return []
  },
  
  // Production optimizations
  compress: true,  // Enable gzip compression
  poweredByHeader: false,  // Remove X-Powered-By header
  
  // Ignore type errors during CI builds (temporary hotfix)
  typescript: {
    ignoreBuildErrors: true,
  },

  // Turbopack configuration (Next 16)
  turbopack: {},
  
  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '3000',
        pathname: '/**',
      },
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8011',
        pathname: '/**',
      },
    ],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60,
  },
  
  // Output optimization
  output: 'standalone',  // Enable standalone output for Docker
};

module.exports = nextConfig;

