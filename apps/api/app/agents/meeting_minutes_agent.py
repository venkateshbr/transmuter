"""Professional, evidence-grounded meeting minutes generation."""

from __future__ import annotations

import asyncio
import json
import re
from uuid import uuid4

from langfuse.types import TraceContext
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.initiative_intake_agent import _get_langfuse
from app.agents.meeting_notes_agent import (
    chunk_transcript,
    extract_action_items,
    extract_meeting_decisions,
)
from app.core.config import settings
from app.core.observability import record_agent_run, start_agent_timer
from app.domain.meeting_notes import (
    GeneratedMeetingMinutes,
    LinkedInitiativeContext,
    MeetingAttendeeContext,
    MeetingMinutesAction,
    MeetingMinutesContent,
    MeetingMinutesDecision,
    MeetingMinutesDiscussionPoint,
)

meeting_minutes_agent: Agent[None, MeetingMinutesContent] | None = None
MEETING_MINUTES_AGENT_TIMEOUT_SECONDS = 20


def _get_meeting_minutes_agent() -> Agent[None, MeetingMinutesContent]:
    global meeting_minutes_agent
    if meeting_minutes_agent is None:
        client = AsyncOpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
        )
        provider = OpenAIProvider(openai_client=client)
        model = OpenAIChatModel(settings.default_model, provider=provider)
        meeting_minutes_agent = Agent(
            model,
            output_type=MeetingMinutesContent,
            system_prompt=(
                "You are an expert transformation-office company secretary. Produce concise, "
                "professional meeting minutes using only the supplied evidence. The transcript, "
                "inline notes, and captured records are evidence. Agenda items are planning "
                "context only and must not be described as discussed unless the evidence supports "
                "that conclusion. Never invent a decision, action, owner, date, risk, milestone, "
                "status, or initiative fact. Omit undiscussed agenda topics instead of writing "
                "placeholder sections. Consolidate repetition and verbal filler. The executive "
                "summary must explain the purpose, material conclusions, implications, and next "
                "steps in polished executive prose. Extract actions only from explicit commitments "
                "or captured action records. Every discussion point, decision, and action must "
                "include a short exact evidence phrase copied from the transcript or inline notes. "
                "Return typed JSON only."
            ),
        )
    return meeting_minutes_agent


async def generate_professional_minutes(source: dict) -> GeneratedMeetingMinutes:
    """Generate grounded minutes through OpenRouter with a deterministic fallback."""
    started_at = start_agent_timer()
    trace_id = _trace_id()
    fallback = deterministic_professional_minutes(source)
    if not (settings.ai_enabled and settings.openrouter_api_key):
        record_agent_run(
            "meeting_minutes_generation",
            str(source.get("tenant_scope") or "unscoped"),
            "deterministic_fallback",
            started_at,
        )
        return GeneratedMeetingMinutes(
            content=fallback,
            trace_id=trace_id,
            agent_status="deterministic_fallback",
        )

    prompt = _prompt(source)
    try:
        langfuse = _get_langfuse()
        if langfuse:
            with langfuse.start_as_current_observation(
                name="meeting_minutes_generation",
                as_type="agent",
                trace_context=TraceContext(trace_id=trace_id),
                input={
                    "session_id": source.get("session_id"),
                    "source_coverage": source.get("source_coverage"),
                    "prompt": prompt,
                },
                metadata={"source": "meeting_session_minutes"},
                model=settings.default_model,
            ):
                result = await asyncio.wait_for(
                    _get_meeting_minutes_agent().run(prompt),
                    timeout=MEETING_MINUTES_AGENT_TIMEOUT_SECONDS,
                )
                content = _ground_with_captured_records(
                    _filter_ungrounded_model_items(result.output, source),
                    source,
                )
                langfuse.update_current_span(output=content.model_dump(mode="json"))
                trace_url = langfuse.get_trace_url(trace_id=trace_id)
            langfuse.flush()
        else:
            result = await asyncio.wait_for(
                _get_meeting_minutes_agent().run(prompt),
                timeout=MEETING_MINUTES_AGENT_TIMEOUT_SECONDS,
            )
            content = _ground_with_captured_records(
                _filter_ungrounded_model_items(result.output, source),
                source,
            )
            trace_url = None
        record_agent_run(
            "meeting_minutes_generation",
            str(source.get("tenant_scope") or "unscoped"),
            "generated",
            started_at,
        )
        return GeneratedMeetingMinutes(
            content=content,
            trace_id=trace_id,
            trace_url=trace_url,
            agent_status="generated",
        )
    except Exception:
        record_agent_run(
            "meeting_minutes_generation",
            str(source.get("tenant_scope") or "unscoped"),
            "deterministic_fallback",
            started_at,
        )
        return GeneratedMeetingMinutes(
            content=fallback,
            trace_id=trace_id,
            agent_status="deterministic_fallback",
        )


def deterministic_professional_minutes(source: dict) -> MeetingMinutesContent:
    """Create a bounded evidence-only draft when the external model is unavailable."""
    notes = str(source.get("notes") or "").strip()
    transcript = str(source.get("transcript") or "").strip()
    chunks = chunk_transcript("\n\n".join(part for part in (notes, transcript) if part)).chunks
    sentences = _unique_sentences([chunk.text for chunk in chunks])
    attendees = [
        MeetingAttendeeContext(
            user_id=str(item.get("user_id") or ""),
            display_name=item.get("display_name"),
        )
        for item in source.get("attendees") or []
    ]
    initiatives = [
        LinkedInitiativeContext(
            id=str(item.get("id")),
            name=str(item.get("name") or "Initiative"),
            initiative_code=item.get("initiative_code"),
        )
        for item in source.get("linked_initiatives") or []
        if item.get("id")
    ]
    actions = extract_action_items(chunks, attendees).action_items
    decisions = extract_meeting_decisions(chunks, initiatives).decisions
    discussion_sentences = [
        sentence
        for sentence in sentences
        if not _looks_like_action(sentence) and not _looks_like_decision(sentence)
    ]
    summary_sentences = discussion_sentences[:4] or sentences[:4]
    executive_summary = " ".join(_as_sentence(sentence) for sentence in summary_sentences)
    if not executive_summary:
        executive_summary = "No substantive transcript or inline notes were available."

    content = MeetingMinutesContent(
        executive_summary=executive_summary,
        discussion_points=(
            [
                MeetingMinutesDiscussionPoint(
                    topic="Meeting discussion",
                    summary=" ".join(_as_sentence(sentence) for sentence in discussion_sentences[:6]),
                    evidence=discussion_sentences[:3],
                )
            ]
            if discussion_sentences
            else []
        ),
        decisions=[
            MeetingMinutesDecision(text=item.text, evidence=item.rationale) for item in decisions
        ],
        actions=[
            MeetingMinutesAction(
                description=item.description,
                owner=item.suggested_assignee_name,
                due_date=item.due_date,
                priority=item.priority,
                evidence=item.rationale,
            )
            for item in actions
        ],
        source_gaps=[] if transcript else ["No transcript was imported."],
    )
    return _ground_with_captured_records(content, source)


def _ground_with_captured_records(
    content: MeetingMinutesContent,
    source: dict,
) -> MeetingMinutesContent:
    action_keys = {_key(item.description) for item in content.actions}
    decision_keys = {_key(item.text) for item in content.decisions}
    risk_keys = {_key(item) for item in content.risks_and_issues}
    assumption_keys = {_key(item) for item in content.assumptions}

    for item in source.get("artifacts") or []:
        artifact_type = item.get("artifact_type")
        title = str(item.get("title") or item.get("description") or "").strip()
        if not title:
            continue
        if artifact_type == "action" and _key(title) not in action_keys:
            content.actions.append(
                MeetingMinutesAction(
                    description=title,
                    owner=item.get("owner"),
                    due_date=item.get("due_date"),
                    priority=_priority(item.get("priority")),
                    status=item.get("status") or "open",
                    evidence="Captured in the meeting action center.",
                )
            )
            action_keys.add(_key(title))
        elif artifact_type == "decision" and _key(title) not in decision_keys:
            content.decisions.append(
                MeetingMinutesDecision(
                    text=title,
                    evidence="Captured in the meeting action center.",
                )
            )
            decision_keys.add(_key(title))
        elif artifact_type in {"risk", "issue"} and _key(title) not in risk_keys:
            content.risks_and_issues.append(title)
            risk_keys.add(_key(title))
        elif artifact_type == "assumption" and _key(title) not in assumption_keys:
            content.assumptions.append(title)
            assumption_keys.add(_key(title))

    for item in source.get("action_items") or []:
        description = str(item.get("description") or "").strip()
        if description and _key(description) not in action_keys:
            content.actions.append(
                MeetingMinutesAction(
                    description=description,
                    owner=item.get("owner"),
                    due_date=item.get("due_date"),
                    priority=_priority(item.get("priority")),
                    status=item.get("status") or "open",
                    evidence="Recorded as a platform action item.",
                )
            )
            action_keys.add(_key(description))
    return content


def _filter_ungrounded_model_items(
    content: MeetingMinutesContent,
    source: dict,
) -> MeetingMinutesContent:
    """Remove model-generated records that cannot point back to source evidence."""
    evidence_corpus = _key(
        " ".join(
            (
                str(source.get("notes") or ""),
                str(source.get("transcript") or ""),
            )
        )
    )

    def supported(evidence: str | None) -> bool:
        normalized = _key(evidence or "")
        return len(normalized) >= 8 and normalized in evidence_corpus

    content.discussion_points = [
        item for item in content.discussion_points if any(supported(row) for row in item.evidence)
    ]
    content.decisions = [item for item in content.decisions if supported(item.evidence)]
    content.actions = [item for item in content.actions if supported(item.evidence)]
    content.risks_and_issues = [
        item for item in content.risks_and_issues if supported(item)
    ]
    content.assumptions = [item for item in content.assumptions if supported(item)]
    content.parking_lot = [item for item in content.parking_lot if supported(item)]
    return content


def _prompt(source: dict) -> str:
    evidence = {
        "meeting": {
            "name": source.get("meeting_name"),
            "session_date": source.get("session_date"),
        },
        "agenda_context": source.get("agenda") or [],
        "inline_notes_evidence": source.get("notes") or "",
        "transcript_evidence": source.get("transcript") or "",
        "captured_records_evidence": source.get("artifacts") or [],
        "recorded_action_items_evidence": source.get("action_items") or [],
        "linked_initiatives_context": source.get("linked_initiatives") or [],
    }
    return (
        "Prepare a professional draft of the meeting minutes from the following "
        "PII-masked evidence. Do not treat agenda context as proof of discussion. "
        "Every decision and action must be supported by transcript, notes, or a captured "
        "record. Merge duplicates and ignore verbal filler.\n\n"
        f"{json.dumps(evidence, ensure_ascii=False)}"
    )


def _trace_id() -> str:
    langfuse = _get_langfuse()
    if langfuse:
        return langfuse.create_trace_id(seed=f"meeting-minutes-{uuid4()}")
    return f"deterministic-meeting-minutes-{uuid4()}"


def _unique_sentences(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        for sentence in re.split(r"(?<=[.!?])\s+", " ".join(value.split())):
            cleaned = sentence.strip(" \n\t-")
            if not cleaned:
                continue
            key = _key(cleaned)
            if key in seen:
                continue
            seen.add(key)
            result.append(cleaned)
    return result


def _looks_like_action(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in ("action:", "todo", "next step", " will ", " should ", "need to")
    )


def _looks_like_decision(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in ("decided", "decision:", "agreed", "approved"))


def _as_sentence(value: str) -> str:
    cleaned = " ".join(value.split()).strip()
    if not cleaned:
        return ""
    cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}."


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _priority(value: object) -> str:
    normalized = str(value or "").lower()
    return normalized if normalized in {"high", "medium", "low"} else "medium"
