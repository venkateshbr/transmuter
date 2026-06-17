#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SKIP_VALIDATE=0
SCHEMA_FILES=()

usage() {
  cat <<'USAGE'
Promote the currently checked-out commit to the Hostinger production stack.

Usage:
  CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh
  CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh --schema path/to/change.sql

Options:
  --schema FILE     Apply a SQL schema/data-change file to production schema
                   transmuter before deploying. Repeat for multiple files.
  --skip-validate  Deploy only; skip local/public health checks.

Merge and pull the reviewed production commit before running this command.
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

if [[ "${#SCHEMA_FILES[@]}" -gt 0 ]]; then
  CONFIRM_PROD_SCHEMA=1 "${SCRIPT_DIR}/apply-schema-sql.sh" prod "${SCHEMA_FILES[@]}"
fi

"${SCRIPT_DIR}/deploy-prod.sh"

if [[ "${SKIP_VALIDATE}" != "1" ]]; then
  "${SCRIPT_DIR}/validate-prod.sh"
fi

echo "Production promotion command completed."
