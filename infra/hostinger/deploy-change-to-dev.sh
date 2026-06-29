#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REFRESH_SCHEMA=0
SKIP_VALIDATE=0
SCHEMA_FILES=()

usage() {
  cat <<'USAGE'
Deploy the current checkout to the Hostinger dev environment.

Usage:
  ./infra/hostinger/deploy-change-to-dev.sh
  ./infra/hostinger/deploy-change-to-dev.sh --schema path/to/change.sql
  ./infra/hostinger/deploy-change-to-dev.sh --refresh-schema --schema path/to/change.sql

Options:
  --schema FILE      Apply a SQL schema/data-change file to transmuter_dev before deploying.
                    Repeat for multiple files; files are applied in argument order.
  --refresh-schema  Reset transmuter_dev from production transmuter before applying schema files.
  --skip-validate   Deploy only; skip local/public health checks.

Deployment:
  Default deploy mode is remote Hostinger VPS Docker Manager API. Dev and
  production are separate Docker Compose projects on the same VPS.
  Set HOSTINGER_DEPLOY_MODE=local only when running directly on the VPS.
  Schema SQL helpers require a database URL reachable from this machine.

Temporary TLS workaround:
  ALLOW_INSECURE_TLS=1 ./infra/hostinger/deploy-change-to-dev.sh
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

if [[ "${#SCHEMA_FILES[@]}" -gt 0 ]]; then
  "${SCRIPT_DIR}/apply-schema-sql.sh" dev "${SCHEMA_FILES[@]}"
fi

"${SCRIPT_DIR}/deploy-dev.sh"

if [[ "${SKIP_VALIDATE}" != "1" ]]; then
  "${SCRIPT_DIR}/validate-dev.sh"
fi

echo "Dev deployment command completed."
