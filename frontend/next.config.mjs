// The browser calls /api/* on this origin and Next forwards it to the API, so
// the API needs no CORS rules and the token is never sent to another origin.
// Rewrites are fixed when the app is built: API_URL is a build-time setting,
// defaulting to the API's compose service name.
const apiUrl = process.env.API_URL ?? "http://upskill-api:8000";

/** @type {import("next").NextConfig} */
const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "no-referrer" },
        ],
      },
    ];
  },
};

export default nextConfig;
