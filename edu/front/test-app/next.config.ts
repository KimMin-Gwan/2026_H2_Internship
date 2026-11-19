import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // /api 로 시작하는 요청을 FastAPI(8100)로 넘긴다
  async rewrites() {
    return [{ source: "/api/:path*", destination: "http://localhost:8100/api/:path*" }];
  },
};

export default nextConfig;