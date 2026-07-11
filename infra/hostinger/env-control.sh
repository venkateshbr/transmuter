#!/usr/bin/env bash

# Load allowlisted dotenv values as data. Hostinger environment values are not
# shell syntax and must never be evaluated with source/eval.
load_dotenv_keys() {
  local env_file="$1"
  local existing_value_mode="$2"
  shift 2
  local key line value

  [[ -f "${env_file}" ]] || return 0
  if [[ "${existing_value_mode}" != "preserve" && "${existing_value_mode}" != "replace" ]]; then
    echo "Dotenv existing-value mode must be preserve or replace." >&2
    return 1
  fi

  for key in "$@"; do
    if [[ ! "${key}" =~ ^[A-Z][A-Z0-9_]*$ ]]; then
      echo "Invalid dotenv key requested: ${key}" >&2
      return 1
    fi
    if [[ "${existing_value_mode}" == "replace" ]]; then
      unset "${key}"
    elif [[ -n "${!key+x}" ]]; then
      continue
    fi
    line="$(grep -E "^[[:space:]]*${key}=" "${env_file}" | tail -n 1 || true)"
    [[ -n "${line}" ]] || continue
    value="${line#*=}"
    value="${value%$'\r'}"
    if [[ "${#value}" -ge 2 && "${value}" == \"*\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "${#value}" -ge 2 && "${value}" == \'*\' ]]; then
      value="${value:1:${#value}-2}"
    fi
    export "${key}=${value}"
  done
}

load_hostinger_control_env() {
  local env_file="$1"
  local keys=(
    HOSTINGER_API_KEY
    HOSTINGER_API_TOKEN
    HOSTINGER_API_BASE_URL
    HOSTINGER_VPS_ID
    HOSTINGER_PUBLIC_IP
    HOSTINGER_SCHEMA_DATABASE_HOST
    HOSTINGER_SCHEMA_APPLY_MODE
    HOSTINGER_SCHEMA_DOCKER_NETWORK
  )

  load_dotenv_keys "${env_file}" preserve "${keys[@]}"
}

load_hostinger_schema_env() {
  local env_file="$1"
  local existing_value_mode="${2:-preserve}"
  local keys=(
    SCHEMA_TARGET
    SUPABASE_SCHEMA
    DB_SCHEMA
    SCHEMA_DATABASE_URL
    DEV_SCHEMA_DATABASE_URL
    DEV_CLONE_DATABASE_URL
    TARGET_DATABASE_URL
    DATABASE_LOCAL_URL
    PROD_SCHEMA_DATABASE_URL
    POSTGRES_DOCKER_IMAGE
    POSTGRES_DOCKER_NETWORK
  )

  load_dotenv_keys "${env_file}" "${existing_value_mode}" "${keys[@]}"
}

reject_offline_hostinger_control_overrides() {
  local variable_name
  local variables=(
    HOSTINGER_API_BASE_URL
    HOSTINGER_VPS_ID
    HOSTINGER_PUBLIC_IP
    HOSTINGER_PROJECT_NAME
    HOSTINGER_STOP_PROJECTS
    HOSTINGER_SCHEMA_DATABASE_HOST
    HOSTINGER_SCHEMA_APPLY_MODE
    HOSTINGER_SCHEMA_DOCKER_NETWORK
    HOSTINGER_SCHEMA_PROJECT_NAME
    HOSTINGER_SCHEMA_JOB_KEEP
    HOSTINGER_COMPOSE_PATH
    HOSTINGER_REPOSITORY_URL
    HOSTINGER_PRESERVE_REMOTE_ENV
    SKIP_GIT_REMOTE_CHECK
    ALLOW_DIRTY_DEPLOY
    TRANSMUTER_COMPOSE_PROJECT
    OFFLINE_HOSTINGER_CONTROLS_LOCKED
    OFFLINE_HOSTINGER_ENVIRONMENT
  )

  for variable_name in "${variables[@]}"; do
    if [[ -n "${!variable_name+x}" ]]; then
      echo "Offline schema rollout does not permit ${variable_name} overrides." >&2
      return 1
    fi
  done
}

bind_offline_hostinger_controls() {
  local environment="$1"

  export HOSTINGER_API_BASE_URL="https://developers.hostinger.com/api"
  export HOSTINGER_VPS_ID="1695814"
  export HOSTINGER_PUBLIC_IP="76.13.208.106"
  export HOSTINGER_SCHEMA_DATABASE_HOST="76.13.208.106"
  export HOSTINGER_SCHEMA_APPLY_MODE="hostinger-job"
  export HOSTINGER_SCHEMA_DOCKER_NETWORK="supabase-aethos_default"
  export HOSTINGER_SCHEMA_JOB_KEEP="0"
  export HOSTINGER_COMPOSE_PATH="docker-compose.hostinger.yml"
  export HOSTINGER_REPOSITORY_URL="https://github.com/venkateshbr/transmuter"
  export HOSTINGER_PRESERVE_REMOTE_ENV="1"
  export SKIP_GIT_REMOTE_CHECK="0"
  export ALLOW_DIRTY_DEPLOY="0"
  export OFFLINE_HOSTINGER_CONTROLS_LOCKED="1"
  export OFFLINE_HOSTINGER_ENVIRONMENT="${environment}"

  case "${environment}" in
    dev)
      export HOSTINGER_PROJECT_NAME="transmuter-dev-hostinger"
      export HOSTINGER_STOP_PROJECTS="transmuter-dev-hostinger"
      export TRANSMUTER_COMPOSE_PROJECT="transmuter-dev-hostinger"
      ;;
    prod)
      export HOSTINGER_PROJECT_NAME="transmuter-hostinger"
      export HOSTINGER_STOP_PROJECTS="transmuter transmuter-hostinger"
      export TRANSMUTER_COMPOSE_PROJECT="transmuter-hostinger"
      ;;
    *)
      echo "Offline Hostinger environment must be dev or prod; got ${environment}." >&2
      return 1
      ;;
  esac
}

assert_offline_hostinger_controls() {
  local expected_project expected_stop_projects expected_compose_project

  if [[ "${OFFLINE_HOSTINGER_CONTROLS_LOCKED:-0}" != "1" ]]; then
    echo "Offline Hostinger controls are not locked." >&2
    return 1
  fi
  case "${OFFLINE_HOSTINGER_ENVIRONMENT:-}" in
    dev)
      expected_project="transmuter-dev-hostinger"
      expected_stop_projects="transmuter-dev-hostinger"
      expected_compose_project="transmuter-dev-hostinger"
      ;;
    prod)
      expected_project="transmuter-hostinger"
      expected_stop_projects="transmuter transmuter-hostinger"
      expected_compose_project="transmuter-hostinger"
      ;;
    *)
      echo "Offline Hostinger environment lock is invalid." >&2
      return 1
      ;;
  esac

  [[ "${HOSTINGER_API_BASE_URL:-}" == "https://developers.hostinger.com/api" ]] || return 1
  [[ "${HOSTINGER_VPS_ID:-}" == "1695814" ]] || return 1
  [[ "${HOSTINGER_PUBLIC_IP:-}" == "76.13.208.106" ]] || return 1
  [[ "${HOSTINGER_SCHEMA_DATABASE_HOST:-}" == "76.13.208.106" ]] || return 1
  [[ "${HOSTINGER_SCHEMA_APPLY_MODE:-}" == "hostinger-job" ]] || return 1
  [[ "${HOSTINGER_SCHEMA_DOCKER_NETWORK:-}" == "supabase-aethos_default" ]] || return 1
  [[ "${HOSTINGER_SCHEMA_JOB_KEEP:-}" == "0" ]] || return 1
  [[ "${HOSTINGER_COMPOSE_PATH:-}" == "docker-compose.hostinger.yml" ]] || return 1
  [[ "${HOSTINGER_REPOSITORY_URL:-}" == "https://github.com/venkateshbr/transmuter" ]] || return 1
  [[ "${HOSTINGER_PRESERVE_REMOTE_ENV:-}" == "1" ]] || return 1
  [[ "${SKIP_GIT_REMOTE_CHECK:-}" == "0" ]] || return 1
  [[ "${ALLOW_DIRTY_DEPLOY:-}" == "0" ]] || return 1
  [[ "${HOSTINGER_PROJECT_NAME:-}" == "${expected_project}" ]] || return 1
  [[ "${HOSTINGER_STOP_PROJECTS:-}" == "${expected_stop_projects}" ]] || return 1
  [[ "${TRANSMUTER_COMPOSE_PROJECT:-}" == "${expected_compose_project}" ]] || return 1
}
