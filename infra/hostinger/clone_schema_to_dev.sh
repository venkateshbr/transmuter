#!/usr/bin/env bash
set -euo pipefail

SOURCE_SCHEMA="${SOURCE_SCHEMA:-transmuter}"
TARGET_SCHEMA="${TARGET_SCHEMA:-transmuter_dev}"
RESET_TARGET_SCHEMA="${RESET_TARGET_SCHEMA:-false}"
POSTGRES_DOCKER_IMAGE="${POSTGRES_DOCKER_IMAGE:-postgres:15-alpine}"
POSTGRES_DOCKER_NETWORK="${POSTGRES_DOCKER_NETWORK:-host}"

usage() {
  cat <<'USAGE'
Clone the production Transmuter schema and data into the Hostinger dev schema.

Required:
  DEV_CLONE_DATABASE_URL  PostgreSQL URL for the Hostinger Supabase database.

Optional:
  SOURCE_SCHEMA=transmuter
  TARGET_SCHEMA=transmuter_dev
  RESET_TARGET_SCHEMA=false
  CONFIRM_RESET_DEV_SCHEMA=0
  POSTGRES_DOCKER_IMAGE=postgres:15-alpine
  POSTGRES_DOCKER_NETWORK=host

Example:
  set -a
  . infra/hostinger/.env.dev
  set +a
  RESET_TARGET_SCHEMA=true CONFIRM_RESET_DEV_SCHEMA=1 \
    ./infra/hostinger/clone_schema_to_dev.sh

This copies both schema objects and table data. It does not copy Supabase Auth
users from auth.* because those are outside the Transmuter application schema.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 1
  fi
}

validate_identifier() {
  local name="$1"
  local value="$2"
  if [[ ! "${value}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "${name} must be a simple PostgreSQL identifier; got '${value}'." >&2
    exit 1
  fi
}

require_env DEV_CLONE_DATABASE_URL
validate_identifier SOURCE_SCHEMA "${SOURCE_SCHEMA}"
validate_identifier TARGET_SCHEMA "${TARGET_SCHEMA}"

if [[ "${SOURCE_SCHEMA}" == "${TARGET_SCHEMA}" ]]; then
  echo "SOURCE_SCHEMA and TARGET_SCHEMA must be different." >&2
  exit 1
fi

if [[ "${RESET_TARGET_SCHEMA}" != "true" && "${RESET_TARGET_SCHEMA}" != "false" ]]; then
  echo "RESET_TARGET_SCHEMA must be either true or false." >&2
  exit 1
fi

if [[ "${RESET_TARGET_SCHEMA}" == "true" && "${CONFIRM_RESET_DEV_SCHEMA:-0}" != "1" ]]; then
  echo "Refusing to reset ${TARGET_SCHEMA}. Set CONFIRM_RESET_DEV_SCHEMA=1 to continue." >&2
  exit 1
fi

USE_DOCKER_TOOLS=0
if ! command -v pg_dump >/dev/null 2>&1 || ! command -v psql >/dev/null 2>&1; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "Install pg_dump/psql or Docker before running this script." >&2
    exit 1
  fi
  USE_DOCKER_TOOLS=1
fi

run_psql() {
  if [[ "${USE_DOCKER_TOOLS}" == "1" ]]; then
    docker run --rm --network "${POSTGRES_DOCKER_NETWORK}" \
      -e DEV_CLONE_DATABASE_URL="${DEV_CLONE_DATABASE_URL}" \
      "${POSTGRES_DOCKER_IMAGE}" \
      sh -c 'psql "$DEV_CLONE_DATABASE_URL" "$@"' sh "$@"
  else
    psql "${DEV_CLONE_DATABASE_URL}" "$@"
  fi
}

run_pg_dump() {
  if [[ "${USE_DOCKER_TOOLS}" == "1" ]]; then
    docker run --rm --network "${POSTGRES_DOCKER_NETWORK}" \
      -e DEV_CLONE_DATABASE_URL="${DEV_CLONE_DATABASE_URL}" \
      "${POSTGRES_DOCKER_IMAGE}" \
      sh -c 'pg_dump "$DEV_CLONE_DATABASE_URL" "$@"' sh "$@"
  else
    pg_dump "${DEV_CLONE_DATABASE_URL}" "$@"
  fi
}

run_psql_file() {
  local file_path="$1"
  local file_dir
  local file_name
  file_dir="$(cd "$(dirname "${file_path}")" && pwd)"
  file_name="$(basename "${file_path}")"

  if [[ "${USE_DOCKER_TOOLS}" == "1" ]]; then
    docker run --rm --network "${POSTGRES_DOCKER_NETWORK}" \
      -e DEV_CLONE_DATABASE_URL="${DEV_CLONE_DATABASE_URL}" \
      -v "${file_dir}:/work:ro" \
      "${POSTGRES_DOCKER_IMAGE}" \
      sh -c 'psql "$DEV_CLONE_DATABASE_URL" -v ON_ERROR_STOP=1 -f "/work/$1"' sh "${file_name}"
  else
    psql "${DEV_CLONE_DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${file_path}"
  fi
}

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

RAW_DUMP="${TMP_DIR}/source_schema_and_data.sql"
REWRITTEN_DUMP="${TMP_DIR}/target_schema_and_data.sql"
PREPARE_SQL="${TMP_DIR}/prepare_target_schema.sql"
GRANTS_SQL="${TMP_DIR}/target_schema_grants.sql"
COUNT_SQL="${TMP_DIR}/target_counts.sql"

cat > "${PREPARE_SQL}" <<SQL
DO \$\$
BEGIN
  IF '${RESET_TARGET_SCHEMA}' = 'true' THEN
    EXECUTE 'DROP SCHEMA IF EXISTS "${TARGET_SCHEMA}" CASCADE';
  END IF;
END
\$\$;

CREATE SCHEMA IF NOT EXISTS "${TARGET_SCHEMA}";
SQL

cat > "${GRANTS_SQL}" <<SQL
GRANT USAGE ON SCHEMA "${TARGET_SCHEMA}" TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA "${TARGET_SCHEMA}" TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "${TARGET_SCHEMA}" TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA "${TARGET_SCHEMA}" TO anon;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA "${TARGET_SCHEMA}" TO authenticated, service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA "${TARGET_SCHEMA}" TO anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA "${TARGET_SCHEMA}" GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA "${TARGET_SCHEMA}" GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA "${TARGET_SCHEMA}" GRANT SELECT ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA "${TARGET_SCHEMA}" GRANT USAGE, SELECT ON SEQUENCES TO authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA "${TARGET_SCHEMA}" GRANT EXECUTE ON FUNCTIONS TO anon, authenticated, service_role;
SQL

cat > "${COUNT_SQL}" <<SQL
SELECT table_name
FROM information_schema.tables
WHERE table_schema = '${TARGET_SCHEMA}'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
SQL

echo "Preparing target schema '${TARGET_SCHEMA}'."
run_psql_file "${PREPARE_SQL}"

echo "Dumping schema and data from '${SOURCE_SCHEMA}'."
run_pg_dump \
  --schema="${SOURCE_SCHEMA}" \
  --no-owner \
  --no-privileges \
  --no-comments \
  --quote-all-identifiers \
  > "${RAW_DUMP}"

echo "Rewriting dump from '${SOURCE_SCHEMA}' to '${TARGET_SCHEMA}'."
sed -E \
  -e "/^CREATE SCHEMA \"${SOURCE_SCHEMA}\";/d" \
  -e "/^DROP SCHEMA \"${SOURCE_SCHEMA}\";/d" \
  -e "s/\"${SOURCE_SCHEMA}\"\\./\"${TARGET_SCHEMA}\"./g" \
  -e "s/SCHEMA \"${SOURCE_SCHEMA}\"/SCHEMA \"${TARGET_SCHEMA}\"/g" \
  -e "s/Schema: ${SOURCE_SCHEMA}/Schema: ${TARGET_SCHEMA}/g" \
  -e "s/SET search_path = \"${SOURCE_SCHEMA}\", pg_catalog;/SET search_path = \"${TARGET_SCHEMA}\", public, auth, extensions, pg_catalog;/g" \
  "${RAW_DUMP}" > "${REWRITTEN_DUMP}"

echo "Importing cloned schema and data into '${TARGET_SCHEMA}'."
run_psql_file "${REWRITTEN_DUMP}"

echo "Applying Supabase API grants for '${TARGET_SCHEMA}'."
run_psql_file "${GRANTS_SQL}"

echo "Imported table count:"
run_psql -v ON_ERROR_STOP=1 -Atc \
  "select count(*) from information_schema.tables where table_schema = '${TARGET_SCHEMA}' and table_type = 'BASE TABLE';"

echo "Key table row counts:"
for table in organizations users initiatives financial_metric_definitions financial_metric_values financial_cost_lines financial_bridge_rows; do
  run_psql -v ON_ERROR_STOP=1 -Atc \
    "select '${table}=' || count(*) from \"${TARGET_SCHEMA}\".\"${table}\";" || true
done

echo "Schema clone completed. Ensure Supabase REST exposes '${TARGET_SCHEMA}' before using the dev app."
