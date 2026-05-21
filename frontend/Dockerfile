# syntax=docker/dockerfile:1
# Production: multi-stage, Next.js standalone (DOCKER_BUILD=1 в next.config)

FROM node:20-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM node:20-bookworm-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_API_V1_URL
ARG NEXT_PUBLIC_SITE_URL
ARG NEXT_PUBLIC_USE_AUTH_COOKIES=1
ARG NEXT_PUBLIC_JWT_COOKIE_ACCESS_NAME=ringoo_access
ARG NEXT_PUBLIC_JWT_COOKIE_REFRESH_NAME=ringoo_refresh

ENV DOCKER_BUILD=1 \
  NEXT_TELEMETRY_DISABLED=1 \
  NEXT_PUBLIC_API_V1_URL=${NEXT_PUBLIC_API_V1_URL} \
  NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL} \
  NEXT_PUBLIC_USE_AUTH_COOKIES=${NEXT_PUBLIC_USE_AUTH_COOKIES} \
  NEXT_PUBLIC_JWT_COOKIE_ACCESS_NAME=${NEXT_PUBLIC_JWT_COOKIE_ACCESS_NAME} \
  NEXT_PUBLIC_JWT_COOKIE_REFRESH_NAME=${NEXT_PUBLIC_JWT_COOKIE_REFRESH_NAME}

RUN npm run build

FROM node:20-bookworm-slim AS runner
WORKDIR /app

ENV NODE_ENV=production \
  NEXT_TELEMETRY_DISABLED=1 \
  PORT=3000 \
  HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 --ingroup nodejs nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:3000').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
