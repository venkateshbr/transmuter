import asyncio
from app.core.database import get_supabase_admin

async def check_archived():
    client = get_supabase_admin()
    res = client.table("initiatives").select("id, name, archived_at, tenant_id").execute()
    for i in res.data:
        print(f"{i['name']} | Archived: {i['archived_at']} | Tenant: {i['tenant_id']}")

if __name__ == "__main__":
    asyncio.run(check_archived())
