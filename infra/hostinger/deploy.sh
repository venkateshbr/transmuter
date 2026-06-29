#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/.env}"
HOSTINGER_COMPOSE_TEMPLATE="${HOSTINGER_COMPOSE_TEMPLATE:-${REPO_ROOT}/docker-compose.hostinger.yml}"
HOSTINGER_API_COMPOSE_TEMPLATE="${HOSTINGER_API_COMPOSE_TEMPLATE:-${REPO_ROOT}/docker-compose.hostinger.api.yml}"
DEPLOY_DIR="${HOSTINGER_DEPLOY_DIR:-/docker/transmuter}"
REMOTE_ENV_FILE_OVERRIDE="${REMOTE_ENV_FILE:-}"
REMOTE_COMPOSE_FILE_OVERRIDE="${REMOTE_COMPOSE_FILE:-}"
REMOTE_ENV_FILE="${REMOTE_ENV_FILE_OVERRIDE:-${DEPLOY_DIR}/.env}"
REMOTE_COMPOSE_FILE="${REMOTE_COMPOSE_FILE_OVERRIDE:-${DEPLOY_DIR}/docker-compose.yml}"
RUN_DB_SCHEMA_MIGRATION="${RUN_DB_SCHEMA_MIGRATION:-0}"
DOCKER_BIN="${DOCKER_BIN:-docker}"
HOSTINGER_DEPLOY_MODE="${HOSTINGER_DEPLOY_MODE:-api}"
HOSTINGER_API_BASE_URL="${HOSTINGER_API_BASE_URL:-https://developers.hostinger.com}"

usage() {
  cat <<'USAGE'
Deploy the Transmuter Hostinger VPS stack.

Default mode:
  Uses Hostinger's VPS Docker Manager API from any machine. Dev and production
  remain separate Docker Compose projects on the same VPS, using different
  image tags, host binds, Supabase schemas, and Traefik hostnames.

Required for API mode:
  HOSTINGER_API_TOKEN or HAPI_API_TOKEN  Hostinger bearer token
  HOSTINGER_VPS_ID                      Hostinger VPS virtual machine ID
  infra/hostinger/.env                  Runtime secrets and deployment settings,
                                        unless HOSTINGER_REUSE_REMOTE_ENV=1
  TRANSMUTER_API_IMAGE                  Registry image for the API/worker
  TRANSMUTER_WEB_IMAGE                  Registry image for the web app

Useful API mode overrides:
  HOSTINGER_DEPLOY_MODE=api             Default remote API deployment mode
  HOSTINGER_API_BASE_URL=https://developers.hostinger.com
  HOSTINGER_API_COMPOSE_TEMPLATE=docker-compose.hostinger.api.yml
  HOSTINGER_BUILD_AND_PUSH_IMAGES=1     Build and push images before API deploy
  HOSTINGER_IMAGE_PLATFORM=linux/amd64
  HOSTINGER_DOCKER_REGISTRY=ghcr.io
  HOSTINGER_DOCKER_USERNAME=<user>
  HOSTINGER_DOCKER_PASSWORD=<token>
  HOSTINGER_REUSE_REMOTE_ENV=1          Reuse existing Hostinger project env
  HOSTINGER_API_WAIT_SECONDS=600

Legacy VPS-local mode:
  HOSTINGER_DEPLOY_MODE=local ./infra/hostinger/deploy.sh

  This copies the required repo subsets into /docker/transmuter on the current
  machine, then builds and starts Docker Compose from that local bundle. Use
  this only when the command is running directly on the Hostinger VPS.

Examples:
  ./infra/hostinger/deploy.sh
  HOSTINGER_BUILD_AND_PUSH_IMAGES=1 ./infra/hostinger/deploy.sh
  HOSTINGER_DEPLOY_MODE=local ./infra/hostinger/deploy.sh
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

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck source=/dev/null
  . "${ENV_FILE}"
  set +a
elif [[ "${HOSTINGER_DEPLOY_MODE}" == "api" && "${HOSTINGER_REUSE_REMOTE_ENV:-0}" == "1" ]]; then
  echo "Missing ${ENV_FILE}; HOSTINGER_REUSE_REMOTE_ENV=1 will reuse the existing Hostinger project environment."
else
  echo "Missing ${ENV_FILE}. Copy infra/hostinger/.env.example to infra/hostinger/.env and fill in real values." >&2
  exit 1
fi

HOSTINGER_DEPLOY_MODE="${HOSTINGER_DEPLOY_MODE:-api}"
DEPLOY_DIR="${HOSTINGER_DEPLOY_DIR:-${DEPLOY_DIR}}"
REMOTE_ENV_FILE="${REMOTE_ENV_FILE_OVERRIDE:-${DEPLOY_DIR}/.env}"
REMOTE_COMPOSE_FILE="${REMOTE_COMPOSE_FILE_OVERRIDE:-${DEPLOY_DIR}/docker-compose.yml}"
COMPOSE_PROJECT="${TRANSMUTER_COMPOSE_PROJECT:-${COMPOSE_PROJECT_NAME:-transmuter-hostinger}}"
if [[ -z "${HOSTINGER_STOP_PROJECTS:-}" ]]; then
  if [[ "${COMPOSE_PROJECT}" == "transmuter-hostinger" ]]; then
    HOSTINGER_STOP_PROJECTS="transmuter transmuter-hostinger"
  else
    HOSTINGER_STOP_PROJECTS="${COMPOSE_PROJECT}"
  fi
fi

APP_EXCLUDES=(
  --exclude ".git/"
  --exclude ".pytest_cache/"
  --exclude ".ruff_cache/"
  --exclude ".mypy_cache/"
  --exclude ".venv/"
  --exclude "node_modules/"
  --exclude ".angular/"
  --exclude "dist/"
  --exclude "coverage/"
  --exclude "*.log"
  --exclude ".env"
  --exclude ".env.local"
  --exclude ".env.*"
)

HOSTINGER_EXCLUDES=(
  --exclude ".env"
  --exclude ".env.local"
  --exclude ".env.hostinger"
  --exclude "docker-compose.yml"
)

env_file_quote() {
  local key="$1"
  local value="$2"

  if [[ "${value}" == *$'\n'* || "${value}" == *$'\r'* ]]; then
    echo "${key} contains a newline, which cannot be sent through the Hostinger Docker environment payload." >&2
    exit 1
  fi

  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//\$/\\\$}"
  value="${value//\`/\\\`}"
  printf '%s="%s"\n' "${key}" "${value}"
}

write_api_environment_payload() {
  local key
  local env_keys=(
    APP_NAME
    VERSION
    TRANSMUTER_COMPOSE_PROJECT
    TRANSMUTER_API_IMAGE
    TRANSMUTER_WEB_IMAGE
    TRANSMUTER_IMAGE_PULL_POLICY
    TRANSMUTER_WEB_BIND
    TRANSMUTER_API_URL
    TRANSMUTER_ENVIRONMENT
    APP_PUBLIC_URL
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
    TRANSMUTER_SENTRY_DSN
  )

  for key in "${env_keys[@]}"; do
    if [[ -n "${!key+x}" ]]; then
      env_file_quote "${key}" "${!key}"
    fi
  done
}

hostinger_api_token() {
  if [[ -n "${HOSTINGER_API_TOKEN:-}" ]]; then
    printf "%s" "${HOSTINGER_API_TOKEN}"
    return
  fi
  if [[ -n "${HAPI_API_TOKEN:-}" ]]; then
    printf "%s" "${HAPI_API_TOKEN}"
    return
  fi
}

print_api_error() {
  local response_file="$1"
  python3 - "${response_file}" <<'PY'
import json
import sys
from pathlib import Path

try:
    data = json.loads(Path(sys.argv[1]).read_text())
except Exception:
    print("Hostinger API returned a non-JSON error response.", file=sys.stderr)
    raise SystemExit(0)

for key in ("error", "message", "correlation_id"):
    value = data.get(key)
    if value:
        print(f"{key}: {value}", file=sys.stderr)
PY
}

hostinger_api_request() {
  local method="$1"
  local path="$2"
  local body_file="${3:-}"
  local output_file="$4"
  local token
  local http_status
  local curl_args
  local curl_config_file

  token="$(hostinger_api_token || true)"
  if [[ -z "${token}" ]]; then
    echo "Missing Hostinger API token. Set HOSTINGER_API_TOKEN or HAPI_API_TOKEN." >&2
    exit 1
  fi

  curl_config_file="$(mktemp)"
  chmod 600 "${curl_config_file}"
  {
    printf 'header = "Authorization: Bearer %s"\n' "${token}"
    printf 'header = "Accept: application/json"\n'
  } > "${curl_config_file}"

  curl_args=(
    -sS
    --config "${curl_config_file}"
    -o "${output_file}"
    -w "%{http_code}"
    -X "${method}"
    "${HOSTINGER_API_BASE_URL%/}${path}"
  )

  if [[ -n "${body_file}" ]]; then
    curl_args+=(
      -H "Content-Type: application/json"
      --data-binary "@${body_file}"
    )
  fi

  if ! http_status="$(curl "${curl_args[@]}")"; then
    rm -f "${curl_config_file}"
    echo "Hostinger API ${method} ${path} request failed before an HTTP response was returned." >&2
    exit 1
  fi
  rm -f "${curl_config_file}"
  if [[ ! "${http_status}" =~ ^2[0-9][0-9]$ ]]; then
    echo "Hostinger API ${method} ${path} failed with HTTP ${http_status}." >&2
    print_api_error "${output_file}"
    exit 1
  fi
}

json_field() {
  local response_file="$1"
  local field_name="$2"
  python3 - "${response_file}" "${field_name}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
value = data.get(sys.argv[2], "")
if value is None:
    value = ""
print(value)
PY
}

resolve_hostinger_vps_id() {
  if [[ -n "${HOSTINGER_VPS_ID:-}" ]]; then
    return
  fi

  if [[ -z "${HOSTINGER_SSH_HOST:-}" && -z "${HOSTINGER_PUBLIC_IP:-}" ]]; then
    echo "Missing HOSTINGER_VPS_ID. Set HOSTINGER_VPS_ID, or set HOSTINGER_SSH_HOST/HOSTINGER_PUBLIC_IP so the script can discover it." >&2
    exit 1
  fi

  local response_file
  response_file="$(mktemp)"
  hostinger_api_request GET "/api/vps/v1/virtual-machines" "" "${response_file}"
  HOSTINGER_VPS_ID="$(
    python3 - "${response_file}" "${HOSTINGER_SSH_HOST:-}" "${HOSTINGER_PUBLIC_IP:-}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
target_host = sys.argv[2]
target_ip = sys.argv[3]
machines = data if isinstance(data, list) else data.get("data", [])

for machine in machines:
    hostname = machine.get("hostname", "")
    ipv4 = machine.get("ipv4") or []
    addresses = [entry.get("address") for entry in ipv4 if isinstance(entry, dict)]
    if (target_host and hostname == target_host) or (target_ip and target_ip in addresses):
        print(machine.get("id", ""))
        break
PY
  )"
  rm -f "${response_file}"

  if [[ -z "${HOSTINGER_VPS_ID}" ]]; then
    echo "Could not discover Hostinger VPS ID from HOSTINGER_SSH_HOST/HOSTINGER_PUBLIC_IP. Set HOSTINGER_VPS_ID explicitly." >&2
    exit 1
  fi
}

validate_project_name() {
  if [[ ! "${COMPOSE_PROJECT}" =~ ^[A-Za-z0-9_-]{3,64}$ ]]; then
    echo "TRANSMUTER_COMPOSE_PROJECT must be 3-64 chars using letters, numbers, dashes, or underscores; got '${COMPOSE_PROJECT}'." >&2
    exit 1
  fi
}

validate_remote_image_name() {
  local variable_name="$1"
  local image_name="$2"

  if [[ -z "${image_name}" ]]; then
    echo "${variable_name} is required for Hostinger API deployment." >&2
    exit 1
  fi

  if [[ "${HOSTINGER_ALLOW_LOCAL_IMAGE_TAGS:-0}" == "1" ]]; then
    return
  fi

  if [[ "${image_name}" != */* || "${image_name}" == localhost/* || "${image_name}" == 127.0.0.1/* ]]; then
    echo "${variable_name}='${image_name}' does not look like a registry image." >&2
    echo "Hostinger API deploys cannot build from this checkout; use a pushed image such as ghcr.io/OWNER/IMAGE:TAG, or set HOSTINGER_ALLOW_LOCAL_IMAGE_TAGS=1 if the image already exists on the VPS." >&2
    exit 1
  fi
}

docker_login_if_configured() {
  local registry="${HOSTINGER_DOCKER_REGISTRY:-${DOCKER_REGISTRY:-}}"
  local username="${HOSTINGER_DOCKER_USERNAME:-${DOCKER_USERNAME:-}}"
  local password="${HOSTINGER_DOCKER_PASSWORD:-${DOCKER_PASSWORD:-}}"
  local login_args

  if [[ -z "${username}" && -z "${password}" ]]; then
    return
  fi

  if [[ -z "${username}" || -z "${password}" ]]; then
    echo "Set both HOSTINGER_DOCKER_USERNAME and HOSTINGER_DOCKER_PASSWORD to log in before pushing images." >&2
    exit 1
  fi

  login_args=(login)
  if [[ -n "${registry}" ]]; then
    login_args+=("${registry}")
  fi
  printf "%s" "${password}" | "${DOCKER_BIN}" "${login_args[@]}" --username "${username}" --password-stdin >/dev/null
}

build_and_push_images() {
  if [[ "${HOSTINGER_BUILD_AND_PUSH_IMAGES:-0}" != "1" ]]; then
    echo "Skipping image build/push. Set HOSTINGER_BUILD_AND_PUSH_IMAGES=1 to build and push registry images before deploy."
    return
  fi

  require_command "${DOCKER_BIN}"
  docker_login_if_configured

  local platform="${HOSTINGER_IMAGE_PLATFORM:-linux/amd64}"
  echo "Building and pushing API image ${TRANSMUTER_API_IMAGE} for ${platform}."
  "${DOCKER_BIN}" buildx build \
    --platform "${platform}" \
    -f "${REPO_ROOT}/apps/api/Dockerfile.prod" \
    -t "${TRANSMUTER_API_IMAGE}" \
    --push \
    "${REPO_ROOT}"

  echo "Building and pushing web image ${TRANSMUTER_WEB_IMAGE} for ${platform}."
  "${DOCKER_BIN}" buildx build \
    --platform "${platform}" \
    -f "${REPO_ROOT}/apps/web/Dockerfile" \
    -t "${TRANSMUTER_WEB_IMAGE}" \
    --push \
    "${REPO_ROOT}/apps/web"
}

wait_for_hostinger_action() {
  local action_id="$1"

  if [[ -z "${action_id}" || "${HOSTINGER_API_WAIT_FOR_ACTION:-1}" == "0" ]]; then
    return
  fi

  local wait_seconds="${HOSTINGER_API_WAIT_SECONDS:-600}"
  local deadline=$(( $(date +%s) + wait_seconds ))
  local response_file
  local state
  response_file="$(mktemp)"

  echo "Waiting for Hostinger action ${action_id}."
  while true; do
    hostinger_api_request GET "/api/vps/v1/virtual-machines/${HOSTINGER_VPS_ID}/actions/${action_id}" "" "${response_file}"
    state="$(json_field "${response_file}" state)"
    case "${state}" in
      success)
        echo "Hostinger action ${action_id} completed successfully."
        rm -f "${response_file}"
        return
        ;;
      error)
        echo "Hostinger action ${action_id} failed." >&2
        rm -f "${response_file}"
        exit 1
        ;;
    esac

    if (( $(date +%s) >= deadline )); then
      echo "Timed out waiting for Hostinger action ${action_id}; last state was '${state}'." >&2
      rm -f "${response_file}"
      exit 1
    fi
    sleep 5
  done
}

print_project_summary() {
  local response_file
  response_file="$(mktemp)"
  hostinger_api_request GET "/api/vps/v1/virtual-machines/${HOSTINGER_VPS_ID}/docker" "" "${response_file}"
  python3 - "${response_file}" "${COMPOSE_PROJECT}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
project_name = sys.argv[2]
projects = data if isinstance(data, list) else data.get("data", [])
project = next((item for item in projects if item.get("name") == project_name), None)
if not project:
    print(f"Hostinger Docker project '{project_name}' was not returned by the project list yet.")
    raise SystemExit(0)

state = project.get("state") or project.get("status") or "unknown"
print(f"Hostinger Docker project state: {state}")
for container in project.get("containers", []) or []:
    name = container.get("name", "container")
    image = container.get("image", "")
    cstate = container.get("state") or container.get("status") or "unknown"
    health = container.get("health") or "no-healthcheck"
    print(f"  {name}: {cstate}, {health}, {image}")
PY
  rm -f "${response_file}"
}

fetch_remote_environment_payload() {
  local output_file="$1"
  local response_file
  response_file="$(mktemp)"
  chmod 600 "${response_file}"
  hostinger_api_request GET "/api/vps/v1/virtual-machines/${HOSTINGER_VPS_ID}/docker/${COMPOSE_PROJECT}" "" "${response_file}"
  python3 - "${response_file}" "${output_file}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
environment = data.get("environment")
if not environment:
    print("Existing Hostinger project environment was empty or unavailable.", file=sys.stderr)
    raise SystemExit(1)
Path(sys.argv[2]).write_text(environment.rstrip("\n") + "\n")
PY
  rm -f "${response_file}"
}

merge_environment_payload() {
  local base_file="$1"
  local override_file="$2"
  local output_file="$3"

  python3 - "${base_file}" "${override_file}" "${output_file}" <<'PY'
import re
import sys
from pathlib import Path

base_path, override_path, output_path = map(Path, sys.argv[1:4])
assignment = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=")

def assignment_key(line):
    match = assignment.match(line)
    if not match:
        return None
    return match.group(1)

overrides = [line.strip() for line in override_path.read_text().splitlines() if assignment_key(line)]
override_keys = {assignment_key(line) for line in overrides}

merged: list[str] = []
seen: set[str] = set()
for raw_line in base_path.read_text().splitlines():
    line = raw_line.strip()
    key = assignment_key(line)
    if not key or key in override_keys or key in seen:
        continue
    merged.append(line)
    seen.add(key)

merged.extend(overrides)
output_path.write_text("\n".join(merged) + "\n")
PY
}

deploy_via_hostinger_api() {
  require_command curl
  require_command python3

  if [[ ! -f "${HOSTINGER_API_COMPOSE_TEMPLATE}" ]]; then
    echo "Missing API compose template: ${HOSTINGER_API_COMPOSE_TEMPLATE}" >&2
    exit 1
  fi

  validate_project_name
  validate_remote_image_name TRANSMUTER_API_IMAGE "${TRANSMUTER_API_IMAGE:-}"
  validate_remote_image_name TRANSMUTER_WEB_IMAGE "${TRANSMUTER_WEB_IMAGE:-}"
  resolve_hostinger_vps_id
  build_and_push_images

  local env_payload_file
  local env_override_file
  local request_body_file
  local response_file
  local compose_size
  local env_size
  local action_id
  env_payload_file="$(mktemp)"
  env_override_file="$(mktemp)"
  request_body_file="$(mktemp)"
  response_file="$(mktemp)"
  chmod 600 "${env_payload_file}" "${env_override_file}" "${request_body_file}" "${response_file}"
  trap "rm -f '${env_payload_file}' '${env_override_file}' '${request_body_file}' '${response_file}'" EXIT

  write_api_environment_payload > "${env_override_file}"
  if [[ "${HOSTINGER_REUSE_REMOTE_ENV:-0}" == "1" ]]; then
    echo "Reusing existing Hostinger environment for ${COMPOSE_PROJECT}."
    fetch_remote_environment_payload "${env_payload_file}"
    merge_environment_payload "${env_payload_file}" "${env_override_file}" "${env_payload_file}"
  else
    cp "${env_override_file}" "${env_payload_file}"
  fi

  compose_size="$(wc -c < "${HOSTINGER_API_COMPOSE_TEMPLATE}" | tr -d ' ')"
  env_size="$(wc -c < "${env_payload_file}" | tr -d ' ')"
  if (( compose_size > 8192 )); then
    echo "Hostinger Docker API compose payload is ${compose_size} bytes; maximum is 8192." >&2
    exit 1
  fi
  if (( env_size > 8192 )); then
    echo "Hostinger Docker API environment payload is ${env_size} bytes; maximum is 8192." >&2
    exit 1
  fi

  python3 - "${COMPOSE_PROJECT}" "${HOSTINGER_API_COMPOSE_TEMPLATE}" "${env_payload_file}" > "${request_body_file}" <<'PY'
import json
import sys
from pathlib import Path

project_name, compose_file, environment_file = sys.argv[1:4]
payload = {
    "project_name": project_name,
    "content": Path(compose_file).read_text(),
    "environment": Path(environment_file).read_text(),
}
json.dump(payload, sys.stdout)
PY

  echo "Deploying ${COMPOSE_PROJECT} to Hostinger VPS ${HOSTINGER_VPS_ID} through Docker Manager API."
  hostinger_api_request POST "/api/vps/v1/virtual-machines/${HOSTINGER_VPS_ID}/docker" "${request_body_file}" "${response_file}"
  action_id="$(json_field "${response_file}" id)"
  wait_for_hostinger_action "${action_id}"
  print_project_summary
  echo "Hostinger API deployment command completed."
  echo "Validate publicly:"
  echo "  curl -fsS ${APP_PUBLIC_URL:-https://transmuter.ishirock.tech}/health"
  echo "  curl -fsS ${APP_PUBLIC_URL:-https://transmuter.ishirock.tech}/api/health"
}

deploy_locally_on_vps() {
  if [[ ! -f "${HOSTINGER_COMPOSE_TEMPLATE}" ]]; then
    echo "Missing compose template: ${HOSTINGER_COMPOSE_TEMPLATE}" >&2
    exit 1
  fi

  require_command rsync
  require_command "${DOCKER_BIN}"

  local deploy_dir_parent
  deploy_dir_parent="$(dirname "${DEPLOY_DIR}")"
  mkdir -p "${deploy_dir_parent}"
  rm -rf "${DEPLOY_DIR}"
  mkdir -p "${DEPLOY_DIR}/apps/api" "${DEPLOY_DIR}/apps/web" "${DEPLOY_DIR}/domain_packs" "${DEPLOY_DIR}/infra/hostinger"

  echo "Staging Transmuter bundle locally into ${DEPLOY_DIR}"
  echo "Compose template: ${HOSTINGER_COMPOSE_TEMPLATE}"

  rsync -az --delete "${APP_EXCLUDES[@]}" \
    "${REPO_ROOT}/apps/api/" "${DEPLOY_DIR}/apps/api/"

  rsync -az --delete "${APP_EXCLUDES[@]}" \
    "${REPO_ROOT}/apps/web/" "${DEPLOY_DIR}/apps/web/"

  rsync -az --delete "${APP_EXCLUDES[@]}" \
    "${REPO_ROOT}/domain_packs/" "${DEPLOY_DIR}/domain_packs/"

  rsync -az --delete "${HOSTINGER_EXCLUDES[@]}" \
    "${REPO_ROOT}/infra/hostinger/" "${DEPLOY_DIR}/infra/hostinger/"

  cp "${HOSTINGER_COMPOSE_TEMPLATE}" "${REMOTE_COMPOSE_FILE}"
  cp "${ENV_FILE}" "${REMOTE_ENV_FILE}"
  chmod 600 "${REMOTE_ENV_FILE}"

  for project in ${HOSTINGER_STOP_PROJECTS}; do
    "${DOCKER_BIN}" compose -p "${project}" -f "${REMOTE_COMPOSE_FILE}" --env-file "${REMOTE_ENV_FILE}" down --remove-orphans >/dev/null 2>&1 || true
  done

  if [[ "${RUN_DB_SCHEMA_MIGRATION}" == "1" ]]; then
    echo "Running schema migration before container restart."
    (
      cd "${DEPLOY_DIR}"
      set -a
      # shellcheck source=/dev/null
      . "${REMOTE_ENV_FILE}"
      set +a
      bash ./infra/hostinger/migrate_supabase_schema_to_transmuter.sh
    )
  else
    echo "Skipping schema migration. Set RUN_DB_SCHEMA_MIGRATION=1 to enable it."
  fi

  (
    cd "${DEPLOY_DIR}"
    set -a
    # shellcheck source=/dev/null
    . "${REMOTE_ENV_FILE}"
    set +a
    "${DOCKER_BIN}" compose -p "${COMPOSE_PROJECT}" -f "${REMOTE_COMPOSE_FILE}" --env-file "${REMOTE_ENV_FILE}" build
    "${DOCKER_BIN}" compose -p "${COMPOSE_PROJECT}" -f "${REMOTE_COMPOSE_FILE}" --env-file "${REMOTE_ENV_FILE}" up -d --remove-orphans
    "${DOCKER_BIN}" compose -p "${COMPOSE_PROJECT}" -f "${REMOTE_COMPOSE_FILE}" --env-file "${REMOTE_ENV_FILE}" ps
  )

  echo "Deployment command completed locally on the VPS."
  echo "Validate locally on the VPS:"
  local local_web_bind="${TRANSMUTER_WEB_BIND:-127.0.0.1:4301}"
  local local_web_base_url="http://${local_web_bind}"
  echo "  curl -fsS ${local_web_base_url}/health"
  echo "  curl -fsS ${local_web_base_url}/api/health"
}

case "${HOSTINGER_DEPLOY_MODE}" in
  api)
    deploy_via_hostinger_api
    ;;
  local)
    deploy_locally_on_vps
    ;;
  *)
    echo "HOSTINGER_DEPLOY_MODE must be 'api' or 'local'; got '${HOSTINGER_DEPLOY_MODE}'." >&2
    exit 1
    ;;
esac
