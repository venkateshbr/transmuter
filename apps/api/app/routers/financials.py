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
    BenefitLedgerImportResult,
    BenefitLedgerRollupSummaryResponse,
    BenefitLedgerSummaryResponse,
    BreakEvenResponse,
    ConfigurableFinancialGridResponse,
    ConfigurableFinancialGridUpdate,
    CostLineCreate,
    CostLineItem,
    CostLineListResponse,
    CostLineUpdate,
    FinancialAttributeDefinition,
    FinancialBenefitLine,
    FinancialBenefitLineCreate,
    FinancialBenefitLineHandoffUpdate,
    FinancialBenefitLineValidationEvent,
    FinancialBenefitLineValidationRequest,
    FinancialBenefitValidationStatus,
    FinancialBridgeRow,
    FinancialCategoryDeleteRequest,
    FinancialCellAssumption,
    FinancialCellAssumptionCreate,
    FinancialCellAssumptionListResponse,
    FinancialCellAssumptionUpdate,
    FinancialConfigurationResponse,
    FinancialConfigurationUpdate,
    FinancialCostCategory,
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
    InitiativeAnnualBaselineResponse,
    InitiativeAnnualBaselineUpdate,
    InitiativeFinancialSelections,
    InitiativeFinancialSelectionsResponse,
    PortfolioBenefitsRegisterResponse,
    PortfolioFinancialContributorsResponse,
    PortfolioFinancialsResponse,
    PortfolioGranularity,
    PortfolioInitiativePortfolioResponse,
    PortfolioInvestmentPaybackResponse,
    PortfolioValueBridgeBasis,
    PortfolioValueRampResponse,
    ScenarioFinancialSummary,
    TenantAnnualBaselineResponse,
    TenantAnnualBaselineUpdate,
    ValueBridgeResponse,
    WorkstreamTargetLockRequest,
    WorkstreamTargetLockResponse,
    WorkstreamTargetLockVersion,
    WorkstreamTargetPreviewResponse,
)
from app.domain.governance import GateSubmissionItem
from app.services.financial import FinancialService
from app.services.governance import GovernanceService

router = APIRouter(tags=["financials"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> FinancialService:
    return FinancialService(client, current_user.tenant_id)


def _governance_svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> GovernanceService:
    return GovernanceService(client, current_user.tenant_id, current_user.id, current_user.role)


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


@router.post(
    "/initiatives/{initiative_id}/financials/benefit-lines",
    response_model=FinancialBenefitLine,
    status_code=201,
)
async def create_benefit_line(
    initiative_id: str,
    body: FinancialBenefitLineCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialBenefitLine:
    assert_can_manage_initiatives(current_user)
    return svc.create_benefit_line(initiative_id, body, str(current_user.id))


@router.delete(
    "/initiatives/{initiative_id}/financials/benefit-lines/{benefit_line_id}",
    status_code=204,
)
async def delete_benefit_line(
    initiative_id: str,
    benefit_line_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_benefit_line(initiative_id, benefit_line_id)


@router.post(
    "/initiatives/{initiative_id}/financials/benefit-lines/{benefit_line_id}/submit",
    response_model=FinancialBenefitLine,
)
async def submit_benefit_line_for_validation(
    initiative_id: str,
    benefit_line_id: str,
    body: FinancialBenefitLineValidationRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialBenefitLine:
    assert_can_manage_initiatives(current_user)
    return svc.submit_benefit_line_for_validation(
        initiative_id, benefit_line_id, body, str(current_user.id)
    )


@router.post(
    "/initiatives/{initiative_id}/financials/benefit-lines/{benefit_line_id}/validate",
    response_model=FinancialBenefitLine,
)
async def validate_benefit_line(
    initiative_id: str,
    benefit_line_id: str,
    body: FinancialBenefitLineValidationRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialBenefitLine:
    assert_can_manage_initiatives(current_user)
    return svc.validate_benefit_line(initiative_id, benefit_line_id, body, str(current_user.id))


@router.post(
    "/initiatives/{initiative_id}/financials/benefit-lines/{benefit_line_id}/reject",
    response_model=FinancialBenefitLine,
)
async def reject_benefit_line(
    initiative_id: str,
    benefit_line_id: str,
    body: FinancialBenefitLineValidationRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialBenefitLine:
    assert_can_manage_initiatives(current_user)
    return svc.reject_benefit_line(initiative_id, benefit_line_id, body, str(current_user.id))


@router.put(
    "/initiatives/{initiative_id}/financials/benefit-lines/{benefit_line_id}/handoff",
    response_model=FinancialBenefitLine,
)
async def update_benefit_line_handoff(
    initiative_id: str,
    benefit_line_id: str,
    body: FinancialBenefitLineHandoffUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialBenefitLine:
    assert_can_manage_initiatives(current_user)
    return svc.update_benefit_line_handoff(
        initiative_id, benefit_line_id, body, str(current_user.id)
    )


@router.get(
    "/initiatives/{initiative_id}/financials/benefit-lines/{benefit_line_id}/validation-events",
    response_model=list[FinancialBenefitLineValidationEvent],
)
async def list_benefit_line_validation_events(
    initiative_id: str,
    benefit_line_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> list[FinancialBenefitLineValidationEvent]:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.list_benefit_line_validation_events(initiative_id, benefit_line_id)


@router.get(
    "/initiatives/{initiative_id}/financials/baseline",
    response_model=InitiativeAnnualBaselineResponse,
)
async def get_initiative_annual_baseline(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
    baseline_year: int | None = Query(None, ge=2020, le=2060),
) -> InitiativeAnnualBaselineResponse:
    """Return annual original-baseline metrics for an initiative."""
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.get_initiative_annual_baseline(initiative_id, baseline_year)


@router.put(
    "/initiatives/{initiative_id}/financials/baseline",
    response_model=InitiativeAnnualBaselineResponse,
)
async def update_initiative_annual_baseline(
    initiative_id: str,
    body: InitiativeAnnualBaselineUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> InitiativeAnnualBaselineResponse:
    """Upsert annual original-baseline metrics for an initiative."""
    assert_can_manage_initiatives(current_user)
    return svc.update_initiative_annual_baseline(initiative_id, body, str(current_user.id))


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
    response_model=GateSubmissionItem,
)
async def request_bankable_plan_rebaseline(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_governance_svc)],
    body: BankablePlanRebaselineRequest,
) -> GateSubmissionItem:
    assert_can_manage_initiatives(current_user)
    return svc.submit_bankable_plan_rebaseline(initiative_id, body.reason)


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


@router.post(
    "/benefit-ledger/import",
    response_model=BenefitLedgerImportResult,
)
async def import_benefit_ledger(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    file: UploadFile = File(...),
) -> BenefitLedgerImportResult:
    assert_can_manage_initiatives(current_user)
    return svc.import_benefit_ledger_csv(await file.read())


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


@router.get(
    "/financial-engine/annual-baselines",
    response_model=TenantAnnualBaselineResponse,
)
async def get_readonly_tenant_annual_baselines(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    baseline_year: int | None = Query(None, ge=2020, le=2060),
) -> TenantAnnualBaselineResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_tenant_annual_baselines(baseline_year)


@router.get(
    "/admin/financial-engine/annual-baselines",
    response_model=TenantAnnualBaselineResponse,
)
async def get_tenant_annual_baselines(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    baseline_year: int | None = Query(None, ge=2020, le=2060),
) -> TenantAnnualBaselineResponse:
    assert_can_manage_initiatives(current_user)
    return svc.get_tenant_annual_baselines(baseline_year)


@router.put(
    "/admin/financial-engine/annual-baselines",
    response_model=TenantAnnualBaselineResponse,
)
async def update_tenant_annual_baselines(
    body: TenantAnnualBaselineUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> TenantAnnualBaselineResponse:
    assert_can_manage_initiatives(current_user)
    return svc.update_tenant_annual_baselines(body, str(current_user.id))


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


@router.post(
    "/admin/financial-engine/cost-categories",
    response_model=FinancialCostCategory,
    status_code=201,
)
async def create_financial_cost_category(
    body: FinancialCostCategory,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialCostCategory:
    assert_can_manage_initiatives(current_user)
    return svc.create_cost_category(body)


@router.patch(
    "/admin/financial-engine/cost-categories/{cost_category_id}",
    response_model=FinancialCostCategory,
)
async def update_financial_cost_category(
    cost_category_id: str,
    body: FinancialCostCategory,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialCostCategory:
    assert_can_manage_initiatives(current_user)
    return svc.update_cost_category(cost_category_id, body)


@router.post(
    "/admin/financial-engine/bridge-rows",
    response_model=FinancialBridgeRow,
    status_code=201,
)
async def create_financial_bridge_row(
    body: FinancialBridgeRow,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialBridgeRow:
    assert_can_manage_initiatives(current_user)
    return svc.create_bridge_row(body)


@router.patch(
    "/admin/financial-engine/bridge-rows/{bridge_row_id}",
    response_model=FinancialBridgeRow,
)
async def update_financial_bridge_row(
    bridge_row_id: str,
    body: FinancialBridgeRow,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialBridgeRow:
    assert_can_manage_initiatives(current_user)
    return svc.update_bridge_row(bridge_row_id, body)


@router.post(
    "/admin/financial-engine/attribute-definitions",
    response_model=FinancialAttributeDefinition,
    status_code=201,
)
async def create_financial_attribute_definition(
    body: FinancialAttributeDefinition,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialAttributeDefinition:
    assert_can_manage_initiatives(current_user)
    return svc.create_attribute_definition(body)


@router.patch(
    "/admin/financial-engine/attribute-definitions/{attribute_definition_id}",
    response_model=FinancialAttributeDefinition,
)
async def update_financial_attribute_definition(
    attribute_definition_id: str,
    body: FinancialAttributeDefinition,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialAttributeDefinition:
    assert_can_manage_initiatives(current_user)
    return svc.update_attribute_definition(attribute_definition_id, body)


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
    basis: PortfolioValueBridgeBasis = Query("all_years"),
    year: int | None = Query(None, ge=2020, le=2060),
) -> ValueBridgeResponse:
    """Portfolio-level Value Bridge across all initiatives."""
    assert_can_view_portfolio(current_user)
    return svc.get_portfolio_value_bridge(basis=basis, year=year)


@router.get("/portfolio/benefits-register", response_model=PortfolioBenefitsRegisterResponse)
async def get_portfolio_benefits_register(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    year: int | None = Query(None, ge=2020, le=2060),
    validation_status: FinancialBenefitValidationStatus | None = Query(None),
    initiative_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    business_unit_id: str | None = Query(None),
    stage: str | None = Query(None),
    tag: str | None = Query(None),
) -> PortfolioBenefitsRegisterResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_portfolio_benefits_register(
        year=year,
        validation_status=validation_status,
        initiative_id=initiative_id,
        workstream_id=workstream_id,
        business_unit_id=business_unit_id,
        stage=stage,
        tag=tag,
    )


@router.get("/portfolio/board-pack.xlsx")
async def export_portfolio_board_pack(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    year: int | None = Query(None, ge=2020, le=2060),
    basis: PortfolioValueBridgeBasis = Query("all_years"),
) -> Response:
    assert_can_view_portfolio(current_user)
    content = svc.export_portfolio_board_pack(year=year, basis=basis)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="transmuter-board-pack.xlsx"'},
    )


@router.get("/portfolio/financials", response_model=PortfolioFinancialsResponse)
async def get_portfolio_financials(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    granularity: PortfolioGranularity = Query("monthly"),
    year: int | None = Query(None),
    initiative_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    business_unit_id: str | None = Query(None),
    stage: str | None = Query(None),
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
        stage=stage,
        tag=tag,
        category_key=category_key,
    )


@router.get("/portfolio/investments-payback", response_model=PortfolioInvestmentPaybackResponse)
async def get_portfolio_investments_payback(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    value_year: int | None = Query(None, ge=2020, le=2060),
    scenario: str = Query("plan_base"),
    initiative_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    business_unit_id: str | None = Query(None),
    stage: str | None = Query(None),
    tag: str | None = Query(None),
) -> PortfolioInvestmentPaybackResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_portfolio_investments_payback(
        value_year=value_year,
        scenario=scenario,
        initiative_id=initiative_id,
        workstream_id=workstream_id,
        business_unit_id=business_unit_id,
        stage=stage,
        tag=tag,
    )


@router.get("/portfolio/initiative-portfolio", response_model=PortfolioInitiativePortfolioResponse)
async def get_portfolio_initiative_portfolio(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    baseline_year: int | None = Query(None, ge=2020, le=2060),
    value_year: int | None = Query(None, ge=2020, le=2060),
    scenario: str = Query("plan_base"),
    initiative_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    business_unit_id: str | None = Query(None),
    stage: str | None = Query(None),
    tag: str | None = Query(None),
) -> PortfolioInitiativePortfolioResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_portfolio_initiative_portfolio(
        baseline_year=baseline_year,
        value_year=value_year,
        scenario=scenario,
        initiative_id=initiative_id,
        workstream_id=workstream_id,
        business_unit_id=business_unit_id,
        stage=stage,
        tag=tag,
    )


@router.get("/portfolio/value-ramp", response_model=PortfolioValueRampResponse)
async def get_portfolio_value_ramp(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    granularity: PortfolioGranularity = Query("monthly"),
    run_rate_year: int | None = Query(None),
    as_of_date: date | None = Query(None),
    initiative_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    business_unit_id: str | None = Query(None),
    stage: str | None = Query(None),
    tag: str | None = Query(None),
    category_key: str | None = Query(None),
) -> PortfolioValueRampResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_portfolio_value_ramp(
        granularity=granularity,
        run_rate_year=run_rate_year,
        as_of_date=as_of_date,
        initiative_id=initiative_id,
        workstream_id=workstream_id,
        business_unit_id=business_unit_id,
        stage=stage,
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
    stage: str | None = Query(None),
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
        stage=stage,
        tag=tag,
        category_key=category_key,
    )
