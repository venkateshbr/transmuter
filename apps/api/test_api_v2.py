import httpx
from app.core.config import settings
from jose import jwt

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
    # Decode WITHOUT verification just to see the payload
    payload = jwt.get_unverified_claims(token)
    print(f"Token Payload: {payload}")
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = httpx.get("http://localhost:8000/initiatives", headers=headers, timeout=5.0)
        print(f"Status: {r.status_code}")
        print(f"Body: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
