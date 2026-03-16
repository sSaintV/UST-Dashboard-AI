/** @type {import('next').NextConfig} */
const nextConfig = {
  /**
   * Proxy /api/* to the FastAPI backend running on localhost:8000.
   * This keeps all requests same-origin from the browser's perspective,
   * avoiding any cross-origin issues and keeping the CORS surface minimal.
   */
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
