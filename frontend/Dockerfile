# Install exactly what package-lock.json pins.
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# The tests run on every image build, so CI's Docker build stage fails on a
# broken page. Then the production bundle is built. API_URL is fixed into the
# /api rewrite at build time (see next.config.mjs).
FROM deps AS build
ARG API_URL=http://upskill-api:8000
ENV API_URL=$API_URL NEXT_TELEMETRY_DISABLED=1
COPY . .
RUN npm test -- --ci && npm run build

# Only the standalone server and static assets are shipped, not node_modules
# or the tests.
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static

# The node image ships an unprivileged "node" user; do not run as root.
USER node

EXPOSE 3000

CMD ["node", "server.js"]
