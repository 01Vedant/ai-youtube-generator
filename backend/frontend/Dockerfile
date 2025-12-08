# Frontend Dockerfile - React + Vite
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies with cache optimization
RUN npm ci --prefer-offline --no-audit

# Copy source
COPY . .

# Build production bundle
RUN npm run build

# Production image
FROM nginx:1.25-alpine

# Install curl for healthcheck
RUN apk add --no-cache curl

# Create non-root user
RUN addgroup -g 1000 appuser && adduser -D -u 1000 -G appuser appuser

# Copy built assets with proper ownership
COPY --from=builder --chown=appuser:appuser /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Use non-root user
USER appuser

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
