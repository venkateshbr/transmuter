"""KPI service — business logic layer."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.domain.kpis import (
    KPICreate,
    KPIEntryItem,
    KPIEntryUpsert,
    KPIItem,
    KPIListResponse,
    KPIPulseSummary,
    KPIUpdate,
)
from app.repositories.kpi import KPIRepository


class KPIService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = KPIRepository(client, tenant_id)
        self._tenant_id = tenant_id

    # ── List / Detail ────────────────────────────────────────────────

    def list_kpis(self, initiative_id: str) -> KPIListResponse:
        kpi_rows = self._repo.list(initiative_id)
        return self._format_kpi_response(kpi_rows)

    def list_all_kpis(self) -> KPIListResponse:
        kpi_rows = self._repo.list_all()
        return self._format_kpi_response(kpi_rows)

    def _format_kpi_response(self, kpi_rows: list[dict]) -> KPIListResponse: # type: ignore[type-arg]
        kpi_ids = [r["id"] for r in kpi_rows]
        
        def _str(v: object) -> str | None:
            return str(v) if v is not None else None

        entries_by_kpi: dict[str, list[KPIEntryItem]] = {k: [] for k in kpi_ids}
        if kpi_ids:
            all_entries = self._repo.get_entries(kpi_ids)
            for e in all_entries:
                entries_by_kpi[e["kpi_id"]].append(
                    KPIEntryItem(
                        id=e["id"],
                        kpi_id=e["kpi_id"],
                        year=e["year"],
                        quarter=e.get("quarter"),
                        value_base=_str(e.get("value_base")),
                        value_high=_str(e.get("value_high")),
                        value_actual=_str(e.get("value_actual")),
                    )
                )

        items = []
        for r in kpi_rows:
            # Flatten initiative info if present
            initiative_name = None
            initiative_code = None
            if "initiative" in r and r["initiative"]:
                initiative_name = r["initiative"].get("name")
                initiative_code = r["initiative"].get("initiative_code")

            # Determine health_status for this specific KPI
            health_status = "no_data"
            k_entries = entries_by_kpi.get(r["id"], [])
            actuals = [e for e in k_entries if e.value_actual is not None]
            if actuals:
                def sort_key(e: KPIEntryItem) -> tuple[int, int]:
                    return (e.year, e.quarter or 5)
                
                latest_entry = sorted(actuals, key=sort_key, reverse=True)[0]
                actual_val = Decimal(latest_entry.value_actual) # type: ignore[arg-type]
                base_val = Decimal(latest_entry.value_base or "0")
                high_val = Decimal(latest_entry.value_high or str(base_val))

                if actual_val >= high_val:
                    health_status = "on_track"
                elif actual_val >= base_val:
                    health_status = "at_risk"
                else:
                    health_status = "critical"

            items.append(
                KPIItem(
                    id=r["id"],
                    initiative_id=r["initiative_id"],
                    initiative_name=initiative_name,
                    initiative_code=initiative_code,
                    health_status=health_status, # type: ignore[arg-type]
                    name=r["name"],
                    type=r["type"],
                    category=r.get("category"),
                    frequency=r["frequency"],
                    unit=r.get("unit"),
                    entries=entries_by_kpi.get(r["id"], []),
                )
            )

        return KPIListResponse(items=items, total=len(items))

    # ── CRUD ─────────────────────────────────────────────────────────

    def create_kpi(self, initiative_id: str, data: KPICreate) -> KPIItem:
        row = self._repo.create(initiative_id, data.model_dump(exclude_none=True))
        return KPIItem(
            id=row["id"],
            initiative_id=row["initiative_id"],
            name=row["name"],
            type=row["type"],
            category=row.get("category"),
            frequency=row["frequency"],
            unit=row.get("unit"),
            entries=[],
        )

    def update_kpi(self, kpi_id: str, data: KPIUpdate) -> KPIItem:
        self._assert_exists(kpi_id)
        patch = data.model_dump(exclude_none=True)
        row = self._repo.update(kpi_id, patch)
        
        # To return full item, we fetch entries
        entries = self._repo.get_entries([kpi_id])
        def _str(v: object) -> str | None:
            return str(v) if v is not None else None

        entry_items = [
            KPIEntryItem(
                id=e["id"],
                kpi_id=e["kpi_id"],
                year=e["year"],
                quarter=e.get("quarter"),
                value_base=_str(e.get("value_base")),
                value_high=_str(e.get("value_high")),
                value_actual=_str(e.get("value_actual")),
            )
            for e in entries
        ]
        
        return KPIItem(
            id=row["id"],
            initiative_id=row["initiative_id"],
            name=row["name"],
            type=row["type"],
            category=row.get("category"),
            frequency=row["frequency"],
            unit=row.get("unit"),
            entries=entry_items,
        )

    def delete_kpi(self, kpi_id: str) -> None:
        self._assert_exists(kpi_id)
        self._repo.delete(kpi_id)

    # ── Entries ──────────────────────────────────────────────────────

    def upsert_entries(self, kpi_id: str, entries: list[KPIEntryUpsert]) -> list[KPIEntryItem]:
        self._assert_exists(kpi_id)
        
        # Convert to dicts for repo
        entry_dicts = []
        for e in entries:
            d = {"year": e.year, "quarter": e.quarter}
            if e.value_base is not None:
                d["value_base"] = str(e.value_base) # type: ignore[assignment]
            if e.value_high is not None:
                d["value_high"] = str(e.value_high) # type: ignore[assignment]
            if e.value_actual is not None:
                d["value_actual"] = str(e.value_actual) # type: ignore[assignment]
            entry_dicts.append(d)
            
        self._repo.upsert_entries(kpi_id, entry_dicts)
        
        def _str(v: object) -> str | None:
            return str(v) if v is not None else None

        # Fetch updated entries
        updated = self._repo.get_entries([kpi_id])
        return [
            KPIEntryItem(
                id=e["id"],
                kpi_id=e["kpi_id"],
                year=e["year"],
                quarter=e.get("quarter"),
                value_base=_str(e.get("value_base")),
                value_high=_str(e.get("value_high")),
                value_actual=_str(e.get("value_actual")),
            )
            for e in updated
        ]

    # ── Pulse ────────────────────────────────────────────────────────

    def get_pulse_summary(self) -> KPIPulseSummary:
        kpis, entries = self._repo.get_all_kpis_and_latest_entries()
        
        total_kpis = len(kpis)
        if total_kpis == 0:
            return KPIPulseSummary(
                total_kpis=0, hitting_base=0, missing_base=0, no_actuals=0, health_score="0.0",
            )
            
        hitting = 0
        missing = 0
        no_actuals = 0
        
        # Group entries by kpi_id
        entries_by_kpi: dict[str, list[dict]] = {} # type: ignore[type-arg]
        for e in entries:
            entries_by_kpi.setdefault(e["kpi_id"], []).append(e)
            
        for k in kpis:
            k_entries = entries_by_kpi.get(k["id"], [])
            
            # Find the "latest" entry that has an actual value.
            # If none have actual value, it's no_actuals.
            actuals = [e for e in k_entries if e.get("value_actual") is not None]
            
            if not actuals:
                no_actuals += 1
                continue
                
            # Sort by year desc, quarter desc to get the most recent
            def sort_key(e: dict) -> tuple[int, int]: # type: ignore[type-arg]
                return (e["year"], e.get("quarter") or 5)
                
            latest = sorted(actuals, key=sort_key, reverse=True)[0]
            
            actual_val = Decimal(str(latest["value_actual"]))
            if latest.get("value_base") is not None:
                base_val = Decimal(str(latest["value_base"]))
            else:
                base_val = Decimal("0")
            
            if actual_val >= base_val:
                hitting += 1
            else:
                missing += 1
                
        # Calculate health score: hitting / (hitting + missing)
        total_tracked = hitting + missing
        if total_tracked == 0:
            health = "0.0"
        else:
            pct = (Decimal(hitting) / Decimal(total_tracked)) * Decimal("100")
            health = str(pct.quantize(Decimal("0.1")))
            
        return KPIPulseSummary(
            total_kpis=total_kpis,
            hitting_base=hitting,
            missing_base=missing,
            no_actuals=no_actuals,
            health_score=health,
        )

    # ── Helpers ──────────────────────────────────────────────────────

    def _assert_exists(self, kpi_id: str) -> dict:  # type: ignore[type-arg]
        row = self._repo.get(kpi_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="KPI not found",
            )
        return row
