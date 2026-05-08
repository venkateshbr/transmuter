"""Validate Transmuter YAML specs against their JSON schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]

SPEC_GROUPS = [
    ("AgentSpec", ROOT / "schemas" / "agent_spec.json", ROOT / "agents" / "specs"),
    ("WorkflowSpec", ROOT / "schemas" / "workflow_spec.json", ROOT / "workflows"),
]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _validate_group(name: str, schema_path: Path, spec_dir: Path) -> int:
    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema)
    failures = 0
    files = sorted(spec_dir.glob("*.yaml"))
    if not files:
        print(f"::notice::{name}: no specs found in {spec_dir.relative_to(ROOT)}")
        return failures

    for spec_path in files:
        spec = _load_yaml(spec_path)
        errors = sorted(validator.iter_errors(spec), key=lambda error: list(error.path))
        if errors:
            failures += 1
            print(f"::error file={spec_path.relative_to(ROOT)}::{name} validation failed")
            for error in errors:
                path = ".".join(str(part) for part in error.path) or "<root>"
                print(f"  - {path}: {error.message}")
        else:
            print(f"Validated {spec_path.relative_to(ROOT)}")
    return failures


def main() -> int:
    failures = 0
    for name, schema_path, spec_dir in SPEC_GROUPS:
        failures += _validate_group(name, schema_path, spec_dir)
    if failures:
        print(f"Spec validation failed for {failures} file group(s)")
        return 1
    print("All specs passed schema validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
