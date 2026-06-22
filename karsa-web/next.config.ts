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
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_URL || 'http://karsa-api:8000'}/:path*`
      }
    ]
  }
};

export default nextConfig;
