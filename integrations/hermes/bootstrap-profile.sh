#!/usr/bin/env sh
set -eu

DATA_DIR="${HERMES_DATA_DIR:-/opt/data}"
PROFILE_SRC="${TRANSMUTER_PROFILE_SRC:-/opt/transmuter/profile}"
REFRESH_PROFILE="${TRANSMUTER_HERMES_REFRESH_PROFILE:-false}"

copy_if_missing_or_refresh() {
  src="$1"
  dst="$2"
  if [ "$REFRESH_PROFILE" = "true" ] || [ ! -f "$dst" ]; then
    cp "$src" "$dst"
  fi
}

mkdir -p "$DATA_DIR" "$DATA_DIR/skills"
copy_if_missing_or_refresh "$PROFILE_SRC/SOUL.md" "$DATA_DIR/SOUL.md"
copy_if_missing_or_refresh "$PROFILE_SRC/config.yaml" "$DATA_DIR/config.yaml"
copy_if_missing_or_refresh "$PROFILE_SRC/mcp.json" "$DATA_DIR/mcp.json"
cp -R "$PROFILE_SRC/skills/." "$DATA_DIR/skills/"

exec hermes "$@"
