#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ "${CONFIRM_PROMOTE:-0}" != "1" ]]; then
  cat >&2 <<'USAGE'
Refusing to promote without explicit confirmation.

Usage:
  CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh

This deploys the currently checked-out repository state to the production
Hostinger stack. Merge and pull main before running it for a reviewed release.
USAGE
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

exec "${SCRIPT_DIR}/deploy-prod.sh" "$@"
