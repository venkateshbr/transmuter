from app.core.database import get_supabase_admin
from app.core.config import settings

def check_sync():
    print(f"URL: {settings.supabase_url}")
    client = get_supabase_admin()
    print("Client created. Executing query...")
    try:
        res = client.table("organizations").select("id, name").limit(1).execute()
        print(f"Result: {res.data}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_sync()
