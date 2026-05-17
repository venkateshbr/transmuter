"""Meeting notes extraction skills with deterministic fallback."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from uuid import uuid4

from langfuse.types import TraceContext

from app.agents.initiative_intake_agent import _get_langfuse
from app.core.config import settings
from app.domain.meeting_notes import (
    ActionItemExtractionResult,
    InitiativeStatusSignal,
    LinkedInitiativeContext,
    MeetingActionItemSuggestion,
    MeetingAttendeeContext,
    MeetingDecision,
    MeetingDecisionsExtractionResult,
    TranscriptChunk,
    TranscriptChunkingResult,
)


def chunk_transcript(transcript: str) -> TranscriptChunkingResult:
    """Split transcript into reviewable speaker/paragraph chunks."""
    trace_id = _trace_id("transcript-chunking")
    blocks = [block.strip() for block in re.split(r"\n\s*\n", transcript.strip()) if block.strip()]
    chunks: list[TranscriptChunk] = []
    for block in blocks:
        speaker = None
        text = block
        match = re.match(r"^([A-Z][A-Za-z .'-]{1,80}):\s*(.+)$", block, flags=re.S)
        if match:
            speaker = match.group(1).strip()
            text = match.group(2).strip()
        sentences = _split_long_text(text)
        for sentence in sentences:
            chunks.append(
                TranscriptChunk(
                    index=len(chunks),
                    speaker=speaker,
                    text=sentence,
                    topic_hint=_topic_hint(sentence),
                )
            )
    if not chunks and transcript.strip():
        chunks.append(TranscriptChunk(index=0, text=transcript.strip()))
    result = TranscriptChunkingResult(
        trace_id=trace_id,
        chunks=chunks,
    )
    return _trace_skill(
        name="transcript_chunking",
        trace_id=trace_id,
        skill_input={"transcript_chars": len(transcript)},
        result=result,
    )


def extract_action_items(
    chunks: list[TranscriptChunk],
    attendees: list[MeetingAttendeeContext],
) -> ActionItemExtractionResult:
    """Extract action items and fuzzy-match assignees against attendees."""
    trace_id = _trace_id("action-item-extraction")
    action_items: list[MeetingActionItemSuggestion] = []
    patterns = (
        r"(?:action|todo|to do|next step)[:\s-]+(?P<task>.+)",
        r"(?:I|we)\s+(?:will|should|need to|needs to)\s+(?P<task>.+)",
        r"(?P<assignee>[A-Z][A-Za-z .'-]{1,60})\s+(?:will|to|should|needs to|owns)\s+(?P<task>.+)",
        r"(?:please|can you)\s+(?P<task>.+)",
    )
    for chunk in chunks:
        text = _clean(chunk.text)
        lowered = text.lower()
        if not any(word in lowered for word in ("action", "todo", "to do", "next step", "will", "should", "owns", "please")):
            continue
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if not match:
                continue
            task = _trim_task(match.groupdict().get("task") or text)
            if not task:
                continue
            assignee_name = match.groupdict().get("assignee") or chunk.speaker
            assignee = _match_attendee(assignee_name, attendees)
            action_items.append(
                MeetingActionItemSuggestion(
                    description=task,
                    suggested_assignee_id=assignee.user_id if assignee else None,
                    suggested_assignee_name=assignee.display_name if assignee else assignee_name,
                    due_date=_due_date_hint(text),
                    priority=_priority_hint(text),
                    rationale="Extracted from an explicit action-oriented statement.",
                )
            )
            break
    result = ActionItemExtractionResult(
        trace_id=trace_id,
        action_items=_dedupe_actions(action_items),
    )
    return _trace_skill(
        name="action_item_extraction",
        trace_id=trace_id,
        skill_input={"chunks": len(chunks), "attendees": len(attendees)},
        result=result,
    )


def extract_meeting_decisions(
    chunks: list[TranscriptChunk],
    linked_initiatives: list[LinkedInitiativeContext],
) -> MeetingDecisionsExtractionResult:
    """Extract decisions and initiative status signals from transcript chunks."""
    trace_id = _trace_id("meeting-decisions-extraction")
    decisions: list[MeetingDecision] = []
    updates: list[InitiativeStatusSignal] = []
    for chunk in chunks:
        text = _clean(chunk.text)
        lowered = text.lower()
        if any(phrase in lowered for phrase in ("decided", "decision", "agreed", "approved", "sign off", "signed off")):
            decisions.append(
                MeetingDecision(
                    text=_trim_decision(text),
                    rationale="Detected from explicit decision language.",
                )
            )
        if any(word in lowered for word in ("status", "blocked", "at risk", "delayed", "green", "amber", "red", "complete")):
            initiative = _match_initiative(text, linked_initiatives)
            if initiative or linked_initiatives:
                updates.append(
                    InitiativeStatusSignal(
                        initiative_id=initiative.id if initiative else linked_initiatives[0].id,
                        initiative_name=initiative.name if initiative else linked_initiatives[0].name,
                        summary=text[:2000],
                        rag_status=_rag_hint(lowered),
                    )
                )
    result = MeetingDecisionsExtractionResult(
        trace_id=trace_id,
        decisions=_dedupe_decisions(decisions),
        initiative_updates=_dedupe_updates(updates),
    )
    return _trace_skill(
        name="meeting_decisions_extraction",
        trace_id=trace_id,
        skill_input={"chunks": len(chunks), "linked_initiatives": len(linked_initiatives)},
        result=result,
    )


def _trace_id(skill: str) -> str:
    langfuse = _get_langfuse()
    if langfuse:
        return langfuse.create_trace_id(seed=f"meeting-notes-{skill}-{uuid4()}")
    return f"deterministic-meeting-notes-{skill}-{uuid4()}"


def _trace_skill(
    *,
    name: str,
    trace_id: str,
    skill_input: dict[str, int],
    result: TranscriptChunkingResult | ActionItemExtractionResult | MeetingDecisionsExtractionResult,
) -> TranscriptChunkingResult | ActionItemExtractionResult | MeetingDecisionsExtractionResult:
    langfuse = _get_langfuse()
    if not langfuse:
        return result
    try:
        with langfuse.start_as_current_observation(
            name=name,
            as_type="agent",
            trace_context=TraceContext(trace_id=trace_id),
            input=skill_input,
            metadata={"source": "meeting_notes_extraction"},
            model=settings.default_model,
        ):
            result.trace_url = langfuse.get_trace_url(trace_id=trace_id)
            langfuse.update_current_span(output=result.model_dump(mode="json"))
        langfuse.flush()
    except Exception:
        result.trace_url = None
    return result


def _split_long_text(text: str) -> list[str]:
    if len(text) <= 900:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) > 900 and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current.strip())
    return chunks


def _topic_hint(text: str) -> str | None:
    lowered = text.lower()
    if "risk" in lowered or "block" in lowered:
        return "risk"
    if "kpi" in lowered or "metric" in lowered:
        return "kpi"
    if "cost" in lowered or "saving" in lowered or "value" in lowered:
        return "value"
    if "action" in lowered or "next step" in lowered:
        return "action"
    return None


def _clean(text: str) -> str:
    return " ".join(text.split())


def _trim_task(text: str) -> str:
    text = re.split(r"\b(?:by|due)\b", text, maxsplit=1, flags=re.I)[0]
    return text.strip(" .:-")


def _trim_decision(text: str) -> str:
    return re.sub(r"^(decision|decided|agreed)[:\s-]+", "", text, flags=re.I).strip(" .")


def _due_date_hint(text: str) -> str | None:
    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if iso:
        return iso.group(1)
    lowered = text.lower()
    if "next week" in lowered:
        return "next week"
    if "friday" in lowered:
        return "Friday"
    if "month end" in lowered or "end of month" in lowered:
        return "month end"
    return None


def _priority_hint(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("urgent", "critical", "high priority", "blocker")):
        return "high"
    if any(word in lowered for word in ("low priority", "nice to have")):
        return "low"
    return "medium"


def _match_attendee(
    name: str | None,
    attendees: list[MeetingAttendeeContext],
) -> MeetingAttendeeContext | None:
    if not name:
        return None
    needle = name.lower().strip()
    best: tuple[float, MeetingAttendeeContext | None] = (0, None)
    for attendee in attendees:
        candidate = (attendee.display_name or "").lower().strip()
        if not candidate:
            continue
        score = SequenceMatcher(None, needle, candidate).ratio()
        if needle in candidate or candidate in needle:
            score = max(score, 0.92)
        if score > best[0]:
            best = (score, attendee)
    return best[1] if best[0] >= 0.72 else None


def _match_initiative(
    text: str,
    initiatives: list[LinkedInitiativeContext],
) -> LinkedInitiativeContext | None:
    lowered = text.lower()
    for initiative in initiatives:
        name = initiative.name.lower()
        code = (initiative.initiative_code or "").lower()
        if name in lowered or (code and code in lowered):
            return initiative
    return None


def _rag_hint(lowered: str) -> str:
    if "amber" in lowered or "watch" in lowered:
        return "amber"
    if any(word in lowered for word in ("red", "blocked", "critical", "delayed", "at risk")):
        return "red"
    return "green"


def _dedupe_actions(items: list[MeetingActionItemSuggestion]) -> list[MeetingActionItemSuggestion]:
    seen: set[str] = set()
    result: list[MeetingActionItemSuggestion] = []
    for item in items:
        key = item.description.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result[:12]


def _dedupe_decisions(items: list[MeetingDecision]) -> list[MeetingDecision]:
    seen: set[str] = set()
    result: list[MeetingDecision] = []
    for item in items:
        key = item.text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result[:12]


def _dedupe_updates(items: list[InitiativeStatusSignal]) -> list[InitiativeStatusSignal]:
    seen: set[tuple[str | None, str]] = set()
    result: list[InitiativeStatusSignal] = []
    for item in items:
        key = (item.initiative_id, item.summary.lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result[:12]
