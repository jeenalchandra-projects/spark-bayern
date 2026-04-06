#!/bin/sh
# Railway injects $PORT — nginx must listen on it, not hardcoded 80.
# We also inject $API_URL into config.js so React knows the backend URL.

PORT="${PORT:-80}"
API_URL="${API_URL:-http://localhost:8000}"

echo "Starting SPARK-Bayern frontend on port $PORT"
echo "API URL: $API_URL"

# Write runtime config so React can read the backend URL
cat > /usr/share/nginx/html/config.js << EOF
window.SPARK_CONFIG = { apiUrl: "${API_URL}" };
EOF

# Write nginx config with the correct port substituted in
cat > /etc/nginx/conf.d/default.conf << EOF
server {
    listen ${PORT};
    root /usr/share/nginx/html;
    index index.html;
    location / { try_files \$uri \$uri/ /index.html; }
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
}
EOF

exec nginx -g "daemon off;"
