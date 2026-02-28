# SWEN Frontend Dockerfile
# Multi-stage build: Node.js for building, nginx for serving

# ============================================
# Stage 1: Build the React application
# ============================================
FROM node:24-alpine AS builder

WORKDIR /app

# Copy package files first (better caching)
COPY services/frontend/package.json services/frontend/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY services/frontend/ ./

# Generate TanStack Router route tree (required before TypeScript build)
RUN npx @tanstack/router-cli generate

# Build the production bundle
RUN npm run build

# ============================================
# Stage 2: Serve built assets with nginx
# ============================================
FROM nginx:1.29-alpine AS runtime

ARG VERSION=dev

# Remove default nginx config and replace with ours
RUN rm /etc/nginx/conf.d/default.conf
COPY services/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx by default runs as root but serves as 'nginx' user
# run fully unprivileged
# Use port 3000 (non-privileged) as set in nginx.conf
RUN chown -R nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

USER nginx

LABEL org.opencontainers.image.title="swen-frontend" \
      org.opencontainers.image.description="SWEN Frontend" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.source="https://github.com/maltewinckler/swen"

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
