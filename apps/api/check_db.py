import asyncio
from app.core.database import get_supabase_admin

async def check_db():
    client = get_supabase_admin()
    
    # Check tenants
    tenants = client.table("organizations").select("id, name").execute()
    print(f"Tenants: {tenants.data}")
    
    # Check initiatives
    inits = client.table("initiatives").select("id, name, tenant_id").execute()
    print(f"Total Initiatives: {len(inits.data)}")
    for i in inits.data:
        print(f" - {i['name']} ({i['tenant_id']})")
        
    # Check users
    users = client.table("users").select("id, email, tenant_id").execute()
    print(f"Total Users: {len(users.data)}")
    for u in users.data:
        print(f" - {u['email']} ({u['tenant_id']})")

if __name__ == "__main__":
    asyncio.run(check_db())
