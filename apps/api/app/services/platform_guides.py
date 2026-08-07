from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt


@dataclass(frozen=True)
class GuideSource:
    slug: str
    category: str
    relative_path: str


GUIDE_SOURCES = (
    GuideSource("tenant-onboarding", "Start here", "team/TENANT_ONBOARDING_USER_GUIDE.md"),
    GuideSource(
        "acme-detailed-demo",
        "Demo guides",
        "user-guides/acme-transformation-office-detailed-setup-and-demo-guide.md",
    ),
    GuideSource("acme-ui-setup", "Demo guides", "user-guides/acme-demo-tenant-ui-setup-guide.md"),
    GuideSource(
        "acme-management-runbook",
        "Demo guides",
        "user-guides/acme-transformation-office-management-runbook.md",
    ),
    GuideSource(
        "acme-value-demonstration",
        "Demo guides",
        "user-guides/acme-transformation-value-demonstration-guide.md",
    ),
    GuideSource(
        "acme-dashboards-reporting",
        "Financial guides",
        "user-guides/acme-dashboard-and-reporting-user-guide.md",
    ),
    GuideSource(
        "admin-financial-configuration",
        "Financial guides",
        "user-guides/admin-financial-configuration-user-guide.md",
    ),
    GuideSource(
        "financial-engine-walkthrough",
        "Financial guides",
        "user-guides/financial-engine-end-to-end-walkthrough.md",
    ),
    GuideSource(
        "automation-financial-scenario",
        "Financial guides",
        "user-guides/automation-productivity-financial-scenario-walkthrough.md",
    ),
    GuideSource(
        "ishirock-ui-setup", "Ishirock guides", "user-guides/ishirock-demo-tenant-ui-setup-guide.md"
    ),
    GuideSource(
        "ishirock-detailed-demo",
        "Ishirock guides",
        "user-guides/ishirock-transformation-office-detailed-setup-and-demo-guide.md",
    ),
    GuideSource(
        "ishirock-value-demonstration",
        "Ishirock guides",
        "user-guides/ishirock-transformation-value-demonstration-guide.md",
    ),
    GuideSource(
        "ishirock-workbook-readiness",
        "Ishirock guides",
        "user-guides/ishirock-ui-readiness-from-workbook-guide.md",
    ),
    GuideSource(
        "benefit-ledger-remediation",
        "Operations",
        "user-guides/acme-benefit-ledger-production-remediation-guide.md",
    ),
    GuideSource(
        "platform-admin-validation-runbook",
        "Operations",
        "user-guides/platform-admin-user-guide-validation-runbook.md",
    ),
    GuideSource(
        "platform-improvement-opportunities",
        "Reference",
        "user-guides/acme-transformation-platform-improvement-opportunities.md",
    ),
)

_SOURCE_BY_SLUG = {source.slug: source for source in GUIDE_SOURCES}
_SLUG_BY_FILENAME = {Path(source.relative_path).name: source.slug for source in GUIDE_SOURCES}
_MARKDOWN = MarkdownIt("commonmark", {"html": False, "linkify": False}).enable("table")


def _docs_root() -> Path:
    service_path = Path(__file__).resolve()
    for candidate in _docs_root_candidates(service_path):
        if candidate.joinpath("user-guides").is_dir():
            return candidate
    raise RuntimeError("Published user-guide sources are not available.")


def _docs_root_candidates(service_path: Path) -> tuple[Path, ...]:
    return tuple(parent / "docs" for parent in service_path.parents)


def _read_source(source: GuideSource) -> str:
    root = _docs_root().resolve()
    path = root.joinpath(source.relative_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise RuntimeError(f"Published guide source is missing: {source.slug}")
    return path.read_text(encoding="utf-8")


def _title(markdown: str) -> str:
    match = re.search(r"^#\s+(.+)$", markdown, flags=re.MULTILINE)
    return match.group(1).strip() if match else "Untitled guide"


def _summary(markdown: str) -> str:
    without_title = re.sub(r"^#\s+.+$", "", markdown, count=1, flags=re.MULTILINE).strip()
    paragraphs = re.split(r"\n\s*\n", without_title)
    for paragraph in paragraphs:
        normalized = " ".join(line.strip() for line in paragraph.splitlines()).strip()
        if not normalized or normalized.startswith(
            ("Last updated:", "Last reviewed:", "---", "- ", "|")
        ):
            continue
        return re.sub(r"[`*_\[\]]", "", normalized)[:320]
    return "Published Transmuter operating guidance."


def _reviewed_at(markdown: str) -> str | None:
    match = re.search(
        r"^(?:Last (?:updated|reviewed)|Launch-readiness note)\s*(?:\([^)]*\))?\s*:\s*`?([^`\n]+)`?",
        markdown,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _rewrite_guide_links(html: str) -> str:
    def replace(match: re.Match[str]) -> str:
        filename = Path(match.group("href").split("#", 1)[0]).name
        fragment = f"#{match.group('href').split('#', 1)[1]}" if "#" in match.group("href") else ""
        slug = _SLUG_BY_FILENAME.get(filename)
        return f'href="/platform/guides/{slug}{fragment}"' if slug else match.group(0)

    return re.sub(r'href="(?P<href>[^"]+\.md(?:#[^"]*)?)"', replace, html)


def list_platform_guides() -> list[dict[str, Any]]:
    items = []
    for source in GUIDE_SOURCES:
        markdown = _read_source(source)
        items.append(
            {
                "slug": source.slug,
                "category": source.category,
                "title": _title(markdown),
                "summary": _summary(markdown),
                "reviewed_at": _reviewed_at(markdown),
            }
        )
    return items


def get_platform_guide(slug: str) -> dict[str, Any] | None:
    source = _SOURCE_BY_SLUG.get(slug)
    if source is None:
        return None
    markdown = _read_source(source)
    return {
        "slug": source.slug,
        "category": source.category,
        "title": _title(markdown),
        "summary": _summary(markdown),
        "reviewed_at": _reviewed_at(markdown),
        "html": _rewrite_guide_links(_MARKDOWN.render(markdown)),
    }
