import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.BACKEND_API_URL || 'http://app:8000'}/:path*`, // Proxy to Backend
      },
    ]
  },
};

export default nextConfig;
