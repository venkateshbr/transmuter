import httpx
from app.core.config import settings

def test_raw_supabase():
    url = f"{settings.supabase_url}/rest/v1/organizations?select=id,name&limit=1"
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}"
    }
    print(f"URL: {url}")
    try:
        r = httpx.get(url, headers=headers, timeout=10.0)
        print(f"Status: {r.status_code}")
        print(f"Result: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_raw_supabase()
