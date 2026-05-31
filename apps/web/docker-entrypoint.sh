#!/usr/bin/env sh
set -eu

API_URL="${TRANSMUTER_API_URL:-/api}"
SENTRY_DSN="${TRANSMUTER_SENTRY_DSN:-}"
APP_ENVIRONMENT="${TRANSMUTER_ENVIRONMENT:-production}"

cat > /usr/share/nginx/html/assets/runtime-config.js <<EOF
window.__TRANSMUTER_API_URL__ = "${API_URL}";
window.__TRANSMUTER_SENTRY_DSN__ = "${SENTRY_DSN}";
window.__TRANSMUTER_ENVIRONMENT__ = "${APP_ENVIRONMENT}";
EOF

exec nginx -g "daemon off;"
