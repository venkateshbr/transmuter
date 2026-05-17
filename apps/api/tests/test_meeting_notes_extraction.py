import json
from pathlib import Path

import pytest

from app.agents.meeting_notes_agent import (
    chunk_transcript,
    extract_action_items,
    extract_meeting_decisions,
)
from app.core.config import settings
from app.domain.meeting_notes import LinkedInitiativeContext, MeetingAttendeeContext


@pytest.fixture(autouse=True)
def disable_langfuse_for_deterministic_skill_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ai_enabled", False)


def test_transcript_chunking_splits_speaker_blocks() -> None:
    result = chunk_transcript(
        "Priya: Decision: approve AP automation pilot.\n\n"
        "Aksha: I will validate invoice baseline by 2026-06-14."
    )

    assert len(result.chunks) == 2
    assert result.chunks[0].speaker == "Priya"
    assert result.chunks[1].speaker == "Aksha"
    assert result.trace_id


def test_action_item_extraction_matches_attendee() -> None:
    chunks = chunk_transcript("Aksha: I will validate invoice baseline by 2026-06-14.").chunks
    result = extract_action_items(
        chunks,
        [MeetingAttendeeContext(user_id="user-aksha", display_name="Aksha Raman")],
    )

    assert len(result.action_items) == 1
    action = result.action_items[0]
    assert "validate invoice baseline" in action.description
    assert action.suggested_assignee_id == "user-aksha"
    assert action.due_date == "2026-06-14"
    assert action.priority == "medium"


def test_decision_extraction_returns_decisions_and_initiative_updates() -> None:
    chunks = chunk_transcript(
        "Vishwa: Decision: approve AP automation pilot.\n\n"
        "Priya: AP automation is blocked and should move red until ERP is ready."
    ).chunks
    result = extract_meeting_decisions(
        chunks,
        [LinkedInitiativeContext(id="init-1", name="AP automation", initiative_code="INIT-001")],
    )

    assert any("approve AP automation pilot" in item.text for item in result.decisions)
    assert len(result.initiative_updates) == 1
    assert result.initiative_updates[0].initiative_id == "init-1"
    assert result.initiative_updates[0].rag_status == "red"


def test_meeting_notes_eval_dataset_has_ten_samples() -> None:
    root = Path(__file__).resolve().parents[3]
    rows = [
        json.loads(line)
        for line in (root / "tests/evals/meeting_notes_extraction_evals.jsonl")
        .read_text()
        .splitlines()
        if line.strip()
    ]

    assert len(rows) == 10
    assert all(row["transcript"] for row in rows)
    assert all("expected_actions" in row for row in rows)
