#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
. "${SCRIPT_DIR}/env-control.sh"

SKIP_VALIDATE=0
OFFLINE_SCHEMA=0
SCHEMA_FILES=()

usage() {
  cat <<'USAGE'
Promote the currently checked-out commit to the Hostinger production stack.

Usage:
  CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh
  CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh --schema path/to/change.sql
  CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh --offline-schema --schema path/to/change.sql

Options:
  --schema FILE     Apply a SQL schema/data-change file to production schema
                   transmuter before deploying. Repeat for multiple files.
  --skip-validate  Deploy only; skip local/public health checks.
  --offline-schema Stop and verify production before applying marked offline migrations.

Merge and pull the reviewed production commit before running this command.
If an offline step fails, leave production stopped and roll forward with a
corrected reviewed commit; never restart pre-migration code after schema commit.
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

if [[ "${CONFIRM_PROMOTE:-0}" != "1" ]]; then
  echo "Refusing to promote without explicit confirmation." >&2
  usage >&2
  exit 1
fi

cd "${REPO_ROOT}"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to promote with uncommitted changes." >&2
  exit 1
fi

current_branch="$(git branch --show-current)"
current_commit="$(git rev-parse --short HEAD)"
echo "Promoting ${current_branch}@${current_commit} to production Hostinger stack."
if [[ "${OFFLINE_SCHEMA}" == "1" ]]; then
  reject_offline_hostinger_control_overrides
  bind_offline_hostinger_controls prod
else
  HOSTINGER_STOP_PROJECTS="${HOSTINGER_STOP_PROJECTS:-transmuter transmuter-hostinger}"
fi

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
  for required_project in transmuter transmuter-hostinger; do
    if [[ " ${validated_stop_projects} " != *" ${required_project} "* ]]; then
      echo "Offline production rollout must stop ${required_project}." >&2
      exit 1
    fi
  done
  if [[ "${#stop_projects[@]}" -ne 2 ]]; then
    echo "Offline production rollout stop set must be exactly: transmuter transmuter-hostinger." >&2
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
    export ENV_FILE="${SCRIPT_DIR}/.env"
    unset HOSTINGER_COMPOSE_URL
    for project_name in "${stop_projects[@]}"; do
      ENV_FILE="${ENV_FILE}" \
        HOSTINGER_PROJECT_NAME="${project_name}" \
        HOSTINGER_VPS_ID="${HOSTINGER_VPS_ID:-1695814}" \
        CONFIRM_STOP_PROJECT=1 \
        EXPECTED_HOSTINGER_PROJECT_NAME="${project_name}" \
        "${SCRIPT_DIR}/stop-docker-project.sh"
    done
    for project_name in "${stop_projects[@]}"; do
      ENV_FILE="${ENV_FILE}" \
        HOSTINGER_PROJECT_NAME="${project_name}" \
        HOSTINGER_VPS_ID="${HOSTINGER_VPS_ID:-1695814}" \
        CONFIRM_STOP_PROJECT=1 \
        EXPECTED_HOSTINGER_PROJECT_NAME="${project_name}" \
        VERIFY_STOPPED_ONLY=1 \
        "${SCRIPT_DIR}/stop-docker-project.sh"
    done
  fi
  HOSTINGER_PROJECT_NAME="${HOSTINGER_PROJECT_NAME:-transmuter-hostinger}" \
    HOSTINGER_VPS_ID="${HOSTINGER_VPS_ID:-1695814}" \
    HOSTINGER_PUBLIC_IP="${HOSTINGER_PUBLIC_IP:-76.13.208.106}" \
    HOSTINGER_SCHEMA_DATABASE_HOST="${HOSTINGER_SCHEMA_DATABASE_HOST:-${HOSTINGER_PUBLIC_IP:-76.13.208.106}}" \
    HOSTINGER_SCHEMA_APPLY_MODE="${HOSTINGER_SCHEMA_APPLY_MODE:-hostinger-job}" \
    OFFLINE_SCHEMA_PINNED="${OFFLINE_SCHEMA}" \
    OFFLINE_SCHEMA_GIT_REF="${HOSTINGER_SCHEMA_GIT_REF:-}" \
    CONFIRM_PROD_SCHEMA=1 \
    "${SCRIPT_DIR}/apply-schema-sql.sh" prod "${SCHEMA_FILES[@]}"
elif [[ "${OFFLINE_SCHEMA}" == "1" ]]; then
  echo "--offline-schema requires at least one --schema file." >&2
  exit 1
fi

"${SCRIPT_DIR}/deploy-prod.sh"

if [[ "${SKIP_VALIDATE}" != "1" ]]; then
  "${SCRIPT_DIR}/validate-prod.sh"
fi

echo "Production promotion command completed."
