from pathlib import Path

from app.services.platform_guides import (
    GUIDE_SOURCES,
    _docs_root_candidates,
    get_platform_guide,
    list_platform_guides,
)


def test_docs_root_candidates_support_the_shallow_production_image_path() -> None:
    candidates = _docs_root_candidates(Path("/app/app/services/platform_guides.py"))

    assert Path("/app/docs") in candidates


def test_published_guide_manifest_contains_only_consolidated_guides() -> None:
    published_paths = {source.relative_path for source in GUIDE_SOURCES}
    canonical_paths = {
        "user-guides/transmuter-administration-guide.md",
        "user-guides/transmuter-user-operations-guide.md",
        "user-guides/transmuter-dashboard-reporting-guide.md",
    }

    assert published_paths == canonical_paths


def test_guide_renderer_formats_tables_and_rewrites_internal_guide_links() -> None:
    guide = get_platform_guide("administration")

    assert guide is not None
    assert guide["reviewed_at"] == "2026-08-08"
    assert "<table>" in guide["html"]
    assert 'href="/guides/user-operations"' in guide["html"]
    assert "<script" not in guide["html"].lower()


def test_dashboard_guide_explains_layouts_bankable_plan_and_locked_waterline() -> None:
    guide = get_platform_guide("dashboards-reporting")

    assert guide is not None
    assert "Customize layout" in guide["html"]
    assert "Benefit realization" in guide["html"]
    assert "Investment and payback" in guide["html"]
    assert "Value waterline" in guide["html"]
    assert "$1.8M benefits - $0.12M recurring costs = $1.68M" in guide["html"]
    assert "must not be counted as locked commitment" in guide["html"]


def test_published_guide_listing_has_unique_slugs_and_useful_metadata() -> None:
    items = list_platform_guides()

    assert len(items) == 3
    assert len({item["slug"] for item in items}) == len(items)
    assert all(item["title"] and item["summary"] and item["category"] for item in items)
    assert all(item["reviewed_at"] for item in items)
    assert {item["slug"] for item in items} == {
        "administration",
        "user-operations",
        "dashboards-reporting",
    }
    assert get_platform_guide("../README") is None
