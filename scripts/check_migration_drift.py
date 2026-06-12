"""Check legacy infra Supabase migrations against the canonical migration tree."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DIR = ROOT / "supabase" / "migrations"
LEGACY_DIR = ROOT / "infra" / "supabase" / "migrations"


def main() -> int:
    failures = 0
    if not CANONICAL_DIR.exists():
        print(f"::error::Missing canonical migration directory: {CANONICAL_DIR}")
        return 1
    if not LEGACY_DIR.exists():
        print("Legacy migration directory is absent; no drift check needed.")
        return 0

    canonical = {path.name: path for path in CANONICAL_DIR.glob("*.sql")}
    legacy = {path.name: path for path in LEGACY_DIR.glob("*.sql")}

    for name, legacy_path in sorted(legacy.items()):
        canonical_path = canonical.get(name)
        if canonical_path is None:
            print(
                f"::error file={legacy_path.relative_to(ROOT)}::Legacy migration has no canonical counterpart"
            )
            failures += 1
            continue
        if legacy_path.read_bytes() != canonical_path.read_bytes():
            print(
                f"::error file={legacy_path.relative_to(ROOT)}::Legacy migration differs from "
                f"{canonical_path.relative_to(ROOT)}"
            )
            failures += 1

    canonical_only = sorted(set(canonical) - set(legacy))
    if canonical_only:
        print(
            "::notice::Canonical migration directory contains "
            f"{len(canonical_only)} files not mirrored in legacy infra/supabase/migrations."
        )
        print("::notice::New migrations should be added only to supabase/migrations.")

    if failures:
        print(f"Migration drift check failed with {failures} issue(s).")
        return 1
    print("Migration drift check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
