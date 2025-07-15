/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  
  // Environment configuration
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:{{cookiecutter.api_port}}',
    NEXT_PUBLIC_APP_NAME: '{{cookiecutter.project_name}}',
    NEXT_PUBLIC_APP_VERSION: '{{cookiecutter.version}}',
  },

  // Image optimization
  images: {
    domains: [
      'localhost',
      // Add your image domains here
    ],
  },

  // Headers for security
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },

  // Redirects
  async redirects() {
    return [
      {
        source: '/home',
        destination: '/',
        permanent: true,
      },
    ];
  },

  // Webpack configuration
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // Important: return the modified config
    return config;
  },

  // TypeScript configuration
  typescript: {
    // Dangerously allow production builds to successfully complete even if
    // your project has type errors.
    ignoreBuildErrors: false,
  },

  // ESLint configuration
  eslint: {
    // Warning: This allows production builds to successfully complete even if
    // your project has ESLint errors.
    ignoreDuringBuilds: false,
  },

  // Build output configuration
  output: 'standalone',
  
  // Compression
  compress: true,
  
  // Generate build ID
  generateBuildId: async () => {
    return `{{cookiecutter.project_slug}}-${new Date().getTime()}`;
  },
};

module.exports = nextConfig;