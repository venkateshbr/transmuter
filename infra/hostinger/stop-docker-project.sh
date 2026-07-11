#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/.env}"

# shellcheck source=/dev/null
. "${SCRIPT_DIR}/env-control.sh"
load_hostinger_control_env "${REPO_ROOT}/.env"
load_hostinger_control_env "${ENV_FILE}"

HOSTINGER_API_BASE_URL="${HOSTINGER_API_BASE_URL:-https://developers.hostinger.com/api}"
HOSTINGER_VPS_ID="${HOSTINGER_VPS_ID:-1695814}"
HOSTINGER_PROJECT_NAME="${HOSTINGER_PROJECT_NAME:-transmuter-hostinger}"
API_TOKEN="${HOSTINGER_API_TOKEN:-${HOSTINGER_API_KEY:-}}"

if [[ "${CONFIRM_STOP_PROJECT:-0}" != "1" ]]; then
  echo "Refusing to stop ${HOSTINGER_PROJECT_NAME} without CONFIRM_STOP_PROJECT=1." >&2
  exit 1
fi
if [[ -z "${EXPECTED_HOSTINGER_PROJECT_NAME:-}" \
  || "${EXPECTED_HOSTINGER_PROJECT_NAME}" != "${HOSTINGER_PROJECT_NAME}" ]]; then
  echo "EXPECTED_HOSTINGER_PROJECT_NAME must exactly match ${HOSTINGER_PROJECT_NAME}." >&2
  exit 1
fi

for command_name in curl jq; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Missing required command: ${command_name}" >&2
    exit 1
  fi
done

if [[ -z "${API_TOKEN}" ]]; then
  echo "Set HOSTINGER_API_KEY or HOSTINGER_API_TOKEN before stopping the project." >&2
  exit 1
fi
if [[ ! "${HOSTINGER_PROJECT_NAME}" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "HOSTINGER_PROJECT_NAME contains unsupported characters." >&2
  exit 1
fi

project_url="${HOSTINGER_API_BASE_URL}/vps/v1/virtual-machines/${HOSTINGER_VPS_ID}/docker/${HOSTINGER_PROJECT_NAME}"

active_container_count() {
  curl -fsS \
    -H "Authorization: Bearer ${API_TOKEN}" \
    "${project_url}/containers" \
    | jq '[if type == "array" then .[] else (.data // [])[] end | select(.state == "running" or .state == "restarting" or .state == "stopping" or .state == "paused")] | length'
}

initial_active_count="$(active_container_count)"
if [[ "${initial_active_count}" == "0" ]]; then
  echo "Hostinger project ${HOSTINGER_PROJECT_NAME} is already stopped."
  exit 0
fi
if [[ "${VERIFY_STOPPED_ONLY:-0}" == "1" ]]; then
  echo "Hostinger project ${HOSTINGER_PROJECT_NAME} has ${initial_active_count} active container(s)." >&2
  exit 1
fi

response="$(
  curl -sS -w '\n%{http_code}' -X POST \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    "${project_url}/stop"
)"
body="$(printf '%s\n' "${response}" | sed '$d')"
status_code="$(printf '%s\n' "${response}" | tail -n 1)"
if [[ "${status_code}" -lt 200 || "${status_code}" -ge 300 ]]; then
  echo "Hostinger project stop failed with status ${status_code}." >&2
  exit 1
fi

action_id="$(printf '%s' "${body}" | jq -r '.id // .data.id // empty')"
if [[ -z "${action_id}" || ! "${action_id}" =~ ^[0-9]+$ ]]; then
  echo "Hostinger project stop did not return an action id." >&2
  exit 1
fi

echo "Waiting for Hostinger stop action ${action_id} on ${HOSTINGER_PROJECT_NAME}."
for _ in $(seq 1 60); do
  action_state="$(
    curl -fsS \
      -H "Authorization: Bearer ${API_TOKEN}" \
      "${HOSTINGER_API_BASE_URL}/vps/v1/virtual-machines/${HOSTINGER_VPS_ID}/actions/${action_id}" \
      | jq -r '.state // .data.state // empty'
  )"
  case "${action_state}" in
    success)
      break
      ;;
    error)
      echo "Hostinger stop action ${action_id} failed." >&2
      exit 1
      ;;
  esac
  sleep 5
done

if [[ "${action_state:-}" != "success" ]]; then
  echo "Timed out waiting for Hostinger stop action ${action_id}." >&2
  exit 1
fi

for _ in $(seq 1 30); do
  active_count="$(active_container_count)"
  if [[ "${active_count}" == "0" ]]; then
    echo "Hostinger project ${HOSTINGER_PROJECT_NAME} is stopped."
    exit 0
  fi
  sleep 2
done

echo "Hostinger project still has active containers after stop action ${action_id}." >&2
exit 1
