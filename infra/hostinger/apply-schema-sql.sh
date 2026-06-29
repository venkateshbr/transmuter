#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
. "${SCRIPT_DIR}/env-control.sh"

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

fetch_hostinger_project_environment() {
  local project_name="$1"
  local api_token="${HOSTINGER_API_TOKEN:-${HOSTINGER_API_KEY:-}}"
  local api_base="${HOSTINGER_API_BASE_URL:-https://developers.hostinger.com/api}"
  local vps_id="${HOSTINGER_VPS_ID:-1695814}"

  if [[ -z "${api_token}" ]]; then
    return 1
  fi
  require_command curl
  require_command jq
  curl -fsS \
    -H "Authorization: Bearer ${api_token}" \
    "${api_base}/vps/v1/virtual-machines/${vps_id}/docker/${project_name}" \
    | jq -r '.environment // ""'
}

write_temp_env_from_project() {
  local project_name="$1"
  local tmp_file="$2"
  local environment

  echo "Missing env file; fetching saved Hostinger environment from project '${project_name}'."
  environment="$(fetch_hostinger_project_environment "${project_name}")"
  if [[ -z "${environment}" ]]; then
    echo "Hostinger project '${project_name}' did not return an environment." >&2
    exit 1
  fi
  umask 077
  printf '%s\n' "${environment}" > "${tmp_file}"
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
load_hostinger_control_env "${REPO_ROOT}/.env"
load_hostinger_control_env "${ENV_FILE}"

if [[ ! -f "${ENV_FILE}" ]]; then
  PROJECT_NAME_DEFAULT="transmuter-hostinger"
  if [[ "${ENVIRONMENT}" == "dev" ]]; then
    PROJECT_NAME_DEFAULT="transmuter-dev-hostinger"
  fi
  HOSTINGER_PROJECT_NAME="${HOSTINGER_PROJECT_NAME:-${PROJECT_NAME_DEFAULT}}"
  TEMP_ENV_FILE="$(mktemp)"
  trap 'rm -f "${TEMP_ENV_FILE:-}"' EXIT
  write_temp_env_from_project "${HOSTINGER_PROJECT_NAME}" "${TEMP_ENV_FILE}"
  ENV_FILE="${TEMP_ENV_FILE}"
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

HOSTINGER_SCHEMA_APPLY_MODE="${HOSTINGER_SCHEMA_APPLY_MODE:-direct}"
INTERNAL_SCHEMA_DATABASE_URL="${SCHEMA_DATABASE_URL}"

if [[ "${HOSTINGER_SCHEMA_APPLY_MODE}" != "hostinger-job" && -n "${HOSTINGER_SCHEMA_DATABASE_HOST:-}" ]]; then
  SCHEMA_DATABASE_URL="${SCHEMA_DATABASE_URL//@db:/@${HOSTINGER_SCHEMA_DATABASE_HOST}:}"
  SCHEMA_DATABASE_URL="${SCHEMA_DATABASE_URL//@host.docker.internal:/@${HOSTINGER_SCHEMA_DATABASE_HOST}:}"
  SCHEMA_DATABASE_URL="${SCHEMA_DATABASE_URL//@127.0.0.1:/@${HOSTINGER_SCHEMA_DATABASE_HOST}:}"
  SCHEMA_DATABASE_URL="${SCHEMA_DATABASE_URL//@localhost:/@${HOSTINGER_SCHEMA_DATABASE_HOST}:}"
fi

POSTGRES_DOCKER_IMAGE="${POSTGRES_DOCKER_IMAGE:-postgres:15-alpine}"
POSTGRES_DOCKER_NETWORK="${POSTGRES_DOCKER_NETWORK:-bridge}"
PGOPTIONS_VALUE="-c search_path=${TARGET_SCHEMA},public,extensions"

USE_DOCKER_TOOLS=0
if [[ "${HOSTINGER_SCHEMA_APPLY_MODE}" != "hostinger-job" ]]; then
  if ! command -v psql >/dev/null 2>&1; then
    require_command docker
    USE_DOCKER_TOOLS=1
  fi
fi

hostinger_api_token() {
  local api_token="${HOSTINGER_API_TOKEN:-${HOSTINGER_API_KEY:-}}"
  if [[ -z "${api_token}" ]]; then
    echo "HOSTINGER_API_KEY or HOSTINGER_API_TOKEN is required for hostinger-job schema mode." >&2
    exit 1
  fi
  printf '%s' "${api_token}"
}

hostinger_schema_project_delete() {
  local project_name="$1"
  local api_token="$2"
  local api_base="${HOSTINGER_API_BASE_URL:-https://developers.hostinger.com/api}"
  local vps_id="${HOSTINGER_VPS_ID:-1695814}"

  curl -fsS -X DELETE \
    -H "Authorization: Bearer ${api_token}" \
    "${api_base}/vps/v1/virtual-machines/${vps_id}/docker/${project_name}/down" \
    >/dev/null 2>&1 || true
}

hostinger_schema_project_logs() {
  local project_name="$1"
  local api_token="$2"
  local api_base="${HOSTINGER_API_BASE_URL:-https://developers.hostinger.com/api}"
  local vps_id="${HOSTINGER_VPS_ID:-1695814}"

  curl -fsS \
    -H "Authorization: Bearer ${api_token}" \
    "${api_base}/vps/v1/virtual-machines/${vps_id}/docker/${project_name}/logs" \
    | jq -r '.[]? as $service | $service.entries[]? | (($service.service // "") + " " + (.line // ""))'
}

schema_sql_url() {
  local sql_file="$1"
  local sql_abs
  local sql_rel
  local commit
  local remote_url
  local repo_path

  if [[ -n "${HOSTINGER_SCHEMA_SQL_URL:-}" ]]; then
    printf '%s' "${HOSTINGER_SCHEMA_SQL_URL}"
    return
  fi

  sql_abs="$(cd "$(dirname "${sql_file}")" && pwd)/$(basename "${sql_file}")"
  case "${sql_abs}" in
    "${REPO_ROOT}"/*)
      sql_rel="${sql_abs#"${REPO_ROOT}/"}"
      ;;
    *)
      echo "Hostinger schema job can only fetch SQL files committed under ${REPO_ROOT}; got ${sql_file}." >&2
      exit 1
      ;;
  esac

  if [[ -n "${HOSTINGER_SCHEMA_SQL_BASE_URL:-}" ]]; then
    printf '%s/%s' "${HOSTINGER_SCHEMA_SQL_BASE_URL%/}" "${sql_rel}"
    return
  fi

  require_command git
  commit="${HOSTINGER_SCHEMA_GIT_REF:-$(git -C "${REPO_ROOT}" rev-parse HEAD)}"
  remote_url="$(git -C "${REPO_ROOT}" config --get remote.origin.url)"
  case "${remote_url}" in
    https://github.com/*)
      repo_path="${remote_url#https://github.com/}"
      ;;
    git@github.com:*)
      repo_path="${remote_url#git@github.com:}"
      ;;
    ssh://git@github.com/*)
      repo_path="${remote_url#ssh://git@github.com/}"
      ;;
    *)
      echo "Cannot derive a raw GitHub SQL URL from remote.origin.url='${remote_url}'." >&2
      echo "Set HOSTINGER_SCHEMA_SQL_URL or HOSTINGER_SCHEMA_SQL_BASE_URL." >&2
      exit 1
      ;;
  esac
  repo_path="${repo_path%.git}"
  printf 'https://raw.githubusercontent.com/%s/%s/%s' "${repo_path}" "${commit}" "${sql_rel}"
}

apply_file_with_hostinger_job() {
  local sql_file="$1"
  local sql_name
  local api_token
  local api_base="${HOSTINGER_API_BASE_URL:-https://developers.hostinger.com/api}"
  local vps_id="${HOSTINGER_VPS_ID:-1695814}"
  local network="${HOSTINGER_SCHEMA_DOCKER_NETWORK:-supabase-aethos_default}"
  local project_name
  local sql_url
  local compose_content
  local environment
  local response
  local body
  local status_code
  local logs_text
  local i

  require_command curl
  require_command jq

  sql_name="$(basename "${sql_file}")"
  api_token="$(hostinger_api_token)"
  project_name="${HOSTINGER_SCHEMA_PROJECT_NAME:-transmuter-schema-${ENVIRONMENT}-$(date +%Y%m%d%H%M%S)}"
  sql_url="$(schema_sql_url "${sql_file}")"
  compose_content="$(cat <<YAML
services:
  schema:
    image: postgres:15-alpine
    command:
      - sh
      - -ec
      - |
        apk add --no-cache ca-certificates curl >/dev/null
        curl -fsSL "\${MIGRATION_SQL_URL}" -o /tmp/change.sql
        psql "\${SCHEMA_DATABASE_URL}" -v ON_ERROR_STOP=1 --single-transaction -f /tmp/change.sql
        echo TRANSMUTER_SCHEMA_APPLY_OK
    environment:
      SCHEMA_DATABASE_URL: \${SCHEMA_DATABASE_URL:?}
      PGOPTIONS: \${PGOPTIONS:?}
      MIGRATION_SQL_URL: \${MIGRATION_SQL_URL:?}
    networks:
      - supabase
    restart: "no"

networks:
  supabase:
    external: true
    name: ${network}
YAML
)"
  environment="$(
    printf 'SCHEMA_DATABASE_URL=%s\nPGOPTIONS=%s\nMIGRATION_SQL_URL=%s\n' \
      "${INTERNAL_SCHEMA_DATABASE_URL}" \
      "${PGOPTIONS_VALUE}" \
      "${sql_url}"
  )"

  echo "Applying ${sql_file} to ${ENVIRONMENT} schema '${TARGET_SCHEMA}' via Hostinger schema job '${project_name}'."
  echo "Schema job will fetch ${sql_url}."
  response="$(
    jq -n \
      --arg project_name "${project_name}" \
      --arg content "${compose_content}" \
      --arg environment "${environment}" \
      '{project_name: $project_name, content: $content, environment: $environment}' \
      | curl -sS -w '\n%{http_code}' -X POST \
        -H "Authorization: Bearer ${api_token}" \
        -H "Content-Type: application/json" \
        -d @- \
        "${api_base}/vps/v1/virtual-machines/${vps_id}/docker"
  )"
  body="$(printf '%s\n' "${response}" | sed '$d')"
  status_code="$(printf '%s\n' "${response}" | tail -n 1)"
  if [[ "${status_code}" -lt 200 || "${status_code}" -ge 300 ]]; then
    echo "Hostinger schema job creation failed with status ${status_code}." >&2
    printf '%s\n' "${body}" >&2
    exit 1
  fi

  for ((i = 1; i <= 60; i++)); do
    logs_text="$(hostinger_schema_project_logs "${project_name}" "${api_token}" 2>/dev/null || true)"
    if printf '%s\n' "${logs_text}" | grep -q 'TRANSMUTER_SCHEMA_APPLY_OK'; then
      echo "Schema job '${project_name}' applied ${sql_name}."
      if [[ "${HOSTINGER_SCHEMA_JOB_KEEP:-0}" != "1" ]]; then
        hostinger_schema_project_delete "${project_name}" "${api_token}"
      fi
      return
    fi
    sleep 5
  done

  echo "Hostinger schema job '${project_name}' did not report success." >&2
  printf '%s\n' "${logs_text}" | tail -80 >&2
  if [[ "${HOSTINGER_SCHEMA_JOB_KEEP:-0}" != "1" ]]; then
    hostinger_schema_project_delete "${project_name}" "${api_token}"
  fi
  exit 1
}

apply_file() {
  local sql_file="$1"
  local sql_dir
  local sql_name

  if [[ ! -f "${sql_file}" ]]; then
    echo "SQL file not found: ${sql_file}" >&2
    exit 1
  fi

  if [[ "${HOSTINGER_SCHEMA_APPLY_MODE}" == "hostinger-job" ]]; then
    apply_file_with_hostinger_job "${sql_file}"
    return
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
