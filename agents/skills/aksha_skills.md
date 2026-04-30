# Aksha — SDET & QA Skills

## Skill: Test Writing Patterns

### Backend Unit Test Template (pytest)
```python
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

class TestMyService:
    @pytest.fixture
    def service(self):
        repo = MagicMock()
        journal_svc = MagicMock()
        return MyService(repo=repo, journal_svc=journal_svc)

    async def test_create_valid_amount(self, service):
        """VR-01: Transaction amount must be > 0."""
        result = await service.create(MyFeatureCreate(
            name="Test", amount=Decimal("100.00")
        ))
        assert result is not None

    async def test_create_zero_amount_raises(self, service):
        """VR-01: Zero amount should raise validation error."""
        with pytest.raises(ValueError, match="must be positive"):
            await service.create(MyFeatureCreate(
                name="Test", amount=Decimal("0.00")
            ))

    async def test_journal_entry_balances(self, service):
        """DE-01: Journal entry debits must equal credits."""
        entry = await service.create_with_journal(...)
        total_debits = sum(line.amount for line in entry.lines if line.type == "debit")
        total_credits = sum(line.amount for line in entry.lines if line.type == "credit")
        assert abs(total_debits - total_credits) < Decimal("0.01")

    async def test_tenant_isolation(self, service):
        """Security: User A must never see User B's data."""
        service_a = MyService(tenant_id="tenant_a", ...)
        service_b = MyService(tenant_id="tenant_b", ...)
        await service_a.create(MyFeatureCreate(name="A's item", amount=Decimal("100")))
        items = await service_b.list_all()
        assert len(items) == 0  # B should see nothing from A
```

### Agent Evaluation Template (Pydantic Evals)
```python
from pydantic_evals import Case, Dataset

agent_eval_dataset = Dataset(
    cases=[
        Case(
            name="classify_office_supplies",
            inputs={"description": "Staples and paper clips", "amount": "45.00"},
            expected_output={"classification": "Office Supplies", "account": "6100"},
            metadata={"source": "agent_corrections", "correction_id": 42},
        ),
        Case(
            name="classify_zero_amount_edge_case",
            inputs={"description": "Free trial subscription", "amount": "0.00"},
            expected_output={"classification": "Other", "account": "6900"},
        ),
    ],
)
```

## Skill: QA Process Checklist

When picking up an IN_QA ticket:

### Functional Testing
- [ ] Happy path works as described in ticket
- [ ] Edge cases handled (empty inputs, max values, null fields)
- [ ] Error messages are user-friendly
- [ ] API responses match Pydantic model schemas

### Financial Testing
- [ ] All amounts use `Decimal`, never `float`
- [ ] Journal entries balance (debits = credits)
- [ ] Period lock is enforced
- [ ] Rounding follows `ROUND_HALF_UP`

### Security Testing
- [ ] Tenant isolation verified (cross-tenant query returns empty)
- [ ] RBAC permissions enforced
- [ ] No PII in logs or external API calls
- [ ] Input validation prevents injection

### Frontend Testing
- [ ] Works in both light and dark themes
- [ ] Responsive at all breakpoints
- [ ] Keyboard navigable
- [ ] No console errors

### Regression Testing
- [ ] Existing test suite passes: `cd backend && pytest`
- [ ] Frontend tests pass: `cd frontend && ng test`
- [ ] No flaky tests introduced

## Skill: Security Test Patterns

When Prahari files a security finding, Aksha writes the regression test. These templates cover the most common categories.

### Tenant Isolation Test (must exist for every data resource)
```python
class TestTenantIsolation:
    """Every data resource must be tested for cross-tenant isolation."""

    async def test_cannot_read_other_tenant_data(self, client_tenant_a, client_tenant_b):
        """Tenant A must never see Tenant B's records."""
        res = await client_tenant_a.post("/api/v1/invoices/", json={...})
        assert res.status_code == 201
        invoice_id = res.json()["id"]

        # Tenant B attempts to read it — must get 404, not 200
        res = await client_tenant_b.get(f"/api/v1/invoices/{invoice_id}")
        assert res.status_code == 404, "CRITICAL: Cross-tenant data leak!"

    async def test_cannot_modify_other_tenant_data(self, client_tenant_a, client_tenant_b):
        """Tenant B cannot update Tenant A's records."""
        res = await client_tenant_a.post("/api/v1/invoices/", json={...})
        invoice_id = res.json()["id"]

        res = await client_tenant_b.put(f"/api/v1/invoices/{invoice_id}", json={...})
        assert res.status_code in (403, 404), "CRITICAL: Cross-tenant write allowed!"
```

### Auth Bypass Tests
```python
class TestAuthEnforcement:
    async def test_unauthenticated_request_rejected(self, http_client):
        """Every protected endpoint must reject requests without a token."""
        res = await http_client.get("/api/v1/invoices/")
        assert res.status_code in (401, 403), f"Accessible without auth: {res.status_code}"

    async def test_expired_token_rejected(self, http_client):
        """Expired JWT tokens must return 401."""
        expired_token = create_access_token({"sub": "user_id"}, expires_delta=timedelta(seconds=-1))
        res = await http_client.get(
            "/api/v1/invoices/",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert res.status_code == 401

    async def test_viewer_cannot_create(self, viewer_client):
        """Viewer role must not be able to create resources."""
        res = await viewer_client.post("/api/v1/invoices/", json={...})
        assert res.status_code == 403
```

### Input Validation / Injection Tests
```python
class TestInputValidation:
    @pytest.mark.parametrize("payload", [
        {"description": "<script>alert('xss')</script>"},
        {"description": "'; DROP TABLE invoices; --"},
        {"description": "A" * 10000},  # Oversized input
        {"amount": -999},              # Negative amount
        {"amount": 0},                 # Zero amount (VR-01)
    ])
    async def test_malicious_input_rejected(self, auth_client, payload):
        """Malicious or invalid inputs must be rejected with 4xx."""
        res = await auth_client.post("/api/v1/invoices/", json=payload)
        assert res.status_code in (400, 422), f"Malicious input accepted: {payload}"

    async def test_response_does_not_leak_internals(self, auth_client):
        """500 errors must not expose stack traces or internal messages."""
        res = await auth_client.get("/api/v1/invoices/nonexistent-uuid")
        if res.status_code == 500:
            body = res.json()
            assert "Traceback" not in str(body), "Stack trace leaked in response!"
            assert "supabase" not in str(body).lower(), "Internal detail leaked!"
```

### Rate Limiting Test
```python
async def test_login_rate_limit_enforced(http_client):
    """Login endpoint must rate-limit after 5 attempts."""
    for i in range(5):
        await http_client.post("/api/v1/auth/login", json={"email": "x", "password": "x"})

    res = await http_client.post("/api/v1/auth/login", json={"email": "x", "password": "x"})
    assert res.status_code == 429, "Rate limiting not enforced on login!"
```

### Cypress Security Scenarios (E2E)
```typescript
// cypress/e2e/security.cy.ts
describe('Security: Auth enforcement', () => {
  it('redirects unauthenticated users to login', () => {
    cy.clearLocalStorage();
    cy.visit('/invoices');
    cy.url().should('include', '/login');
  });

  it('does not store JWT in localStorage', () => {
    cy.login('user@example.com', 'password');
    cy.window().then(win => {
      const keys = Object.keys(win.localStorage);
      const hasJwt = keys.some(k => win.localStorage.getItem(k)?.startsWith('eyJ'));
      expect(hasJwt).to.be.false;
    });
  });
});
```
