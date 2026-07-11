#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ "$#" -lt 1 ]]; then
  echo "At least one schema file is required for offline preflight." >&2
  exit 1
fi
for command_name in curl git; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Missing required command: ${command_name}" >&2
    exit 1
  fi
done

cd "${REPO_ROOT}"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Offline schema rollout requires a clean worktree." >&2
  exit 1
fi

current_branch="$(git branch --show-current)"
current_sha="$(git rev-parse HEAD)"
if [[ -z "${current_branch}" ]]; then
  echo "Offline schema rollout requires a pushed branch, not detached HEAD." >&2
  exit 1
fi
remote_sha="$(git ls-remote origin "refs/heads/${current_branch}" | awk '{print $1}')"
if [[ -z "${remote_sha}" || "${remote_sha}" != "${current_sha}" ]]; then
  echo "Origin branch ${current_branch} must point to ${current_sha} before offline rollout." >&2
  exit 1
fi
if [[ -n "${HOSTINGER_SCHEMA_GIT_REF:-}" \
  && "${HOSTINGER_SCHEMA_GIT_REF}" != "${current_sha}" ]]; then
  echo "HOSTINGER_SCHEMA_GIT_REF must equal the pushed checkout SHA ${current_sha}." >&2
  exit 1
fi
if [[ -n "${HOSTINGER_DEPLOY_REF:-}" && "${HOSTINGER_DEPLOY_REF}" != "${current_sha}" ]]; then
  echo "HOSTINGER_DEPLOY_REF must equal the pushed checkout SHA ${current_sha}." >&2
  exit 1
fi
if [[ -n "${HOSTINGER_COMPOSE_URL:-}" ]]; then
  echo "Offline schema rollout does not permit HOSTINGER_COMPOSE_URL overrides." >&2
  exit 1
fi
if [[ -n "${HOSTINGER_SCHEMA_SQL_URL:-}" || -n "${HOSTINGER_SCHEMA_SQL_BASE_URL:-}" ]]; then
  echo "Offline schema rollout does not permit SQL URL overrides." >&2
  exit 1
fi
schema_routing_overrides=(
  ENV_FILE
  SCHEMA_TARGET
  SUPABASE_SCHEMA
  DB_SCHEMA
  SCHEMA_DATABASE_URL
  DEV_SCHEMA_DATABASE_URL
  DEV_CLONE_DATABASE_URL
  TARGET_DATABASE_URL
  DATABASE_LOCAL_URL
  PROD_SCHEMA_DATABASE_URL
)
for variable_name in "${schema_routing_overrides[@]}"; do
  if [[ -n "${!variable_name+x}" ]]; then
    echo "Offline schema rollout does not permit ${variable_name} overrides." >&2
    exit 1
  fi
done

remote_url="$(git config --get remote.origin.url)"
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
    echo "Cannot derive GitHub source URL from origin ${remote_url}." >&2
    exit 1
    ;;
esac
repo_path="${repo_path%.git}"

for schema_file in "$@"; do
  schema_abs="$(cd "$(dirname "${schema_file}")" && pwd)/$(basename "${schema_file}")"
  case "${schema_abs}" in
    "${REPO_ROOT}"/*)
      schema_rel="${schema_abs#"${REPO_ROOT}/"}"
      ;;
    *)
      echo "Offline schema file must be inside ${REPO_ROOT}: ${schema_file}" >&2
      exit 1
      ;;
  esac
  git cat-file -e "HEAD:${schema_rel}"

  schema_url="https://raw.githubusercontent.com/${repo_path}/${current_sha}/${schema_rel}"
  curl -fsSL --max-time 20 --output /dev/null "${schema_url}"
done

echo "Offline schema source preflight passed for ${current_branch}@${current_sha:0:12}."
