#!/usr/bin/env bash

# Load Hostinger deployment control values from dotenv files without sourcing
# the full runtime environment into the current shell.
load_hostinger_control_env() {
  local env_file="$1"
  local key line value
  local control_keys=(
    HOSTINGER_API_KEY
    HOSTINGER_API_TOKEN
    HOSTINGER_API_BASE_URL
    HOSTINGER_VPS_ID
    HOSTINGER_PUBLIC_IP
    HOSTINGER_SCHEMA_DATABASE_HOST
    HOSTINGER_SCHEMA_APPLY_MODE
    HOSTINGER_SCHEMA_DOCKER_NETWORK
  )

  [[ -f "${env_file}" ]] || return 0

  for key in "${control_keys[@]}"; do
    if [[ -n "${!key+x}" ]]; then
      continue
    fi
    line="$(grep -E "^[[:space:]]*${key}=" "${env_file}" | tail -n 1 || true)"
    [[ -n "${line}" ]] || continue
    value="${line#*=}"
    value="${value%$'\r'}"
    case "${value}" in
      \"*\")
        value="${value#\"}"
        value="${value%\"}"
        ;;
      \'*\')
        value="${value#\'}"
        value="${value%\'}"
        ;;
    esac
    export "${key}=${value}"
  done
}
