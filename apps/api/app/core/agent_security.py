from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from pydantic import ValidationInfo

_PROMPT_INJECTION_PATTERNS = (
    re.compile(r"\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b", re.IGNORECASE),
    re.compile(r"\b(system|developer)\s+(prompt|message|instructions?)\b", re.IGNORECASE),
    re.compile(
        r"\b(reveal|print|show|dump|exfiltrate)\s+(the\s+)?(prompt|secrets?|keys?)\b", re.IGNORECASE
    ),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
)
_PII_OR_SECRET_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(
        r"\b(api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password)\s*[:=]", re.IGNORECASE
    ),
)


def validate_agent_text(value: str, field_name: str = "text") -> str:
    """Reject high-risk prompt-injection and PII before text reaches agent tools."""
    text = value.strip()
    if len(text) > 4000:
        raise ValueError(f"{field_name} must be 4000 characters or fewer")
    if any(pattern.search(text) for pattern in _PROMPT_INJECTION_PATTERNS):
        raise ValueError(f"{field_name} contains prompt-injection language")
    if any(pattern.search(text) for pattern in _PII_OR_SECRET_PATTERNS):
        raise ValueError(f"{field_name} contains PII or secret material")
    return value


def validate_agent_text_list(values: Iterable[str], field_name: str = "text") -> list[str]:
    return [validate_agent_text(value, field_name) for value in values]


def validate_agent_model_strings(value: Any, info: ValidationInfo | None = None) -> Any:
    field_name = info.field_name if info else "text"
    if isinstance(value, str):
        validate_agent_text(value, field_name)
    elif isinstance(value, (list, tuple)):
        for item in value:
            validate_agent_model_strings(item, info)
    elif isinstance(value, dict):
        for item in value.values():
            validate_agent_model_strings(item, info)
    return value
