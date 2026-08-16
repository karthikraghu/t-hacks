import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Proxy API calls through Next so a single tunnel/LAN origin serves both the
  // frontend and the FastAPI backend without cross-origin requests. Active only
  // when NEXT_PUBLIC_API_URL is set to "" (relative URLs); local dev with the
  // default http://localhost:8000 is unaffected.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;

