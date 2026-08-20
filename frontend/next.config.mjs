/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  agentRules: false,
  // Static export so Vercel can deploy from the monorepo root via vercel.json
  // without requiring the Root Directory UI setting.
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
