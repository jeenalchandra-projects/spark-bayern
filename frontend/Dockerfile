# =============================================================================
# Dockerfile — Frontend (two-stage build)
# =============================================================================
# WHAT IS A TWO-STAGE BUILD?
# Stage 1 (builder): Has Node.js installed. Runs "npm run build" which compiles
#   our React code into static HTML/CSS/JS files in the "dist" folder.
# Stage 2 (final): Has only Nginx (a lightweight web server). Copies the
#   compiled files from Stage 1. No Node.js in the final image — smaller and safer.
#
# WHY THIS IS BETTER:
# The final Docker image doesn't contain Node.js, npm, or any build tools.
# It's just a minimal web server serving static files. Smaller = faster = safer.
# =============================================================================

# --- Stage 1: Build ---
FROM node:20-slim AS builder
WORKDIR /app

# Copy package files first (for Docker layer caching)
COPY package*.json ./
RUN npm ci --silent

# Accept build argument for the API URL
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

# Copy source and build
COPY . .
RUN npm run build

# --- Stage 2: Serve ---
FROM nginx:alpine

# Copy built files from Stage 1
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config for single-page app (handles React Router if added later)
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { try_files $uri $uri/ /index.html; } \
    gzip on; \
    gzip_types text/plain text/css application/json application/javascript; \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
