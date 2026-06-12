"""Financial router — thin parse + respond layer."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin, get_supabase_request_client
from app.core.rbac import (
    assert_can_manage_initiatives,
    assert_can_view_initiative,
    assert_can_view_portfolio,
)
from app.domain.financials import (
    BankablePlanRebaselineRequest,
    BankablePlanResponse,
    BankablePlanVersion,
    BenefitLedgerEntry,
    BenefitLedgerEntryCreate,
    BenefitLedgerEntryUpdate,
    BenefitLedgerGranularity,
    BenefitLedgerRollupSummaryResponse,
    BenefitLedgerSummaryResponse,
    BreakEvenResponse,
    ConfigurableFinancialGridResponse,
    ConfigurableFinancialGridUpdate,
    CostLineCreate,
    CostLineItem,
    CostLineListResponse,
    CostLineUpdate,
    FinancialCategoryDeleteRequest,
    FinancialCellAssumption,
    FinancialCellAssumptionCreate,
    FinancialCellAssumptionListResponse,
    FinancialCellAssumptionUpdate,
    FinancialConfigurationResponse,
    FinancialConfigurationUpdate,
    FinancialEngineConfigurationResponse,
    FinancialForecastResponse,
    FinancialForecastUpdate,
    FinancialGovernanceSettings,
    FinancialGovernanceSettingsUpdate,
    FinancialGridResponse,
    FinancialMetricDeactivateRequest,
    FinancialMetricDefinition,
    FinancialMetricDefinitionCreate,
    FinancialMetricDefinitionUpdate,
    FinancialReportingSettings,
    FinancialReportingSettingsUpdate,
    FinancialScenario,
    FinancialScenarioDefinition,
    FinancialScenarioDefinitionCreate,
    FinancialScenarioDefinitionUpdate,
    InitiativeFinancialSelections,
    InitiativeFinancialSelectionsResponse,
    PortfolioFinancialContributorsResponse,
    PortfolioFinancialsResponse,
    PortfolioGranularity,
    ScenarioFinancialSummary,
    ValueBridgeResponse,
    WorkstreamTargetLockRequest,
    WorkstreamTargetLockResponse,
    WorkstreamTargetLockVersion,
    WorkstreamTargetPreviewResponse,
)
from app.services.financial import FinancialService

router = APIRouter(tags=["financials"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> FinancialService:
    return FinancialService(client, current_user.tenant_id)


def _admin_svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> FinancialService:
    return FinancialService(get_supabase_admin(), current_user.tenant_id)


# ── Financial Grid ────────────────────────────────────────────────────────────


@router.get(
    "/initiatives/{initiative_id}/financials", response_model=ConfigurableFinancialGridResponse
)
async def get_financials(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> ConfigurableFinancialGridResponse:
    """Return the configurable monthly financial grid for an initiative."""
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.get_configurable_financial_grid(initiative_id)


@router.put(
    "/initiatives/{initiative_id}/financials", response_model=ConfigurableFinancialGridResponse
)
async def update_financials(
    initiative_id: str,
    body: ConfigurableFinancialGridUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> ConfigurableFinancialGridResponse:
    """Upsert the configurable monthly financial grid for an initiative."""
    assert_can_manage_initiatives(current_user)
    return svc.update_configurable_financial_grid(initiative_id, body, str(current_user.id))


@router.get(
    "/initiatives/{initiative_id}/bankable-plan",
    response_model=BankablePlanResponse,
)
async def get_bankable_plan(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> BankablePlanResponse:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.get_bankable_plan_history(initiative_id)


@router.get(
    "/initiatives/{initiative_id}/bankable-plan/history",
    response_model=list[BankablePlanVersion],
)
async def list_bankable_plan_history(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> list[BankablePlanVersion]:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.list_bankable_plan_history(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/bankable-plan/rebaseline",
    response_model=BankablePlanVersion,
)
async def rebaseline_bankable_plan(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    body: BankablePlanRebaselineRequest | None = None,
) -> BankablePlanVersion:
    assert_can_manage_initiatives(current_user)
    return svc.rebaseline_bankable_plan(
        initiative_id,
        str(current_user.id),
        reason=body.reason if body else None,
    )


@router.get(
    "/initiatives/{initiative_id}/benefit-ledger",
    response_model=list[BenefitLedgerEntry],
)
async def list_benefit_ledger_entries(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> list[BenefitLedgerEntry]:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.list_benefit_ledger_entries(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/benefit-ledger",
    response_model=BenefitLedgerEntry,
    status_code=201,
)
async def create_benefit_ledger_entry(
    initiative_id: str,
    body: BenefitLedgerEntryCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> BenefitLedgerEntry:
    assert_can_manage_initiatives(current_user)
    return svc.create_benefit_ledger_entry(initiative_id, body)


@router.put(
    "/initiatives/{initiative_id}/benefit-ledger/{entry_id}",
    response_model=BenefitLedgerEntry,
)
async def update_benefit_ledger_entry(
    initiative_id: str,
    entry_id: str,
    body: BenefitLedgerEntryUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> BenefitLedgerEntry:
    assert_can_manage_initiatives(current_user)
    return svc.update_benefit_ledger_entry(initiative_id, entry_id, body)


@router.delete(
    "/initiatives/{initiative_id}/benefit-ledger/{entry_id}",
    status_code=204,
)
async def delete_benefit_ledger_entry(
    initiative_id: str,
    entry_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_benefit_ledger_entry(initiative_id, entry_id)


@router.get(
    "/benefit-ledger/summary",
    response_model=BenefitLedgerRollupSummaryResponse,
)
async def get_benefit_ledger_rollup_summary(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    granularity: BenefitLedgerGranularity = Query("monthly"),
    workstream_id: str | None = Query(None),
) -> BenefitLedgerRollupSummaryResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_benefit_ledger_rollup_summary(granularity, workstream_id)


@router.get(
    "/initiatives/{initiative_id}/benefit-ledger/summary",
    response_model=BenefitLedgerSummaryResponse,
)
async def get_benefit_ledger_summary(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
    granularity: BenefitLedgerGranularity = Query("monthly"),
) -> BenefitLedgerSummaryResponse:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.get_benefit_ledger_summary(initiative_id, granularity)


@router.get(
    "/admin/financial-governance",
    response_model=FinancialGovernanceSettings,
)
async def get_financial_governance_settings(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_admin_svc)],
) -> FinancialGovernanceSettings:
    assert_can_manage_initiatives(current_user)
    return svc.get_governance_settings()


@router.put(
    "/admin/financial-governance",
    response_model=FinancialGovernanceSettings,
)
async def update_financial_governance_settings(
    body: FinancialGovernanceSettingsUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_admin_svc)],
) -> FinancialGovernanceSettings:
    assert_can_manage_initiatives(current_user)
    return svc.update_governance_settings(body)


@router.get(
    "/workstreams/{workstream_id}/target-lock/preview",
    response_model=WorkstreamTargetPreviewResponse,
)
async def preview_workstream_target_lock(
    workstream_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    lock_date: date | None = Query(None),
) -> WorkstreamTargetPreviewResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_workstream_target_preview(workstream_id, lock_date or date.today())


@router.get(
    "/workstreams/{workstream_id}/target-lock",
    response_model=WorkstreamTargetLockResponse,
)
async def get_workstream_target_lock_history(
    workstream_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> WorkstreamTargetLockResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_workstream_target_history(workstream_id)


@router.post(
    "/workstreams/{workstream_id}/target-lock",
    response_model=WorkstreamTargetLockVersion,
    status_code=201,
)
async def lock_workstream_target(
    workstream_id: str,
    body: WorkstreamTargetLockRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> WorkstreamTargetLockVersion:
    assert_can_manage_initiatives(current_user)
    return svc.lock_workstream_target(workstream_id, body, str(current_user.id))


@router.get(
    "/initiatives/{initiative_id}/financials/selections",
    response_model=InitiativeFinancialSelectionsResponse,
)
async def get_financial_selections(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> InitiativeFinancialSelectionsResponse:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.get_initiative_selections(initiative_id)


@router.put(
    "/initiatives/{initiative_id}/financials/selections",
    response_model=InitiativeFinancialSelectionsResponse,
)
async def update_financial_selections(
    initiative_id: str,
    body: InitiativeFinancialSelections,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> InitiativeFinancialSelectionsResponse:
    assert_can_manage_initiatives(current_user)
    return svc.update_initiative_selections(initiative_id, body)


@router.get(
    "/initiatives/{initiative_id}/financials/forecasts",
    response_model=FinancialForecastResponse,
)
async def list_financial_forecasts(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> FinancialForecastResponse:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.list_forecasts(initiative_id)


@router.put(
    "/initiatives/{initiative_id}/financials/forecasts",
    response_model=FinancialForecastResponse,
)
async def update_financial_forecasts(
    initiative_id: str,
    body: list[FinancialForecastUpdate],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialForecastResponse:
    assert_can_manage_initiatives(current_user)
    return svc.update_forecasts(initiative_id, body)


@router.get("/initiatives/{initiative_id}/financials/export.xlsx")
async def export_financials_workbook(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> Response:
    """Export financial entries and cost lines as an XLSX workbook."""
    assert_can_view_initiative(client, current_user, initiative_id)
    workbook = svc.export_workbook(initiative_id)
    return Response(
        content=workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f'attachment; filename="initiative-{initiative_id}-financials.xlsx"'
            )
        },
    )


@router.post(
    "/initiatives/{initiative_id}/financials/import.xlsx",
    response_model=FinancialGridResponse,
)
async def import_financials_workbook(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    file: UploadFile = File(...),
) -> FinancialGridResponse:
    """Import financial entries and cost lines from an XLSX workbook."""
    assert_can_manage_initiatives(current_user)
    return svc.import_workbook(initiative_id, await file.read())


# ── Cost Lines ────────────────────────────────────────────────────────────────


@router.get(
    "/initiatives/{initiative_id}/financials/cost-lines",
    response_model=CostLineListResponse,
)
async def list_cost_lines(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> CostLineListResponse:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.list_cost_lines(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/financials/cost-lines",
    response_model=CostLineItem,
    status_code=201,
)
async def create_cost_line(
    initiative_id: str,
    body: CostLineCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> CostLineItem:
    assert_can_manage_initiatives(current_user)
    return svc.create_cost_line(initiative_id, body)


@router.put(
    "/initiatives/{initiative_id}/financials/cost-lines/{cost_line_id}",
    response_model=CostLineItem,
)
async def update_cost_line(
    initiative_id: str,
    cost_line_id: str,
    body: CostLineUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> CostLineItem:
    assert_can_manage_initiatives(current_user)
    return svc.update_cost_line(initiative_id, cost_line_id, body)


@router.delete(
    "/initiatives/{initiative_id}/financials/cost-lines/{cost_line_id}",
    status_code=204,
)
async def delete_cost_line(
    initiative_id: str,
    cost_line_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_cost_line(initiative_id, cost_line_id)


@router.get(
    "/admin/financial-configuration",
    response_model=FinancialConfigurationResponse,
)
async def get_financial_configuration(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialConfigurationResponse:
    assert_can_manage_initiatives(current_user)
    return svc.get_configuration()


@router.get(
    "/financial-configuration",
    response_model=FinancialConfigurationResponse,
)
async def get_readonly_financial_configuration(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialConfigurationResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_configuration()


@router.get(
    "/financial-engine-configuration",
    response_model=FinancialEngineConfigurationResponse,
)
async def get_financial_engine_configuration(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialEngineConfigurationResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_engine_configuration()


@router.put(
    "/admin/financial-engine/reporting-settings",
    response_model=FinancialReportingSettings,
)
async def update_financial_reporting_settings(
    body: FinancialReportingSettingsUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialReportingSettings:
    assert_can_manage_initiatives(current_user)
    return svc.update_reporting_settings(body)


@router.post(
    "/admin/financial-engine/metrics",
    response_model=FinancialMetricDefinition,
    status_code=201,
)
async def create_financial_metric_definition(
    body: FinancialMetricDefinitionCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialMetricDefinition:
    assert_can_manage_initiatives(current_user)
    return svc.create_metric_definition(body, str(current_user.id))


@router.patch(
    "/admin/financial-engine/metrics/{metric_definition_id}",
    response_model=FinancialMetricDefinition,
)
async def update_financial_metric_definition(
    metric_definition_id: str,
    body: FinancialMetricDefinitionUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialMetricDefinition:
    assert_can_manage_initiatives(current_user)
    return svc.update_metric_definition(metric_definition_id, body, str(current_user.id))


@router.post(
    "/admin/financial-engine/scenarios",
    response_model=FinancialScenarioDefinition,
    status_code=201,
)
async def create_financial_scenario_definition(
    body: FinancialScenarioDefinitionCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialScenarioDefinition:
    assert_can_manage_initiatives(current_user)
    return svc.create_scenario_definition(body)


@router.patch(
    "/admin/financial-engine/scenarios/{scenario_id}",
    response_model=FinancialScenarioDefinition,
)
async def update_financial_scenario_definition(
    scenario_id: str,
    body: FinancialScenarioDefinitionUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialScenarioDefinition:
    assert_can_manage_initiatives(current_user)
    return svc.update_scenario_definition(scenario_id, body)


@router.put(
    "/admin/financial-configuration",
    response_model=FinancialConfigurationResponse,
)
async def update_financial_configuration(
    body: FinancialConfigurationUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialConfigurationResponse:
    assert_can_manage_initiatives(current_user)
    return svc.update_configuration(body)


@router.post("/admin/financial-configuration/cost-categories/delete")
async def delete_financial_cost_category(
    body: FinancialCategoryDeleteRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> dict[str, object]:
    assert_can_manage_initiatives(current_user)
    return svc.delete_cost_category(body)


@router.post("/admin/financial-configuration/metrics/deactivate")
async def deactivate_financial_metric(
    body: FinancialMetricDeactivateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> dict[str, object]:
    assert_can_manage_initiatives(current_user)
    return svc.deactivate_metric(body)


# ── Value Bridge ──────────────────────────────────────────────────────────────


@router.get(
    "/initiatives/{initiative_id}/financials/value-bridge",
    response_model=ValueBridgeResponse,
)
async def get_value_bridge(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> ValueBridgeResponse:
    """Value Bridge for a single initiative."""
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.get_value_bridge(initiative_id)


@router.get(
    "/initiatives/{initiative_id}/financials/scenario-summary",
    response_model=ScenarioFinancialSummary,
)
async def get_scenario_summary(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
    scenario: FinancialScenario = Query("base"),
) -> ScenarioFinancialSummary:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.get_scenario_summary(initiative_id, scenario)


@router.get(
    "/initiatives/{initiative_id}/financials/break-even",
    response_model=BreakEvenResponse,
)
async def get_break_even(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
    scenario: FinancialScenario = Query("base"),
) -> BreakEvenResponse:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.get_break_even(initiative_id, scenario)


@router.get(
    "/initiatives/{initiative_id}/financials/assumptions",
    response_model=FinancialCellAssumptionListResponse,
)
async def list_cell_assumptions(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> FinancialCellAssumptionListResponse:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.list_cell_assumptions(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/financials/assumptions",
    response_model=FinancialCellAssumption,
    status_code=201,
)
async def upsert_cell_assumption(
    initiative_id: str,
    body: FinancialCellAssumptionCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialCellAssumption:
    assert_can_manage_initiatives(current_user)
    return svc.upsert_cell_assumption(initiative_id, body, current_user.id)


@router.put(
    "/initiatives/{initiative_id}/financials/assumptions/{assumption_id}",
    response_model=FinancialCellAssumption,
)
async def update_cell_assumption(
    initiative_id: str,
    assumption_id: str,
    body: FinancialCellAssumptionUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialCellAssumption:
    assert_can_manage_initiatives(current_user)
    return svc.update_cell_assumption(initiative_id, assumption_id, body, current_user.id)


@router.delete(
    "/initiatives/{initiative_id}/financials/assumptions/{assumption_id}",
    status_code=204,
)
async def delete_cell_assumption(
    initiative_id: str,
    assumption_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_cell_assumption(initiative_id, assumption_id)


@router.get("/portfolio/value-bridge", response_model=ValueBridgeResponse)
async def get_portfolio_value_bridge(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> ValueBridgeResponse:
    """Portfolio-level Value Bridge across all initiatives."""
    assert_can_view_portfolio(current_user)
    return svc.get_portfolio_value_bridge()


@router.get("/portfolio/financials", response_model=PortfolioFinancialsResponse)
async def get_portfolio_financials(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    granularity: PortfolioGranularity = Query("monthly"),
    year: int | None = Query(None),
    initiative_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    business_unit_id: str | None = Query(None),
    tag: str | None = Query(None),
    category_key: str | None = Query(None),
) -> PortfolioFinancialsResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_portfolio_financials(
        granularity=granularity,
        year=year,
        initiative_id=initiative_id,
        workstream_id=workstream_id,
        business_unit_id=business_unit_id,
        tag=tag,
        category_key=category_key,
    )


@router.get(
    "/portfolio/financials/contributors",
    response_model=PortfolioFinancialContributorsResponse,
)
async def get_portfolio_financial_contributors(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    period: str = Query(..., min_length=4),
    granularity: PortfolioGranularity = Query("monthly"),
    year: int | None = Query(None),
    initiative_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    business_unit_id: str | None = Query(None),
    tag: str | None = Query(None),
    category_key: str | None = Query(None),
) -> PortfolioFinancialContributorsResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_portfolio_financial_contributors(
        granularity=granularity,
        period=period,
        year=year,
        initiative_id=initiative_id,
        workstream_id=workstream_id,
        business_unit_id=business_unit_id,
        tag=tag,
        category_key=category_key,
    )
