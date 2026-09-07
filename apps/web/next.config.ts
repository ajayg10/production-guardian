import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: false,
  experimental: {
    // Suppress hydration warnings from browser extensions that inject attributes
    // like bis_skin_checked="1" (Bitdefender, etc.) into DOM nodes before React hydrates
  },
};

export default nextConfig;
