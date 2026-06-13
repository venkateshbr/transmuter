import httpx
from app.core.config import settings

def get_token():
    url = f"{settings.supabase_url}/auth/v1/token?grant_type=password"
    data = {
        "email": "admin@ishirock.dev",
        "password": "Transmuter2026!",
        "gotrue_meta_security": {}
    }
    headers = {
        "apikey": settings.supabase_anon_key,
        "Content-Type": "application/json"
    }
    r = httpx.post(url, json=data, headers=headers)
    return r.json()["access_token"]

def test_api():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    r = httpx.get("http://localhost:8000/initiatives", headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text}")

if __name__ == "__main__":
    test_api()
