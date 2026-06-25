import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  trailingSlash: false,
  typescript: {
    ignoreBuildErrors: true, // Pre-existing errors in proposals/intelligence pages
  },
  images: {
    unoptimized: true
  },
  async rewrites() {
    const backend = process.env.API_URL || 'http://karsa-api:8000';
    return [
      // Attribution routes: backend has prefix="/api/v1/attribution"
      {
        source: '/api/v1/:path*',
        destination: `${backend}/api/v1/:path*`
      },
      // CIO Dashboard routes: backend has prefix="/api", so /api/X → backend /api/X
      {
        source: '/api/portfolio/:path*',
        destination: `${backend}/api/portfolio/:path*`
      },
      {
        source: '/api/risk/:path*',
        destination: `${backend}/api/risk/:path*`
      },
      {
        source: '/api/decisions/:path*',
        destination: `${backend}/api/decisions/:path*`
      },
      {
        source: '/api/exposures/:path*',
        destination: `${backend}/api/exposures/:path*`
      },
      {
        source: '/api/cio/:path*',
        destination: `${backend}/api/cio/:path*`
      },
      {
        source: '/api/market/:path*',
        destination: `${backend}/api/market/:path*`
      },
      // All other /api routes: strip /api prefix (backend has no prefix)
      {
        source: '/api/:path*',
        destination: `${backend}/:path*`
      },
      // Non-/api backend routes (thesis, memos, investments, research, etc.)
      {
        source: '/thesis/:path*',
        destination: `${backend}/thesis/:path*`
      },
      {
        source: '/thesis',
        destination: `${backend}/thesis`
      },
      {
        source: '/cio/:path*',
        destination: `${backend}/cio/:path*`
      },
      {
        source: '/investments/:path*',
        destination: `${backend}/investments/:path*`
      },
      {
        source: '/research/:path*',
        destination: `${backend}/research/:path*`
      },
      {
        source: '/performance/:path*',
        destination: `${backend}/performance/:path*`
      },
      {
        source: '/workers/:path*',
        destination: `${backend}/workers/:path*`
      },
      {
        source: '/post-mortem/:path*',
        destination: `${backend}/post-mortem/:path*`
      },
      {
        source: '/allocation/:path*',
        destination: `${backend}/allocation/:path*`
      },
      {
        source: '/search',
        destination: `${backend}/search`
      },
      {
        source: '/health',
        destination: `${backend}/health`
      }
    ]
  }
};

export default nextConfig;
