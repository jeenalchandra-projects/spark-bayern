# =============================================================================
# Dockerfile — Frontend (runtime-configurable API URL)
# =============================================================================
# THE PROBLEM WE'RE SOLVING:
# React apps built with Vite bake environment variables into the JavaScript
# at build time. This means we'd need to know the API Gateway URL BEFORE
# building the Docker image — a chicken-and-egg problem on Railway.
#
# THE SOLUTION — Runtime configuration via nginx:
# Stage 1: Build React with a PLACEHOLDER for the API URL
# Stage 2: Nginx serves a tiny config.js file that sets window.SPARK_API_URL
#          at RUNTIME using an environment variable injected by Railway.
#          The React app reads this window variable first, then falls back
#          to the build-time value.
#
# This way: build once, configure at runtime. The same Docker image works
# for local development AND Railway deployment — just set the env var.
# =============================================================================

# --- Stage 1: Build React app ---
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --silent
COPY . .

# Build with a placeholder — the real URL is injected at runtime
ENV VITE_API_URL=__RUNTIME_API_URL__
RUN npm run build

# --- Stage 2: Runtime nginx server ---
FROM nginx:alpine

# Install envsubst (part of gettext) — replaces ${VARIABLE} in files
# This is what allows runtime env var injection
RUN apk add --no-cache gettext

# Copy built React files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our nginx config template
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the runtime config script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

# Use our entrypoint script (injects env vars, then starts nginx)
CMD ["/docker-entrypoint.sh"]
