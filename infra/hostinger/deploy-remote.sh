#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/.env}"
. "${SCRIPT_DIR}/env-control.sh"
load_hostinger_control_env "${REPO_ROOT}/.env"
load_hostinger_control_env "${ENV_FILE}"

HOSTINGER_API_BASE_URL="${HOSTINGER_API_BASE_URL:-https://developers.hostinger.com/api}"
HOSTINGER_VPS_ID="${HOSTINGER_VPS_ID:-1695814}"
HOSTINGER_COMPOSE_PATH="${HOSTINGER_COMPOSE_PATH:-docker-compose.hostinger.yml}"
HOSTINGER_REPOSITORY_URL="${HOSTINGER_REPOSITORY_URL:-}"
HOSTINGER_PROJECT_NAME="${HOSTINGER_PROJECT_NAME:-${TRANSMUTER_COMPOSE_PROJECT:-transmuter-hostinger}}"
HOSTINGER_PRESERVE_REMOTE_ENV="${HOSTINGER_PRESERVE_REMOTE_ENV:-}"
SKIP_GIT_REMOTE_CHECK="${SKIP_GIT_REMOTE_CHECK:-0}"
ALLOW_DIRTY_DEPLOY="${ALLOW_DIRTY_DEPLOY:-0}"

usage() {
  cat <<'USAGE'
Deploy Transmuter to Hostinger VPS through the Hostinger Docker project API.

Usage:
  ./infra/hostinger/deploy-dev.sh
  ./infra/hostinger/deploy-prod.sh

Required:
  HOSTINGER_API_KEY or HOSTINGER_API_TOKEN in the shell, repo .env, or the
  selected infra/hostinger env file.

Defaults:
  VPS ID:      1695814
  dev project: transmuter-dev-hostinger
  prod project: transmuter-hostinger

Remote deploy model:
  The Hostinger API fetches the compose file from GitHub and builds/recreates
  the Docker project on the VPS. The current checkout must be committed and
  pushed before deployment; uncommitted local files cannot be transported by
  this API.

Useful overrides:
  HOSTINGER_DEPLOY_REF=<git ref or SHA>
  HOSTINGER_COMPOSE_URL=https://github.com/owner/repo/blob/ref/docker-compose.hostinger.yml
  HOSTINGER_PROJECT_NAME=transmuter-dev-hostinger
  HOSTINGER_VPS_ID=1695814
  ENV_FILE=infra/hostinger/.env.dev
  HOSTINGER_PRESERVE_REMOTE_ENV=1
  SKIP_GIT_REMOTE_CHECK=1

When ENV_FILE is missing, the script fetches and reuses the existing project's
saved Hostinger environment. This avoids replacing a running project with an
empty environment.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command curl
require_command jq
require_command git

API_TOKEN="${HOSTINGER_API_TOKEN:-${HOSTINGER_API_KEY:-}}"
if [[ -z "${API_TOKEN}" ]]; then
  echo "Set HOSTINGER_API_KEY or HOSTINGER_API_TOKEN in .env, ${ENV_FILE}, or the shell before deploying." >&2
  exit 1
fi

if [[ ! "${HOSTINGER_PROJECT_NAME}" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "HOSTINGER_PROJECT_NAME must contain only letters, numbers, dashes, and underscores." >&2
  exit 1
fi

cd "${REPO_ROOT}"

current_sha="$(git rev-parse HEAD)"
current_short_sha="$(git rev-parse --short HEAD)"
current_branch="$(git branch --show-current || true)"

if [[ "${ALLOW_DIRTY_DEPLOY}" != "1" && -n "$(git status --porcelain)" ]]; then
  cat >&2 <<'EOF'
Refusing remote deploy with uncommitted changes.

Hostinger's Docker project API fetches source from GitHub, so local-only edits
would not be deployed. Commit and push first, or set ALLOW_DIRTY_DEPLOY=1 only
when HOSTINGER_COMPOSE_URL points to the exact content you intend to deploy.
EOF
  exit 1
fi

if [[ -z "${HOSTINGER_REPOSITORY_URL}" ]]; then
  origin_url="$(git config --get remote.origin.url || true)"
  case "${origin_url}" in
    git@github.com:*)
      HOSTINGER_REPOSITORY_URL="https://github.com/${origin_url#git@github.com:}"
      HOSTINGER_REPOSITORY_URL="${HOSTINGER_REPOSITORY_URL%.git}"
      ;;
    https://github.com/*)
      HOSTINGER_REPOSITORY_URL="${origin_url%.git}"
      ;;
    *)
      HOSTINGER_REPOSITORY_URL="https://github.com/venkateshbr/transmuter"
      ;;
  esac
fi

if [[ -n "${current_branch}" && "${SKIP_GIT_REMOTE_CHECK}" != "1" ]]; then
  remote_sha="$(git ls-remote origin "refs/heads/${current_branch}" | awk '{print $1}' || true)"
  if [[ -z "${remote_sha}" ]]; then
    echo "Current branch '${current_branch}' is not pushed to origin." >&2
    echo "Push the branch first, or set SKIP_GIT_REMOTE_CHECK=1 if you supplied a deployable HOSTINGER_COMPOSE_URL." >&2
    exit 1
  fi
  if [[ "${remote_sha}" != "${current_sha}" ]]; then
    echo "Origin branch '${current_branch}' is not at ${current_short_sha}." >&2
    echo "Push the current commit before deploying through the Hostinger API." >&2
    exit 1
  fi
fi

HOSTINGER_DEPLOY_REF="${HOSTINGER_DEPLOY_REF:-${current_sha}}"
if [[ -n "${HOSTINGER_COMPOSE_URL:-}" ]]; then
  compose_content="${HOSTINGER_COMPOSE_URL}"
else
  compose_content="${HOSTINGER_REPOSITORY_URL}/blob/${HOSTINGER_DEPLOY_REF}/${HOSTINGER_COMPOSE_PATH}"
fi

load_env_file() {
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck source=/dev/null
    . "${ENV_FILE}"
    set +a
  fi
}

runtime_env_keys=(
  APP_NAME
  VERSION
  DEBUG
  ENVIRONMENT
  APP_PUBLIC_URL
  TRANSMUTER_API_URL
  TRANSMUTER_ENVIRONMENT
  TRANSMUTER_API_IMAGE
  TRANSMUTER_WEB_IMAGE
  TRANSMUTER_WEB_BIND
  TRANSMUTER_COMPOSE_PROJECT
  TRAEFIK_HOSTNAME
  TRAEFIK_ROUTER_NAME
  TRAEFIK_SERVICE_NAME
  TRAEFIK_HTTP_ENTRYPOINT
  TRAEFIK_HTTPS_ENTRYPOINT
  TRAEFIK_CERT_RESOLVER
  SUPABASE_TARGET
  SUPABASE_URL
  SUPABASE_ANON_KEY
  SUPABASE_SERVICE_KEY
  SUPABASE_CLOUD_URL
  SUPABASE_CLOUD_ANON_KEY
  SUPABASE_CLOUD_SERVICE_KEY
  SUPABASE_LOCAL_URL
  SUPABASE_LOCAL_ANON_KEY
  SUPABASE_LOCAL_SERVICE_KEY
  SUPABASE_SCHEMA
  DATABASE_URL
  DATABASE_CLOUD_URL
  DATABASE_LOCAL_URL
  DB_SCHEMA
  JWT_SECRET
  JWT_ALGORITHM
  JWT_EXPIRY_MINUTES
  AI_ENABLED
  OPENROUTER_API_KEY
  OPENROUTER_BASE_URL
  DEFAULT_MODEL
  LANGFUSE_SECRET_KEY
  LANGFUSE_PUBLIC_KEY
  LANGFUSE_HOST
  LOGFIRE_TOKEN
  SENTRY_DSN
  SENTRY_TRACES_SAMPLE_RATE
  ALERT_WEBHOOK_URL
  RESEND_API_KEY
  RESEND_FROM_EMAIL
  MICROSOFT_GRAPH_CLIENT_ID
  MICROSOFT_GRAPH_CLIENT_SECRET
  MICROSOFT_GRAPH_TENANT_ID
  MICROSOFT_GRAPH_REDIRECT_URI
  MICROSOFT_GRAPH_SCOPES
  PAYMENT_PROVIDER
  STRIPE_SECRET_KEY
  STRIPE_PUBLISHABLE_KEY
  STRIPE_WEBHOOK_SECRET
  STRIPE_PRICE_TEAM_MONTHLY
  STRIPE_PRICE_TEAM_ANNUAL
  STRIPE_PRICE_BUSINESS_MONTHLY
  STRIPE_PRICE_BUSINESS_ANNUAL
  ENCRYPTION_KEY
  PLATFORM_ADMIN_EMAILS
  PLATFORM_ADMIN_BOOTSTRAP_ENABLED
  PLATFORM_ADMIN_BOOTSTRAP_EMAIL
  PLATFORM_ADMIN_BOOTSTRAP_PASSWORD
  PLATFORM_ADMIN_PREVIOUS_EMAIL
)

build_environment_from_shell() {
  local key value
  for key in "${runtime_env_keys[@]}"; do
    if [[ -n "${!key+x}" ]]; then
      value="${!key}"
      if [[ -n "${value}" ]]; then
        printf '%s=%s\n' "${key}" "${value}"
      fi
    fi
  done
}

fetch_project_environment() {
  curl -fsS \
    -H "Authorization: Bearer ${API_TOKEN}" \
    "${HOSTINGER_API_BASE_URL}/vps/v1/virtual-machines/${HOSTINGER_VPS_ID}/docker/${HOSTINGER_PROJECT_NAME}" \
    | jq -r '.environment // ""'
}

remote_environment=""
if [[ -f "${ENV_FILE}" ]]; then
  load_env_file
  if [[ "${HOSTINGER_PRESERVE_REMOTE_ENV}" == "1" ]]; then
    remote_environment="$(fetch_project_environment)"
  else
    remote_environment="$(build_environment_from_shell)"
  fi
else
  if [[ -z "${HOSTINGER_PRESERVE_REMOTE_ENV}" ]]; then
    HOSTINGER_PRESERVE_REMOTE_ENV=1
  fi
  if [[ "${HOSTINGER_PRESERVE_REMOTE_ENV}" != "1" ]]; then
    echo "Missing ${ENV_FILE}; cannot build a project environment." >&2
    echo "Create the env file or set HOSTINGER_PRESERVE_REMOTE_ENV=1." >&2
    exit 1
  fi
  echo "Missing ${ENV_FILE}; preserving saved Hostinger project environment for ${HOSTINGER_PROJECT_NAME}."
  remote_environment="$(fetch_project_environment)"
fi

if [[ -z "${remote_environment}" ]]; then
  echo "Hostinger project environment is empty. Refusing to replace ${HOSTINGER_PROJECT_NAME}." >&2
  exit 1
fi

request_body="$(
  jq -n \
    --arg project_name "${HOSTINGER_PROJECT_NAME}" \
    --arg content "${compose_content}" \
    --arg environment "${remote_environment}" \
    '{project_name: $project_name, content: $content, environment: $environment}'
)"

echo "Deploying ${HOSTINGER_PROJECT_NAME} to Hostinger VPS ${HOSTINGER_VPS_ID}."
echo "Compose content: ${compose_content}"
echo "Git commit: ${current_short_sha}"

response="$(
  curl -sS -w '\n%{http_code}' -X POST \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${request_body}" \
    "${HOSTINGER_API_BASE_URL}/vps/v1/virtual-machines/${HOSTINGER_VPS_ID}/docker"
)"
body="$(printf '%s\n' "${response}" | sed '$d')"
status_code="$(printf '%s\n' "${response}" | tail -n 1)"

if [[ "${status_code}" -lt 200 || "${status_code}" -ge 300 ]]; then
  echo "Hostinger API deploy failed with status ${status_code}." >&2
  if [[ -n "${body}" ]]; then
    printf '%s\n' "${body}" >&2
  fi
  exit 1
fi

echo "Hostinger API accepted deployment for ${HOSTINGER_PROJECT_NAME}."
if [[ -n "${body}" ]]; then
  printf '%s\n' "${body}" | jq '.' 2>/dev/null || printf '%s\n' "${body}"
fi
