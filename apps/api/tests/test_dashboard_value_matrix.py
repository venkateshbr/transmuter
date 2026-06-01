from uuid import UUID

from app.services.dashboard import DashboardService


class _Repo:
    pass


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


def test_executive_summary_pdf_uses_dashboard_context() -> None:
    service = DashboardService(_Repo())  # type: ignore[arg-type]

    def fake_dashboard_data(**_: object) -> dict[str, object]:
        return {
            "summary": {"total_initiatives": 3, "at_risk": 1, "pending_approvals": 2},
            "value_bridge": {
                "benefits_base": "100.0000",
                "benefits_high": "150.0000",
                "benefits_actual": "80.0000",
                "costs_plan": "25.0000",
                "costs_actual": "30.0000",
                "net_base": "75.0000",
                "net_actual": "50.0000",
            },
            "kpi_pulse": {"health_score": "66.7", "missing_base": 1},
            "risk_heatmap": {"high_medium": 1},
            "recent_activity": [{"initiative_id": "init-1", "rag_status": "red"}],
            "value_matrix": {
                "totals": {
                    "total": {
                        "initiatives": [
                            {"id": "init-1", "name": "Korea pricing launch", "actual": "80.0000"}
                        ]
                    }
                }
            },
        }

    service.get_dashboard_data = fake_dashboard_data  # type: ignore[method-assign]

    pdf = service.generate_executive_summary_pdf(
        user_id=UUID("22222222-2222-2222-2222-222222222222"),
        role="transformation_office",
    )

    assert pdf.startswith(b"%PDF-1.4")
    assert b"Transmuter Executive Summary" in pdf
    assert b"Resolve 2 pending gate approvals" in pdf
