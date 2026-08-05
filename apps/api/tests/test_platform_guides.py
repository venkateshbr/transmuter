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


def test_published_guide_manifest_covers_all_canonical_user_guides() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    published_paths = {source.relative_path for source in GUIDE_SOURCES}
    canonical_paths = {
        f"user-guides/{path.name}"
        for path in repo_root.joinpath("docs/user-guides").glob("*.md")
        if path.name != "README.md"
    }
    canonical_paths.add("team/TENANT_ONBOARDING_USER_GUIDE.md")

    assert published_paths == canonical_paths


def test_guide_renderer_formats_tables_and_rewrites_internal_guide_links() -> None:
    guide = get_platform_guide("tenant-onboarding")

    assert guide is not None
    assert guide["reviewed_at"] == "2026-08-05"
    assert "<table>" in guide["html"]
    assert 'href="/platform/guides/acme-ui-setup"' in guide["html"]
    assert "<script" not in guide["html"].lower()


def test_published_guide_listing_has_unique_slugs_and_useful_metadata() -> None:
    items = list_platform_guides()

    assert len(items) == 15
    assert len({item["slug"] for item in items}) == len(items)
    assert all(item["title"] and item["summary"] and item["category"] for item in items)
    assert all(item["reviewed_at"] == "2026-08-05" for item in items)
    assert any(item["slug"] == "platform-admin-validation-runbook" for item in items)
    assert get_platform_guide("../README") is None
