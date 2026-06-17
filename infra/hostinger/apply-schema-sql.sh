#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENVIRONMENT="${1:-}"
if [[ -n "${ENVIRONMENT}" ]]; then
  shift
fi

usage() {
  cat <<'USAGE'
Apply one or more SQL files to a Hostinger Supabase application schema.

Usage:
  ./infra/hostinger/apply-schema-sql.sh dev path/to/change.sql [more.sql...]
  CONFIRM_PROD_SCHEMA=1 ./infra/hostinger/apply-schema-sql.sh prod path/to/change.sql

Defaults:
  dev  -> infra/hostinger/.env.dev, schema transmuter_dev
  prod -> infra/hostinger/.env, schema transmuter

The script sets PostgreSQL search_path to:
  <target_schema>,public,extensions

SQL files should use unqualified app table/function names unless they explicitly
need another schema. Production requires CONFIRM_PROD_SCHEMA=1.
USAGE
}

if [[ "${ENVIRONMENT}" == "-h" || "${ENVIRONMENT}" == "--help" || -z "${ENVIRONMENT}" ]]; then
  usage
  exit 0
fi

if [[ "${ENVIRONMENT}" != "dev" && "${ENVIRONMENT}" != "prod" ]]; then
  echo "Environment must be 'dev' or 'prod'; got '${ENVIRONMENT}'." >&2
  exit 1
fi

if [[ "$#" -lt 1 ]]; then
  echo "At least one SQL file is required." >&2
  usage >&2
  exit 1
fi

validate_identifier() {
  local name="$1"
  local value="$2"
  if [[ ! "${value}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "${name} must be a simple PostgreSQL identifier; got '${value}'." >&2
    exit 1
  fi
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

if [[ "${ENVIRONMENT}" == "prod" && "${CONFIRM_PROD_SCHEMA:-0}" != "1" ]]; then
  echo "Refusing to apply production schema SQL without CONFIRM_PROD_SCHEMA=1." >&2
  exit 1
fi

ENV_FILE_DEFAULT="${SCRIPT_DIR}/.env"
TARGET_SCHEMA_DEFAULT="transmuter"
if [[ "${ENVIRONMENT}" == "dev" ]]; then
  ENV_FILE_DEFAULT="${SCRIPT_DIR}/.env.dev"
  TARGET_SCHEMA_DEFAULT="transmuter_dev"
fi

ENV_FILE="${ENV_FILE:-${ENV_FILE_DEFAULT}}"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing env file: ${ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck source=/dev/null
. "${ENV_FILE}"
set +a

TARGET_SCHEMA="${SCHEMA_TARGET:-${SUPABASE_SCHEMA:-${DB_SCHEMA:-${TARGET_SCHEMA_DEFAULT}}}}"
validate_identifier TARGET_SCHEMA "${TARGET_SCHEMA}"

SCHEMA_DATABASE_URL="${SCHEMA_DATABASE_URL:-}"
if [[ -z "${SCHEMA_DATABASE_URL}" ]]; then
  if [[ "${ENVIRONMENT}" == "dev" ]]; then
    SCHEMA_DATABASE_URL="${DEV_SCHEMA_DATABASE_URL:-${DEV_CLONE_DATABASE_URL:-${TARGET_DATABASE_URL:-${DATABASE_LOCAL_URL:-}}}}"
  else
    SCHEMA_DATABASE_URL="${PROD_SCHEMA_DATABASE_URL:-${TARGET_DATABASE_URL:-${DATABASE_LOCAL_URL:-}}}"
  fi
fi

if [[ -z "${SCHEMA_DATABASE_URL}" ]]; then
  echo "No schema database URL is configured for ${ENVIRONMENT}." >&2
  echo "Set SCHEMA_DATABASE_URL, or configure TARGET_DATABASE_URL/DATABASE_LOCAL_URL in ${ENV_FILE}." >&2
  exit 1
fi

POSTGRES_DOCKER_IMAGE="${POSTGRES_DOCKER_IMAGE:-postgres:15-alpine}"
POSTGRES_DOCKER_NETWORK="${POSTGRES_DOCKER_NETWORK:-host}"
PGOPTIONS_VALUE="-c search_path=${TARGET_SCHEMA},public,extensions"

USE_DOCKER_TOOLS=0
if ! command -v psql >/dev/null 2>&1; then
  require_command docker
  USE_DOCKER_TOOLS=1
fi

apply_file() {
  local sql_file="$1"
  local sql_dir
  local sql_name

  if [[ ! -f "${sql_file}" ]]; then
    echo "SQL file not found: ${sql_file}" >&2
    exit 1
  fi

  sql_dir="$(cd "$(dirname "${sql_file}")" && pwd)"
  sql_name="$(basename "${sql_file}")"

  echo "Applying ${sql_file} to ${ENVIRONMENT} schema '${TARGET_SCHEMA}'."
  if [[ "${USE_DOCKER_TOOLS}" == "1" ]]; then
    docker run --rm --network "${POSTGRES_DOCKER_NETWORK}" \
      -e SCHEMA_DATABASE_URL="${SCHEMA_DATABASE_URL}" \
      -e PGOPTIONS="${PGOPTIONS_VALUE}" \
      -v "${sql_dir}:/work:ro" \
      "${POSTGRES_DOCKER_IMAGE}" \
      sh -c 'psql "$SCHEMA_DATABASE_URL" -v ON_ERROR_STOP=1 --single-transaction -f "/work/$1"' sh "${sql_name}"
  else
    PGOPTIONS="${PGOPTIONS_VALUE}" \
      psql "${SCHEMA_DATABASE_URL}" -v ON_ERROR_STOP=1 --single-transaction -f "${sql_file}"
  fi
}

for sql_file in "$@"; do
  apply_file "${sql_file}"
done

echo "Schema SQL applied to ${ENVIRONMENT} schema '${TARGET_SCHEMA}'."
