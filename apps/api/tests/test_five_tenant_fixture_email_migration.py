from __future__ import annotations

import inspect
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import EmailStr, TypeAdapter

from scripts import migrate_five_tenant_fixture_email_domains as migration
from scripts.multi_tenant_transformation_profiles import COMPANY_PROFILES
from scripts.seed_five_tenant_transformation_program import FIXTURE_OWNER


class _Result:
    def __init__(self, data: object = None, *, count: int | None = None) -> None:
        self.data = data
        self.count = count


class _Query:
    def __init__(self, client: _Client, table: str) -> None:
        self.client = client
        self.table = table
        self.filters: list[tuple[str, object]] = []
        self.single = False
        self.count = False
        self.update_payload: dict[str, object] | None = None

    def select(self, *_columns: str, count: str | None = None) -> _Query:
        self.count = count == "exact"
        return self

    def eq(self, key: str, value: object) -> _Query:
        self.filters.append((key, value))
        return self

    def ilike(self, key: str, value: object) -> _Query:
        self.filters.append((f"ilike:{key}", value))
        return self

    def maybe_single(self) -> _Query:
        self.single = True
        return self

    def limit(self, _value: int) -> _Query:
        return self

    def update(self, payload: dict[str, object]) -> _Query:
        self.update_payload = payload
        return self

    def execute(self) -> _Result:
        rows = self.client.tables[self.table]

        def matches(row: dict[str, object]) -> bool:
            for key, value in self.filters:
                if key.startswith("ilike:"):
                    column = key.removeprefix("ilike:")
                    if str(row.get(column) or "").lower() != str(value).lower():
                        return False
                elif row.get(key) != value:
                    return False
            return True

        selected = [row for row in rows if matches(row)]
        if self.update_payload is not None:
            subject = str(selected[0]["id"]) if selected else ""
            target = str(self.update_payload.get("email") or "")
            if (
                subject == self.client.fail_platform_subject
                and ".qa.transmuter-dev.ishirock.tech" in target
            ):
                raise RuntimeError("injected platform failure")
            for row in selected:
                row.update(self.update_payload)
            self.client.events.append(
                {
                    "kind": "platform",
                    "subject": subject,
                    "payload": dict(self.update_payload),
                    "filters": tuple(self.filters),
                }
            )
            if (
                subject == self.client.mutate_unrelated_after_platform_subject
                and ".qa.transmuter-dev.ishirock.tech" in target
                and self.client.unrelated_subject is not None
            ):
                unrelated = self.client.auth_users[self.client.unrelated_subject]
                unrelated.app_metadata = {
                    **unrelated.app_metadata,
                    "concurrent_change": True,
                }
            return _Result([dict(row) for row in selected])
        if self.count:
            return _Result(selected[:1], count=len(selected))
        if self.single:
            return _Result(dict(selected[0]) if selected else None)
        return _Result([dict(row) for row in selected])


class _AuthAdmin:
    def __init__(self, client: _Client) -> None:
        self.client = client

    def list_users(self, **_kwargs: object) -> list[SimpleNamespace]:
        self.client.list_users_calls += 1
        if self.client.list_users_calls == self.client.fail_list_users_call:
            raise RuntimeError("injected postflight failure")
        return list(self.client.auth_users.values())

    def get_user_by_id(self, subject_id: str) -> SimpleNamespace:
        return SimpleNamespace(user=self.client.auth_users.get(subject_id))

    def update_user_by_id(self, subject_id: str, payload: dict[str, object]) -> SimpleNamespace:
        self.client.events.append(
            {
                "kind": "auth",
                "subject": subject_id,
                "payload": dict(payload),
            }
        )
        user = self.client.auth_users[subject_id]
        user.email = str(payload["email"])
        return SimpleNamespace(user=user)


class _Client:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, object]]] = {
            "organizations": [],
            "users": [],
            "user_invites": [],
            "integration_connections": [],
            "integration_oauth_states": [],
        }
        self.auth_users: dict[str, SimpleNamespace] = {}
        self.events: list[dict[str, object]] = []
        self.fail_platform_subject: str | None = None
        self.fail_list_users_call: int | None = None
        self.list_users_calls = 0
        self.mutate_unrelated_after_platform_subject: str | None = None
        self.unrelated_subject: str | None = None
        self.auth = SimpleNamespace(admin=_AuthAdmin(self))

    def table(self, name: str) -> _Query:
        return _Query(self, name)


def _client_with_fixture(
    *, complete: set[tuple[str, str]] | None = None
) -> tuple[_Client, dict[tuple[str, str], str]]:
    client = _Client()
    complete = complete or set()
    subjects: dict[tuple[str, str], str] = {}
    for tenant_index, profile in enumerate(COMPANY_PROFILES, start=1):
        tenant_id = f"tenant-{tenant_index}"
        client.tables["organizations"].append(
            {
                "id": tenant_id,
                "slug": profile.slug,
                "settings": {"qa_fixture": {"owner": FIXTURE_OWNER, "slug": profile.slug}},
            }
        )
        for identity_index, (old_email, mapping) in enumerate(
            migration.expected_email_mappings(profile).items(), start=1
        ):
            new_email, role, identity_key = mapping
            subject_id = f"subject-{tenant_index}-{identity_index}"
            email = new_email if (profile.slug, identity_key) in complete else old_email
            app_metadata = {
                "transmuter_authorization_transmuter_dev": {
                    "tenant_id": tenant_id,
                    "role": role,
                },
                "transmuter_fixture": {
                    "owner": FIXTURE_OWNER,
                    "tenant_id": tenant_id,
                },
                "preserved": {"identity": identity_index},
            }
            user_metadata = {"display_name": f"Fixture {tenant_index}-{identity_index}"}
            client.tables["users"].append(
                {
                    "id": subject_id,
                    "tenant_id": tenant_id,
                    "email": email,
                    "role": role,
                }
            )
            client.auth_users[subject_id] = SimpleNamespace(
                id=subject_id,
                email=email,
                app_metadata=app_metadata,
                user_metadata=user_metadata,
                role="authenticated",
                is_super_admin=False,
                password_hash=f"unchanged-{tenant_index}-{identity_index}",
            )
            subjects[(profile.slug, identity_key)] = subject_id
    return client, subjects


def test_mapping_is_fixed_to_five_profiles_and_fifty_valid_destinations() -> None:
    assert migration.LEGACY_DOMAINS_BY_SLUG == {
        "qa-e2e-20260712-acme-global-manufacturing": ("acme-global-manufacturing.transmuter.test"),
        "qa-e2e-20260712-northstar-retail-group": ("northstar-retail-group.transmuter.test"),
        "qa-e2e-20260712-meridian-commercial-bank": ("meridian-commercial-bank.transmuter.test"),
        "qa-e2e-20260712-solstice-health-network": ("solstice-health-network.transmuter.test"),
        "qa-e2e-20260712-horizon-energy-utilities": ("horizon-energy-utilities.transmuter.test"),
    }
    assert [(profile.slug, profile.email_domain) for profile in COMPANY_PROFILES] == [
        (
            "qa-e2e-20260712-acme-global-manufacturing",
            "acme-global-manufacturing.qa.transmuter-dev.ishirock.tech",
        ),
        (
            "qa-e2e-20260712-northstar-retail-group",
            "northstar-retail-group.qa.transmuter-dev.ishirock.tech",
        ),
        (
            "qa-e2e-20260712-meridian-commercial-bank",
            "meridian-commercial-bank.qa.transmuter-dev.ishirock.tech",
        ),
        (
            "qa-e2e-20260712-solstice-health-network",
            "solstice-health-network.qa.transmuter-dev.ishirock.tech",
        ),
        (
            "qa-e2e-20260712-horizon-energy-utilities",
            "horizon-energy-utilities.qa.transmuter-dev.ishirock.tech",
        ),
    ]
    adapter = TypeAdapter(EmailStr)
    mappings = [migration.expected_email_mappings(profile) for profile in COMPANY_PROFILES]

    assert len(mappings) == 5
    assert sum(map(len, mappings)) == 50
    assert all(
        str(adapter.validate_python(new_email)) == new_email
        for profile_mappings in mappings
        for new_email, _role, _identity in profile_mappings.values()
    )


def test_mapping_rejects_a_profile_outside_the_exact_slug_allowlist() -> None:
    unreviewed = replace(COMPANY_PROFILES[0], slug="qa-e2e-unreviewed-tenant")

    with pytest.raises(migration.MigrationError, match="outside the reviewed"):
        migration.expected_email_mappings(unreviewed)


def test_apply_updates_only_pending_identities_auth_then_tenant_scoped_cas(
    tmp_path: Any,
) -> None:
    already_complete = (COMPANY_PROFILES[0].slug, "admin")
    client, subjects = _client_with_fixture(complete={already_complete})
    original_snapshots = {
        subject: (
            user.password_hash,
            user.app_metadata.copy(),
            user.user_metadata.copy(),
            user.role,
        )
        for subject, user in client.auth_users.items()
    }
    plan = migration.preflight(client)

    result = migration.apply_migration(client, plan, tmp_path / "journal.json")

    complete_subject = subjects[already_complete]
    writes = [event for event in client.events if event["subject"] != complete_subject]
    assert all(item.state == "complete" for item in result.identities)
    assert not any(event["subject"] == complete_subject for event in client.events)
    assert len(writes) == 98
    for offset in range(0, len(writes), 2):
        auth_event, platform_event = writes[offset : offset + 2]
        assert auth_event["kind"] == "auth"
        assert platform_event["kind"] == "platform"
        assert auth_event["subject"] == platform_event["subject"]
        assert set(auth_event["payload"]) == {"email", "email_confirm"}  # type: ignore[arg-type]
        assert auth_event["payload"]["email_confirm"] is True  # type: ignore[index]
        filters = platform_event["filters"]  # type: ignore[assignment]
        assert {key for key, _value in filters} == {"id", "tenant_id", "email"}
    assert {
        subject: (user.password_hash, user.app_metadata, user.user_metadata, user.role)
        for subject, user in client.auth_users.items()
    } == original_snapshots


def test_rollback_never_reverts_an_identity_complete_before_this_run(tmp_path: Any) -> None:
    already_complete = (COMPANY_PROFILES[0].slug, "admin")
    client, subjects = _client_with_fixture(complete={already_complete})
    plan = migration.preflight(client)
    preexisting_subject = subjects[already_complete]
    preexisting_email = client.auth_users[preexisting_subject].email
    pending = [item for item in plan.identities if item.state == "pending"]
    first_pending = pending[0]
    client.fail_platform_subject = pending[1].subject_id

    with pytest.raises(migration.MigrationError, match="rolled back"):
        migration.apply_migration(client, plan, tmp_path / "journal.json")

    assert client.auth_users[preexisting_subject].email == preexisting_email
    platform = next(row for row in client.tables["users"] if row["id"] == preexisting_subject)
    assert platform["email"] == preexisting_email
    assert client.auth_users[first_pending.subject_id].email == first_pending.old_email
    assert migration.preflight(client).identities == plan.identities


def test_preflight_rejects_a_claimed_target_email() -> None:
    client, _subjects = _client_with_fixture()
    profile = COMPANY_PROFILES[0]
    target_email = next(iter(migration.expected_email_mappings(profile).values()))[0]
    client.auth_users["colliding-subject"] = SimpleNamespace(
        id="colliding-subject",
        email=target_email,
        app_metadata={},
        user_metadata={},
        role="authenticated",
        is_super_admin=False,
    )

    with pytest.raises(migration.MigrationError, match="already claimed"):
        migration.preflight(client)


def test_preflight_rejects_split_auth_and_platform_email_state() -> None:
    client, subjects = _client_with_fixture()
    profile = COMPANY_PROFILES[0]
    key = (profile.slug, "admin")
    subject = subjects[key]
    mapping = migration.expected_email_mappings(profile)
    new_email = next(new for _old, (new, _role, identity) in mapping.items() if identity == "admin")
    client.auth_users[subject].email = new_email

    with pytest.raises(migration.MigrationError, match="Auth and platform emails are split"):
        migration.preflight(client)


def test_postflight_failure_rolls_back_every_changed_identity_in_reverse_order(
    tmp_path: Any,
) -> None:
    client, _subjects = _client_with_fixture()
    plan = migration.preflight(client)
    client.fail_list_users_call = client.list_users_calls + len(plan.identities) + 1

    with pytest.raises(migration.MigrationError, match="rolled back"):
        migration.apply_migration(client, plan, tmp_path / "journal.json")

    rollback_events = client.events[-2 * len(plan.identities) :]
    expected_rollback = [
        (kind, identity.subject_id)
        for identity in reversed(plan.identities)
        for kind in ("platform", "auth")
    ]
    assert [
        (str(event["kind"]), str(event["subject"])) for event in rollback_events
    ] == expected_rollback
    restored = migration.preflight(client)
    assert all(identity.state == "pending" for identity in restored.identities)


def test_unrelated_auth_mutation_after_writes_triggers_fixture_rollback(
    tmp_path: Any,
) -> None:
    client, _subjects = _client_with_fixture()
    unrelated_subject = "unrelated-subject"
    client.auth_users[unrelated_subject] = SimpleNamespace(
        id=unrelated_subject,
        email="unrelated@example.com",
        app_metadata={"source": "external"},
        user_metadata={"display_name": "Unrelated"},
        role="authenticated",
        is_super_admin=False,
    )
    client.unrelated_subject = unrelated_subject
    plan = migration.preflight(client)
    client.mutate_unrelated_after_platform_subject = plan.identities[-1].subject_id

    with pytest.raises(migration.MigrationError, match="rolled back"):
        migration.apply_migration(client, plan, tmp_path / "journal.json")

    assert client.auth_users[unrelated_subject].app_metadata["concurrent_change"] is True
    restored = migration.preflight(client)
    assert all(identity.state == "pending" for identity in restored.identities)
    rollback_subjects = [
        str(event["subject"]) for event in client.events[-2 * len(plan.identities) :]
    ]
    assert unrelated_subject not in rollback_subjects


def test_preflight_rejects_non_authenticated_auth_role() -> None:
    client, subjects = _client_with_fixture()
    subject = subjects[(COMPANY_PROFILES[0].slug, "admin")]
    client.auth_users[subject].role = "service_role"

    with pytest.raises(migration.MigrationError, match="unsafe Auth privilege"):
        migration.preflight(client)


def test_main_loads_hostinger_environment_before_settings_bound_imports() -> None:
    source = inspect.getsource(migration.main)

    load_environment = source.index("five_tenant.load_runtime_environment(args)")
    import_enterprise = source.index(
        "from scripts import seed_enterprise_transformation_scenario as enterprise"
    )
    import_database = source.index("from app.core.database import get_supabase_admin")
    get_client = source.index("client = get_supabase_admin()")

    assert load_environment < import_enterprise < import_database < get_client
