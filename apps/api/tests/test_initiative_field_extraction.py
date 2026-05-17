import json
from pathlib import Path

import pytest

from app.agents import initiative_intake_agent
from app.agents.initiative_intake_agent import (
    deterministic_field_extraction,
    extract_initiative_fields,
)


def test_deterministic_field_extraction_is_typed_and_conservative() -> None:
    result = deterministic_field_extraction(
        "Initiative: AP automation rollout. Type: cost reduction. Priority: high. "
        "Workstream: Finance operations. Country: Singapore. "
        "Value logic: reduce manual processing cost. Dependencies: ERP integration. "
        "Planned end: 2026-09-30."
    )

    assert result.trace_id
    assert result.agent_status == "deterministic_fallback"
    assert result.confidence > 0
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    assert result.draft.name == "AP automation rollout"
    assert result.draft.type == "cost_reduction"
    assert result.draft.priority == "high"
    assert result.draft.workstream == "Finance operations"
    assert result.draft.country == "Singapore"
    assert result.draft.value_logic == "reduce manual processing cost"
    assert result.draft.dependencies == "ERP integration"
    assert result.draft.planned_end and result.draft.planned_end.isoformat() == "2026-09-30"


def test_deterministic_field_extraction_returns_nulls_when_unsupported() -> None:
    result = deterministic_field_extraction("Ambiguous idea with no firm scope.")

    assert result.draft.type is None
    assert result.draft.priority is None
    assert result.draft.workstream is None
    assert result.draft.country is None
    assert result.draft.planned_end is None


@pytest.mark.asyncio
async def test_extract_initiative_fields_uses_fallback_when_ai_disabled(monkeypatch) -> None:
    monkeypatch.setattr(initiative_intake_agent.settings, "ai_enabled", False)

    result = await extract_initiative_fields("Project: pricing uplift. Type: revenue growth.")

    assert result.agent_status == "deterministic_fallback"
    assert result.draft.name == "pricing uplift"
    assert result.draft.type == "revenue_growth"


def test_initiative_intake_eval_dataset_has_twenty_golden_examples() -> None:
    eval_path = Path(__file__).resolve().parents[3] / "tests/evals/initiative_intake_evals.jsonl"
    rows = [json.loads(line) for line in eval_path.read_text().splitlines() if line.strip()]

    assert len(rows) == 20
    assert all(row["id"].startswith("ife-") for row in rows)
    assert all(row["input"]["text"] and isinstance(row["expected_output"], dict) for row in rows)
    assert all(row["difficulty"] in {"easy", "medium", "hard"} for row in rows)
    assert all(row["source"] in {"synthetic", "anonymised"} for row in rows)
