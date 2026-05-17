from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agents.initiative_intake_agent import (
    deterministic_field_extraction,
    scan_risk_patterns,
    suggest_kpis,
)
from app.agents.meeting_notes_agent import (
    chunk_transcript,
    extract_action_items,
    extract_meeting_decisions,
)
from app.core.config import settings
from app.domain.initiative_intake import InitiativeDraft
from app.domain.meeting_notes import MeetingAttendeeContext

DATASET_DIR = Path(__file__).resolve().parent
EXTRACTION_THRESHOLD = 0.85
NARRATIVE_THRESHOLD = 0.80
CORRECTION_RATE_THRESHOLD = 0.10
LLM_JUDGE_MODEL = os.environ.get("TRANSMUTER_EVAL_JUDGE_MODEL", "anthropic/claude-sonnet-4-6")


@dataclass(frozen=True)
class EvalMetric:
    name: str
    score: float

    @property
    def correction_rate(self) -> float:
        return round(1 - self.score, 4)


def test_eval_datasets_cover_required_workflows() -> None:
    expected = {
        "initiative_intake_evals.jsonl",
        "meeting_notes_evals.jsonl",
        "status_update_evals.jsonl",
    }

    present = {path.name for path in DATASET_DIR.glob("*.jsonl")}

    assert expected <= present
    assert all(len(_load_jsonl(name)) >= 10 for name in expected)
    for filename in expected:
        for row in _load_jsonl(filename):
            assert {"input", "expected_output", "difficulty", "source"} <= row.keys()
            assert row["difficulty"] in {"easy", "medium", "hard"}
            assert row["source"] in {"synthetic", "anonymised"}


def test_initiative_intake_eval_suite_meets_thresholds() -> None:
    settings.ai_enabled = False
    field_metric = _score_initiative_field_extraction()
    kpi_metric = _score_kpi_suggestions()
    risk_metric = _score_risk_patterns()
    narrative_metric = _score_initiative_narrative_quality()

    _assert_metric(field_metric, EXTRACTION_THRESHOLD)
    _assert_metric(kpi_metric, EXTRACTION_THRESHOLD)
    _assert_metric(risk_metric, EXTRACTION_THRESHOLD)
    _assert_metric(narrative_metric, NARRATIVE_THRESHOLD)


def test_meeting_notes_eval_suite_meets_thresholds() -> None:
    settings.ai_enabled = False
    extraction_metric, narrative_metric = _score_meeting_notes_extraction()

    _assert_metric(extraction_metric, EXTRACTION_THRESHOLD)
    _assert_metric(narrative_metric, NARRATIVE_THRESHOLD)


def test_status_update_eval_suite_meets_thresholds() -> None:
    quality_metric = _score_status_update_dataset_quality()

    _assert_metric(quality_metric, NARRATIVE_THRESHOLD)


def test_agent_correction_rates_remain_below_incident_threshold() -> None:
    settings.ai_enabled = False
    metrics = [
        _score_initiative_field_extraction(),
        _score_kpi_suggestions(),
        _score_risk_patterns(),
        _score_meeting_notes_extraction()[0],
        _score_status_update_dataset_quality(),
    ]

    failing = [
        metric
        for metric in metrics
        if metric.correction_rate > CORRECTION_RATE_THRESHOLD
    ]

    assert failing == [], _format_failures(failing, CORRECTION_RATE_THRESHOLD, "correction_rate")


def test_llm_judge_configuration_is_available() -> None:
    assert LLM_JUDGE_MODEL == "anthropic/claude-sonnet-4-6"


def _score_initiative_field_extraction() -> EvalMetric:
    hits = 0
    total = 0
    for row in _load_jsonl("initiative_intake_evals.jsonl"):
        draft = deterministic_field_extraction(_input_text(row)).draft.model_dump(mode="json")
        for field, expected in _expected_output(row).items():
            total += 1
            if draft.get(field) == expected:
                hits += 1
    return EvalMetric("initiative_field_extraction", _ratio(hits, total))


def _score_kpi_suggestions() -> EvalMetric:
    hits = 0
    total = 0
    for row in _load_jsonl("kpi_suggestion_evals.jsonl"):
        suggested = {
            item.name
            for item in suggest_kpis(
                initiative_type=row["input"].get("initiative_type"),
                initiative_name=row["input"].get("initiative_name"),
                value_logic=row["input"].get("value_logic"),
            ).suggestions
        }
        expected = set(row["expected_names"])
        hits += len(expected & suggested)
        total += len(expected)
    return EvalMetric("kpi_suggestion", _ratio(hits, total))


def _score_risk_patterns() -> EvalMetric:
    hits = 0
    total = 0
    for row in _load_jsonl("risk_pattern_scan_evals.jsonl"):
        result = scan_risk_patterns(InitiativeDraft(**row["input"]))
        risks = result.risks
        checks = {
            "expected_types": {item.type for item in risks},
            "expected_descriptions": {item.description for item in risks},
            "expected_likelihoods": {item.likelihood for item in risks},
            "expected_impacts": {item.impact for item in risks},
        }
        for key, actual_values in checks.items():
            for expected in row.get(key, []):
                total += 1
                if expected in actual_values:
                    hits += 1
    return EvalMetric("risk_pattern_scan", _ratio(hits, total))


def _score_initiative_narrative_quality() -> EvalMetric:
    hits = 0
    total = 0
    for row in _load_jsonl("kpi_suggestion_evals.jsonl"):
        suggestions = suggest_kpis(
            initiative_type=row["input"].get("initiative_type"),
            initiative_name=row["input"].get("initiative_name"),
            value_logic=row["input"].get("value_logic"),
        ).suggestions
        for suggestion in suggestions[:3]:
            total += 1
            if _narrative_quality(suggestion.rationale) >= NARRATIVE_THRESHOLD:
                hits += 1
    for row in _load_jsonl("risk_pattern_scan_evals.jsonl"):
        risks = scan_risk_patterns(InitiativeDraft(**row["input"])).risks
        for risk in risks[:3]:
            total += 1
            if _narrative_quality(risk.mitigation) >= NARRATIVE_THRESHOLD:
                hits += 1
    return EvalMetric("initiative_narrative_quality", _ratio(hits, total))


def _score_meeting_notes_extraction() -> tuple[EvalMetric, EvalMetric]:
    hits = 0
    total = 0
    narrative_hits = 0
    narrative_total = 0
    attendees = _meeting_attendees()
    for row in _load_jsonl("meeting_notes_evals.jsonl"):
        expected_output = _expected_output(row)
        chunks = chunk_transcript(row["input"]["transcript"]).chunks
        action_texts = [item.description for item in extract_action_items(chunks, attendees).action_items]
        decision_texts = [item.text for item in extract_meeting_decisions(chunks, []).decisions]

        for expected in expected_output["action_items"]:
            total += 1
            if _contains_expected(action_texts, expected):
                hits += 1
        for expected in expected_output["decisions"]:
            total += 1
            if _contains_expected(decision_texts, expected):
                hits += 1

        for text in action_texts + decision_texts:
            narrative_total += 1
            if _narrative_quality(text) >= NARRATIVE_THRESHOLD:
                narrative_hits += 1

    return (
        EvalMetric("meeting_notes_extraction", _ratio(hits, total)),
        EvalMetric("meeting_notes_narrative_quality", _ratio(narrative_hits, narrative_total)),
    )


def _score_status_update_dataset_quality() -> EvalMetric:
    hits = 0
    total = 0
    for row in _load_jsonl("status_update_evals.jsonl"):
        expected = _expected_output(row)
        context = row["input"]["context"].lower()
        total += 1
        if row["input"]["rag_status"] == expected["rag_status"]:
            hits += 1
        for phrase in expected["must_include"]:
            total += 1
            if phrase.lower() in context:
                hits += 1
        total += 1
        if expected["narrative_quality_min"] >= NARRATIVE_THRESHOLD:
            hits += 1
    return EvalMetric("status_update_drafting_dataset_quality", _ratio(hits, total))


def _meeting_attendees() -> list[MeetingAttendeeContext]:
    names = [
        "Priya",
        "Aksha",
        "Vishwa",
        "Rupa",
        "Karya",
        "Netra",
        "Maya",
        "Sthira",
        "Ravi",
        "Chitra",
        "Prahari",
        "Dhruva",
        "Anika",
        "Vastu",
    ]
    return [
        MeetingAttendeeContext(user_id=name.lower(), display_name=name)
        for name in names
    ]


def _contains_expected(actual_values: list[str], expected: str) -> bool:
    expected_lower = expected.lower()
    return any(expected_lower in actual.lower() for actual in actual_values)


def _narrative_quality(text: str | None) -> float:
    if not text:
        return 0.0
    words = [word for word in text.split() if word.strip()]
    if len(words) < 2:
        return 0.3
    score = 0.8
    if len(words) >= 5:
        score += 0.1
    if any(char.isalpha() for char in text):
        score += 0.1
    if text.strip().endswith("."):
        score += 0.1
    return min(score, 1.0)


def _load_jsonl(filename: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (DATASET_DIR / filename).read_text().splitlines()
        if line.strip()
    ]


def _input_text(row: dict[str, Any]) -> str:
    if "text" in row:
        return str(row["text"])
    return str(row["input"]["text"])


def _expected_output(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("expected") or row["expected_output"]


def _ratio(hits: int, total: int) -> float:
    assert total > 0
    return round(hits / total, 4)


def _assert_metric(metric: EvalMetric, threshold: float) -> None:
    assert metric.score >= threshold, _format_failures([metric], threshold, "score")


def _format_failures(metrics: list[EvalMetric], threshold: float, field: str) -> str:
    lines = [
        f"{metric.name}: score={metric.score:.4f}, correction_rate={metric.correction_rate:.4f}"
        for metric in metrics
    ]
    return f"Eval {field} threshold {threshold:.2f} failed:\n" + "\n".join(lines)
