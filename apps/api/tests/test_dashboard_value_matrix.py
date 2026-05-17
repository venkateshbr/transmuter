from app.services.dashboard import DashboardService


class _Repo:
    pass


class _ExecutiveSummaryRepo:
    def get_initiatives_for_dashboard(self, owner_user_id=None):
        return [
            {
                "id": "init-1",
                "name": "AP Automation",
                "initiative_code": "AP-001",
                "stage": "in_progress",
                "rag_status": "red",
                "pressure_score": "8.5",
                "workstream_id": "ws-1",
                "tag": "automation",
                "workstreams": {
                    "name": "Operations",
                    "business_unit_id": "bu-1",
                    "business_units": {"name": "North America"},
                },
            },
            {
                "id": "init-2",
                "name": "Commercial Lift",
                "initiative_code": "COM-001",
                "stage": "scoping",
                "rag_status": "green",
                "pressure_score": "2.0",
                "workstream_id": "ws-1",
                "tag": "commercial",
                "workstreams": {
                    "name": "Operations",
                    "business_unit_id": "bu-1",
                    "business_units": {"name": "North America"},
                },
            },
        ]

    def get_risks_for_heatmap(self):
        return [
            {
                "id": "risk-1",
                "initiative_id": "init-1",
                "impact": "high",
                "likelihood": "high",
            }
        ]

    def get_open_risks_detail(self):
        return [
            {
                "id": "risk-1",
                "initiative_id": "init-1",
                "description": "ERP dependency may slip",
                "impact": "high",
                "likelihood": "high",
                "rating": "high",
                "initiatives": {"name": "AP Automation", "initiative_code": "AP-001"},
            }
        ]

    def get_kpi_data(self):
        return (
            [{"id": "kpi-1", "name": "Cycle time", "initiative_id": "init-1"}],
            [{"kpi_id": "kpi-1", "year": 2026, "quarter": 2, "value_base": "10", "value_actual": "8"}],
        )

    def get_financial_summary_data(self):
        return (
            [
                {
                    "initiative_id": "init-1",
                    "year": 2026,
                    "gm_uplift_base": "100.0000",
                    "gm_uplift_high": "125.0000",
                    "gm_uplift_actual": "80.0000",
                }
            ],
            [{"initiative_id": "init-1", "year": 2026, "amount_plan": "10.0000", "amount_actual": "8.0000"}],
        )

    def get_my_milestones(self, user_id, limit=5):
        return []

    def get_pending_approvals_count(self):
        return 1

    def get_my_actions(self, user_id, limit=5):
        return []

    def get_recent_activity(self):
        return []

    def get_filter_options(self):
        return ([{"id": "bu-1", "name": "North America"}], [{"id": "ws-1", "name": "Operations"}])


def test_value_matrix_groups_workstreams_tags_and_selected_year() -> None:
    service = DashboardService(_Repo())  # type: ignore[arg-type]
    initiatives = [
        {
            "id": "init-1",
            "name": "Automation Savings",
            "initiative_code": "AUT-001",
            "stage": "in_progress",
            "rag_status": "green",
            "workstream_id": "ws-1",
            "tag": "automation",
            "workstreams": {
                "name": "Operations",
                "business_units": {"name": "North America"},
            },
        },
        {
            "id": "init-2",
            "name": "Commercial Lift",
            "initiative_code": "COM-001",
            "stage": "scoping",
            "rag_status": "amber",
            "workstream_id": "ws-1",
            "tag": "commercial",
            "workstreams": {
                "name": "Operations",
                "business_units": {"name": "North America"},
            },
        },
        {
            "id": "init-3",
            "name": "No FY28 Value",
            "initiative_code": "OFF-001",
            "stage": "scoping",
            "rag_status": "green",
            "workstream_id": "ws-2",
            "tag": "offshoring",
            "workstreams": {"name": "Finance", "business_units": {"name": "Shared Services"}},
        },
    ]
    entries = [
        {
            "initiative_id": "init-1",
            "year": 2028,
            "quarter": 1,
            "gm_uplift_base": "100.0000",
            "gm_uplift_high": "150.0000",
            "gm_uplift_actual": "25.0000",
        },
        {
            "initiative_id": "init-1",
            "year": 2028,
            "quarter": 2,
            "gm_uplift_base": "50.0000",
            "gm_uplift_high": "75.0000",
            "gm_uplift_actual": None,
        },
        {
            "initiative_id": "init-2",
            "year": 2028,
            "quarter": None,
            "gm_uplift_base": "200.0000",
            "gm_uplift_high": "300.0000",
            "gm_uplift_actual": "125.0000",
        },
        {
            "initiative_id": "init-3",
            "year": 2027,
            "quarter": None,
            "gm_uplift_base": "999.0000",
            "gm_uplift_high": "999.0000",
            "gm_uplift_actual": "999.0000",
        },
    ]
    costs = [
        {
            "initiative_id": "init-1",
            "year": 2028,
            "quarter": None,
            "amount_plan": "10.0000",
            "amount_actual": "4.0000",
            "is_recurring": True,
        },
        {
            "initiative_id": "init-1",
            "year": 2028,
            "quarter": None,
            "amount_plan": "5.0000",
            "amount_actual": "2.0000",
            "is_recurring": False,
        },
    ]

    matrix = service._calculate_value_matrix(initiatives, entries, costs, 2028)
    operations = next(row for row in matrix["rows"] if row["workstream_name"] == "Operations")
    finance = next(row for row in matrix["rows"] if row["workstream_name"] == "Finance")
    automation_initiative = operations["cells"]["automation"]["initiatives"][0]

    assert matrix["selected_year"] == 2028
    assert matrix["available_years"] == [2027, 2028]
    assert operations["cells"]["automation"]["base"] == "150.0000"
    assert operations["cells"]["automation"]["high"] == "225.0000"
    assert operations["cells"]["automation"]["initiative_count"] == 1
    assert operations["cells"]["commercial"]["base"] == "200.0000"
    assert operations["total"]["base"] == "350.0000"
    assert automation_initiative["gross_margin_base"] == "150.0000"
    assert automation_initiative["recurring_costs_plan"] == "10.0000"
    assert automation_initiative["one_time_costs_plan"] == "5.0000"
    assert automation_initiative["net_value_base"] == "135.0000"
    assert finance["cells"]["offshoring"]["initiative_count"] == 0
    assert matrix["totals"]["total"]["high"] == "525.0000"


def test_value_matrix_uses_latest_available_year_when_target_missing() -> None:
    service = DashboardService(_Repo())  # type: ignore[arg-type]

    matrix = service._calculate_value_matrix(
        initiatives=[
            {
                "id": "init-1",
                "name": "Automation Savings",
                "initiative_code": "AUT-001",
                "stage": "in_progress",
                "rag_status": "green",
                "workstream_id": "ws-1",
                "tag": "automation",
                "workstreams": {
                    "name": "Operations",
                    "business_units": {"name": "North America"},
                },
            }
        ],
        entries=[
            {
                "initiative_id": "init-1",
                "year": 2027,
                "quarter": None,
                "gm_uplift_base": "100.0000",
                "gm_uplift_high": "125.0000",
                "gm_uplift_actual": None,
            }
        ],
        costs=[],
        target_year=2030,
    )

    assert matrix["selected_year"] == 2027
    assert matrix["totals"]["total"]["base"] == "100.0000"


def test_pipeline_by_stage_detail_includes_financial_ranges() -> None:
    service = DashboardService(_Repo())  # type: ignore[arg-type]

    detail = service._calculate_pipeline_by_stage_detail(
        initiatives=[
            {"id": "init-1", "stage": "scoping"},
            {"id": "init-2", "stage": "in_progress"},
        ],
        entries=[
            {
                "initiative_id": "init-1",
                "gm_uplift_base": "100.0000",
                "gm_uplift_high": "150.0000",
                "gm_uplift_actual": "25.0000",
            },
            {
                "initiative_id": "init-2",
                "gm_uplift_base": "300.0000",
                "gm_uplift_high": "450.0000",
                "gm_uplift_actual": "125.0000",
            },
        ],
        costs=[
            {
                "initiative_id": "init-1",
                "amount_plan": "40.0000",
                "amount_actual": "10.0000",
            }
        ],
    )

    assert detail["scoping"]["count"] == 1
    assert detail["scoping"]["benefits_base"] == "100.0000"
    assert detail["scoping"]["net_base"] == "60.0000"
    assert detail["in_progress"]["benefits_high"] == "450.0000"
    assert detail["complete"]["count"] == 0


def test_executive_summary_generation_uses_dashboard_facts() -> None:
    service = DashboardService(_ExecutiveSummaryRepo())  # type: ignore[arg-type]

    summary = service.generate_executive_summary(
        user_id="00000000-0000-0000-0000-000000000001",  # type: ignore[arg-type]
        role="admin",
        business_unit_id="bu-1",
    )

    assert summary["portfolio_health"]["total_initiatives"] == 2
    assert summary["portfolio_health"]["at_risk"] == 1
    assert summary["financial_overview"]["net_base"] == "90.0000"
    assert summary["kpi_pulse"]["missing_base"] == 1
    assert summary["top_initiatives"][0]["code"] == "AP-001"
    assert summary["key_risks"][0]["description"] == "ERP dependency may slip"
    assert "pending gate approvals" in " ".join(summary["recommended_actions"])


def test_executive_summary_pdf_is_valid_pdf_bytes(monkeypatch) -> None:
    service = DashboardService(_ExecutiveSummaryRepo())  # type: ignore[arg-type]
    monkeypatch.setattr(service, "_trace_executive_summary", lambda summary: None)

    content = service.generate_executive_summary_pdf(
        user_id="00000000-0000-0000-0000-000000000001",  # type: ignore[arg-type]
        role="admin",
    )

    assert content.startswith(b"%PDF-1.4")
    assert b"Transmuter Executive Summary" in content
