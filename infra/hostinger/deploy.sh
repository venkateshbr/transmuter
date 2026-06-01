#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/.env}"

usage() {
  cat <<'USAGE'
Deploy Transmuter to the Hostinger VPS.

Required local file:
  infra/hostinger/.env  Runtime secrets and deployment settings. Use infra/hostinger/.env.example as the template.

Useful environment overrides:
  ENV_FILE=/path/to/hostinger.env
  HOSTINGER_SSH_HOST=srv1695814.hstgr.cloud
  HOSTINGER_SSH_USER=root
  HOSTINGER_SSH_PORT=22
  HOSTINGER_DEPLOY_DIR=/opt/transmuter
  RUN_DB_SCHEMA_MIGRATION=1

Example:
  ./infra/hostinger/deploy.sh
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

shell_quote() {
  printf "%q" "$1"
}

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy infra/hostinger/.env.example to infra/hostinger/.env and fill in real values." >&2
  exit 1
fi

set -a
# shellcheck source=/dev/null
. "${ENV_FILE}"
set +a

HOSTINGER_SSH_HOST="${HOSTINGER_SSH_HOST:-srv1695814.hstgr.cloud}"
HOSTINGER_PUBLIC_IP="${HOSTINGER_PUBLIC_IP:-76.13.208.106}"
HOSTINGER_SSH_USER="${HOSTINGER_SSH_USER:-root}"
HOSTINGER_SSH_PORT="${HOSTINGER_SSH_PORT:-22}"
HOSTINGER_DEPLOY_DIR="${HOSTINGER_DEPLOY_DIR:-/opt/transmuter}"
REMOTE_ENV_FILE="${REMOTE_ENV_FILE:-${HOSTINGER_DEPLOY_DIR}/infra/hostinger/.env}"
COMPOSE_FILE="${COMPOSE_FILE:-infra/hostinger/docker-compose.yml}"
DOCKER_BIN="${DOCKER_BIN:-docker}"
RUN_DB_SCHEMA_MIGRATION="${RUN_DB_SCHEMA_MIGRATION:-0}"

require_command ssh
require_command scp
require_command rsync

SSH_TARGET="${HOSTINGER_SSH_USER}@${HOSTINGER_SSH_HOST}"
SSH_OPTS=(-p "${HOSTINGER_SSH_PORT}")
SCP_OPTS=(-P "${HOSTINGER_SSH_PORT}")
RSYNC_RSH="ssh -p ${HOSTINGER_SSH_PORT}"
REMOTE_DIR_QUOTED="$(shell_quote "${HOSTINGER_DEPLOY_DIR}")"
REMOTE_ENV_QUOTED="$(shell_quote "${REMOTE_ENV_FILE}")"
COMPOSE_QUOTED="$(shell_quote "${COMPOSE_FILE}")"
DOCKER_QUOTED="$(shell_quote "${DOCKER_BIN}")"

echo "Deploying Transmuter to ${SSH_TARGET} (${HOSTINGER_PUBLIC_IP})"
echo "Remote directory: ${HOSTINGER_DEPLOY_DIR}"

ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "mkdir -p ${REMOTE_DIR_QUOTED}"

rsync -az \
  --exclude ".git/" \
  --exclude ".pytest_cache/" \
  --exclude ".ruff_cache/" \
  --exclude ".mypy_cache/" \
  --exclude ".venv/" \
  --exclude "node_modules/" \
  --exclude "apps/web/dist/" \
  --exclude "backend.log" \
  --exclude "frontend.log" \
  --exclude ".env" \
  --exclude ".env.local" \
  --exclude ".env.hostinger" \
  --exclude "infra/hostinger/.env" \
  --exclude "scratch/" \
  -e "${RSYNC_RSH}" \
  "${REPO_ROOT}/" "${SSH_TARGET}:${HOSTINGER_DEPLOY_DIR}/"

scp "${SCP_OPTS[@]}" "${ENV_FILE}" "${SSH_TARGET}:${REMOTE_ENV_FILE}"

if [[ "${RUN_DB_SCHEMA_MIGRATION}" == "1" ]]; then
  echo "Running schema migration on the VPS before container restart."
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "
    set -euo pipefail
    cd ${REMOTE_DIR_QUOTED}
    set -a
    . ${REMOTE_ENV_QUOTED}
    set +a
    ./infra/hostinger/migrate_supabase_schema_to_transmuter.sh
  "
else
  echo "Skipping schema migration. Set RUN_DB_SCHEMA_MIGRATION=1 to enable it."
fi

ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "
  set -euo pipefail
  cd ${REMOTE_DIR_QUOTED}
  set -a
  . ${REMOTE_ENV_QUOTED}
  set +a
  ${DOCKER_QUOTED} compose -f ${COMPOSE_QUOTED} --env-file ${REMOTE_ENV_QUOTED} build
  ${DOCKER_QUOTED} compose -f ${COMPOSE_QUOTED} --env-file ${REMOTE_ENV_QUOTED} up -d --remove-orphans
  ${DOCKER_QUOTED} compose -f ${COMPOSE_QUOTED} --env-file ${REMOTE_ENV_QUOTED} ps
"

echo "Deployment command completed."
echo "Validate from the VPS or reverse proxy:"
echo "  curl -fsS https://${TRAEFIK_HOSTNAME:-transmuter.ishirock.tech}/health"
echo "  curl -fsS https://${TRAEFIK_HOSTNAME:-transmuter.ishirock.tech}/api/health"
