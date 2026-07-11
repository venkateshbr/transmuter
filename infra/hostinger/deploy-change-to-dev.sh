#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REFRESH_SCHEMA=0
SKIP_VALIDATE=0
OFFLINE_SCHEMA=0
SCHEMA_FILES=()

usage() {
  cat <<'USAGE'
Deploy the current checkout to the Hostinger dev environment.

Usage:
  ./infra/hostinger/deploy-change-to-dev.sh
  ./infra/hostinger/deploy-change-to-dev.sh --schema path/to/change.sql
  ./infra/hostinger/deploy-change-to-dev.sh --offline-schema --schema path/to/change.sql
  ./infra/hostinger/deploy-change-to-dev.sh --refresh-schema --schema path/to/change.sql

Options:
  --schema FILE      Apply a SQL schema/data-change file to transmuter_dev before deploying.
                    Repeat for multiple files; files are applied in argument order.
  --refresh-schema  Reset transmuter_dev from production transmuter before applying schema files.
  --offline-schema  Stop and verify the dev project before applying marked offline migrations.
  --skip-validate   Deploy only; skip local/public health checks.

Temporary TLS workaround:
  ALLOW_INSECURE_TLS=1 ./infra/hostinger/deploy-change-to-dev.sh

Offline failure recovery:
  The project remains stopped. Fix, commit, push, and rerun the offline rollout;
  do not restart pre-migration code after the migration commits.
USAGE
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --schema)
      if [[ -z "${2:-}" ]]; then
        echo "--schema requires a SQL file path." >&2
        exit 1
      fi
      SCHEMA_FILES+=("$2")
      shift 2
      ;;
    --refresh-schema)
      REFRESH_SCHEMA=1
      shift
      ;;
    --skip-validate)
      SKIP_VALIDATE=1
      shift
      ;;
    --offline-schema)
      OFFLINE_SCHEMA=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "${OFFLINE_SCHEMA}" == "1" && "${REFRESH_SCHEMA}" == "1" ]]; then
  echo "--offline-schema cannot be combined with --refresh-schema." >&2
  exit 1
fi

if [[ "${REFRESH_SCHEMA}" == "1" ]]; then
  echo "Refreshing transmuter_dev from production transmuter."
  (
    set -a
    # shellcheck source=/dev/null
    . "${SCRIPT_DIR}/.env.dev"
    set +a
    POSTGRES_DOCKER_NETWORK="${POSTGRES_DOCKER_NETWORK:-supabase-aethos_default}" \
      RESET_TARGET_SCHEMA=true \
      CONFIRM_RESET_DEV_SCHEMA=1 \
      "${SCRIPT_DIR}/clone_schema_to_dev.sh"
  )
fi

export HOSTINGER_PROJECT_NAME="${HOSTINGER_PROJECT_NAME:-transmuter-dev-hostinger}"
export HOSTINGER_VPS_ID="${HOSTINGER_VPS_ID:-1695814}"
export HOSTINGER_PUBLIC_IP="${HOSTINGER_PUBLIC_IP:-76.13.208.106}"
export HOSTINGER_SCHEMA_DATABASE_HOST="${HOSTINGER_SCHEMA_DATABASE_HOST:-${HOSTINGER_PUBLIC_IP}}"
export HOSTINGER_SCHEMA_APPLY_MODE="${HOSTINGER_SCHEMA_APPLY_MODE:-hostinger-job}"
export HOSTINGER_STOP_PROJECTS="${HOSTINGER_STOP_PROJECTS:-${HOSTINGER_PROJECT_NAME}}"

stop_projects=()
if [[ "${OFFLINE_SCHEMA}" == "1" ]]; then
  read -r -a stop_projects <<<"${HOSTINGER_STOP_PROJECTS}"
  validated_stop_projects=""
  for project_name in "${stop_projects[@]}"; do
    if [[ ! "${project_name}" =~ ^[A-Za-z0-9_-]+$ ]]; then
      echo "Invalid offline stop project: ${project_name}" >&2
      exit 1
    fi
    if [[ " ${validated_stop_projects} " == *" ${project_name} "* ]]; then
      echo "Duplicate offline stop project: ${project_name}" >&2
      exit 1
    fi
    validated_stop_projects="${validated_stop_projects} ${project_name}"
  done
  if [[ "${#stop_projects[@]}" -ne 1 \
    || "${stop_projects[0]}" != "transmuter-dev-hostinger" ]]; then
    echo "Offline dev rollout stop set must be exactly: transmuter-dev-hostinger." >&2
    exit 1
  fi
fi

if [[ "${#SCHEMA_FILES[@]}" -gt 0 ]]; then
  for schema_file in "${SCHEMA_FILES[@]}"; do
    if [[ ! -f "${schema_file}" || ! -r "${schema_file}" ]]; then
      echo "Schema file is not readable: ${schema_file}" >&2
      exit 1
    fi
    if grep -Fq "Apply with the application stack stopped" "${schema_file}" \
      && [[ "${OFFLINE_SCHEMA}" != "1" ]]; then
      echo "${schema_file} requires --offline-schema." >&2
      exit 1
    fi
  done
  if [[ "${OFFLINE_SCHEMA}" == "1" ]]; then
    "${SCRIPT_DIR}/preflight-offline-schema.sh" "${SCHEMA_FILES[@]}"
    pinned_sha="$(git rev-parse HEAD)"
    export HOSTINGER_SCHEMA_GIT_REF="${pinned_sha}"
    export HOSTINGER_DEPLOY_REF="${pinned_sha}"
    unset HOSTINGER_COMPOSE_URL
    for project_name in "${stop_projects[@]}"; do
      ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/.env.dev}" \
        HOSTINGER_PROJECT_NAME="${project_name}" \
        CONFIRM_STOP_PROJECT=1 \
        EXPECTED_HOSTINGER_PROJECT_NAME="${project_name}" \
        "${SCRIPT_DIR}/stop-docker-project.sh"
    done
    for project_name in "${stop_projects[@]}"; do
      ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/.env.dev}" \
        HOSTINGER_PROJECT_NAME="${project_name}" \
        CONFIRM_STOP_PROJECT=1 \
        EXPECTED_HOSTINGER_PROJECT_NAME="${project_name}" \
        VERIFY_STOPPED_ONLY=1 \
        "${SCRIPT_DIR}/stop-docker-project.sh"
    done
  fi
  OFFLINE_SCHEMA_PINNED="${OFFLINE_SCHEMA}" \
    OFFLINE_SCHEMA_GIT_REF="${HOSTINGER_SCHEMA_GIT_REF:-}" \
    "${SCRIPT_DIR}/apply-schema-sql.sh" dev "${SCHEMA_FILES[@]}"
elif [[ "${OFFLINE_SCHEMA}" == "1" ]]; then
  echo "--offline-schema requires at least one --schema file." >&2
  exit 1
fi

"${SCRIPT_DIR}/deploy-dev.sh"

if [[ "${SKIP_VALIDATE}" != "1" ]]; then
  "${SCRIPT_DIR}/validate-dev.sh"
fi

echo "Dev deployment command completed."
