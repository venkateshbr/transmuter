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

    matrix = service._calculate_value_matrix(initiatives, entries, 2028)
    operations = next(row for row in matrix["rows"] if row["workstream_name"] == "Operations")
    finance = next(row for row in matrix["rows"] if row["workstream_name"] == "Finance")

    assert matrix["selected_year"] == 2028
    assert matrix["available_years"] == [2027, 2028]
    assert operations["cells"]["automation"]["base"] == "150.0000"
    assert operations["cells"]["automation"]["high"] == "225.0000"
    assert operations["cells"]["automation"]["initiative_count"] == 1
    assert operations["cells"]["commercial"]["base"] == "200.0000"
    assert operations["total"]["base"] == "350.0000"
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
                "workstreams": {"name": "Operations", "business_units": {"name": "North America"}},
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
        target_year=2030,
    )

    assert matrix["selected_year"] == 2027
    assert matrix["totals"]["total"]["base"] == "100.0000"
