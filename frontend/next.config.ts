import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

// eslint-disable-next-line @typescript-eslint/no-require-imports
const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: process.env.ANALYZE === "true",
});

function cspConnectSrc(): string {
  const sentry =
    process.env.NEXT_PUBLIC_SENTRY_DSN?.trim() ?
      " https://*.ingest.sentry.io https://*.ingest.de.sentry.io"
    : "";
  const origins = new Set<string>(["'self'"]);
  if (isRelaxedLocalCsp()) {
    for (const o of devApiHttpOrigins()) origins.add(o);
  } else {
    const base =
      process.env.NEXT_PUBLIC_API_V1_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      "";
    try {
      if (base) origins.add(new URL(base).origin);
    } catch {
      /* ignore */
    }
  }
  return `${[...origins].join(" ")} ws: wss:${sentry}`;
}

/** Собирает http-origin API для CSP (dev: localhost + 127.0.0.1 + host из env). */
function devApiHttpOrigins(): string[] {
  const out = new Set<string>([
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://host.docker.internal:8000",
  ]);
  for (const raw of [
    process.env.NEXT_PUBLIC_API_URL,
    process.env.NEXT_PUBLIC_API_V1_URL?.replace(/\/api\/v1\/?$/i, ""),
  ]) {
    if (!raw?.trim()) continue;
    try {
      const u = new URL(raw.trim());
      if (u.protocol === "http:") out.add(u.origin);
    } catch {
      /* ignore */
    }
  }
  return [...out];
}

/** Локальная разработка (Docker / localhost API). */
function isRelaxedLocalCsp(): boolean {
  if (process.env.RINGOO_RELAX_CSP === "1") return true;
  if (process.env.NODE_ENV === "development") return true;
  const api = `${process.env.NEXT_PUBLIC_API_URL ?? ""} ${process.env.NEXT_PUBLIC_API_V1_URL ?? ""}`;
  return /localhost|127\.0\.0\.1|host\.docker\.internal/i.test(api);
}

/** Локальный backend отдаёт медиа по http — без http: в img-src браузер блокирует /media/. */
function cspImgSrc(): string {
  const base = "img-src 'self' data: blob: https:";
  if (!isRelaxedLocalCsp()) {
    return base;
  }
  // http: (scheme) + явные origin — покрывает localhost/127.0.0.1 и любые порты dev API
  return `${base} http: ${devApiHttpOrigins().join(" ")}`;
}

/** Домены Яндекс.Карт API 2.1 (скрипт, тайлы, подсказки, статика). */
const YANDEX_MAPS_SCRIPT = "https://api-maps.yandex.ru";
const YANDEX_MAPS_STATIC = "https://yastatic.net";
const YANDEX_MAPS_CONNECT =
  "https://api-maps.yandex.ru https://yandex.ru https://*.yandex.ru https://*.yandex.net https://yastatic.net";

/** CSP собирается при старте сервера (учитывает env из Docker/.env.local). */
function buildContentSecurityPolicy(): string {
  return [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline' 'unsafe-eval' ${YANDEX_MAPS_SCRIPT} ${YANDEX_MAPS_STATIC}`,
    `style-src 'self' 'unsafe-inline' ${YANDEX_MAPS_STATIC}`,
    cspImgSrc(),
    `font-src 'self' data: ${YANDEX_MAPS_STATIC}`,
    `connect-src ${cspConnectSrc()} ${YANDEX_MAPS_CONNECT}`,
    "worker-src 'self' blob:",
    "frame-src 'self' https://sketchfab.com https://*.sketchfab.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

const nextConfig: NextConfig = {
  // Production Docker-образ (frontend/Dockerfile, DOCKER_BUILD=1)
  ...(process.env.DOCKER_BUILD === "1" ? { output: "standalone" as const } : {}),
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  async redirects() {
    return [
      { source: '/sitemap', destination: '/site-map', permanent: true },
      { source: '/order-track', destination: '/order-status', permanent: true },
    ];
  },
  async headers() {
    const contentSecurityPolicy = buildContentSecurityPolicy();
    const securityHeaders: { key: string; value: string }[] = [
      {
        key: "Permissions-Policy",
        value:
          'accelerometer=(self "https://sketchfab.com"), gyroscope=(self "https://sketchfab.com"), fullscreen=(self "https://sketchfab.com")',
      },
      {
        key: "Content-Security-Policy",
        value: contentSecurityPolicy,
      },
    ];
    if (process.env.CSP_REPORT_ONLY === "1") {
      securityHeaders.push({
        key: "Content-Security-Policy-Report-Only",
        value: contentSecurityPolicy,
      });
    }
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
  images: {
    // Dev/Docker: оптимизатор в контейнере не достучится до localhost:8000 на хосте
    unoptimized: process.env.NODE_ENV === "development",
    // Без этого fetch к http://localhost:8000/media/... резолвится в 127.0.0.1 → ImageError 400
    dangerouslyAllowLocalIP:
      process.env.NODE_ENV === "development" ||
      process.env.IMAGES_ALLOW_LOCAL_IP === "true",
    qualities: [75, 80, 90],
    localPatterns: [
      { pathname: "/magazins/**" },
      { pathname: "/menegers/**" },
    ],
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/media/**",
      },
      {
        protocol: "http",
        hostname: "127.0.0.1",
        port: "8000",
        pathname: "/media/**",
      },
      {
        protocol: "http",
        hostname: "web",
        port: "8000",
        pathname: "/media/**",
      },
      {
        protocol: "http",
        hostname: "host.docker.internal",
        port: "8000",
        pathname: "/media/**",
      },
      {
        protocol: "https",
        hostname: "**",
        pathname: "/media/**",
      },
    ],
    formats: ["image/avif", "image/webp"],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
    minimumCacheTTL: 3600,
  },
  compress: true,
};

export default withSentryConfig(withBundleAnalyzer(nextConfig), {
  silent: true,
  sourcemaps: {
    disable: true,
  },
});
