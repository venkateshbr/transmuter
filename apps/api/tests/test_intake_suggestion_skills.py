import json
from pathlib import Path

from app.agents.initiative_intake_agent import scan_risk_patterns, suggest_kpis
from app.domain.initiative_intake import InitiativeDraft


def test_kpi_suggestion_returns_typed_domain_relevant_items() -> None:
    result = suggest_kpis(
        initiative_type="revenue_growth",
        initiative_name="Pricing uplift",
        value_logic="increase gross margin from enterprise deals",
    )

    names = [item.name for item in result.suggestions]
    assert 3 <= len(result.suggestions) <= 5
    assert "Gross margin uplift" in names
    assert "Incremental gross margin" in names
    assert all(item.accepted for item in result.suggestions)
    assert all(item.rationale for item in result.suggestions)


def test_risk_pattern_scan_returns_reviewable_risks() -> None:
    result = scan_risk_patterns(
        InitiativeDraft(
            name="AP automation",
            type="cost_reduction",
            dependencies="ERP integration",
        )
    )

    assert 2 <= len(result.risks) <= 4
    assert any(risk.type == "financial" for risk in result.risks)
    assert any("AP automation" in risk.description for risk in result.risks)
    assert all(risk.accepted for risk in result.risks)
    assert all(risk.mitigation for risk in result.risks)
    assert all(risk.rationale for risk in result.risks)


def test_kpi_and_risk_eval_datasets_have_ten_examples_each() -> None:
    root = Path(__file__).resolve().parents[3]
    kpi_rows = [
        json.loads(line)
        for line in (root / "tests/evals/kpi_suggestion_evals.jsonl").read_text().splitlines()
        if line.strip()
    ]
    risk_rows = [
        json.loads(line)
        for line in (root / "tests/evals/risk_pattern_scan_evals.jsonl").read_text().splitlines()
        if line.strip()
    ]

    assert len(kpi_rows) == 10
    assert len(risk_rows) == 10
    assert all(row["expected_names"] for row in kpi_rows)
    assert all(row["input"]["name"] for row in risk_rows)
