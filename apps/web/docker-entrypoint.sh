#!/usr/bin/env sh
set -eu

API_URL="${TRANSMUTER_API_URL:-/api}"

cat > /usr/share/nginx/html/assets/runtime-config.js <<EOF
window.__TRANSMUTER_API_URL__ = "${API_URL}";
EOF

exec nginx -g "daemon off;"
