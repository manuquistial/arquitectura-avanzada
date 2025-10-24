/** @type {import('next').NextConfig} */
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
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8011',
    NEXT_PUBLIC_ENVIRONMENT: process.env.NODE_ENV || 'development',
  },
  
  // Security Headers disabled for HTTP deployment
  async headers() {
    return []
  },
  
  // Production optimizations
  swcMinify: true,
  compress: true,  // Enable gzip compression
  poweredByHeader: false,  // Remove X-Powered-By header
  
  // Bundle optimization
  webpack: (config, { isServer }) => {
    if (!isServer) {
      // Optimize client bundle
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      };
    }
    return config;
  },
  
  // Image optimization
  images: {
    domains: ['localhost'],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60,  // Cache images for 1 minute
  },
  
  // Output optimization
  output: 'standalone',  // Enable standalone output for Docker
};

module.exports = nextConfig;

