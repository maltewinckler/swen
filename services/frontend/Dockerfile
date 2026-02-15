# SWEN Frontend Dockerfile
# Multi-stage build: Node.js for building, Node.js for serving

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
# Stage 2: Serve built assets (vite preview)
# ============================================
FROM node:24-alpine AS runtime

WORKDIR /app

# Copy what we need to run `vite preview`
COPY --from=builder /app/package.json /app/package-lock.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/vite.config.ts ./

# Vite preview defaults to 4173 and binds to localhost; we override to 0.0.0.0:3000
EXPOSE 3000

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3000"]
