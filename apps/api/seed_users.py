import uuid
from app.core.database import get_supabase_admin

def seed():
    client = get_supabase_admin()
    
    # Get first organization
    orgs = client.table("organizations").select("*").limit(1).execute()
    if not orgs.data:
        print("No organizations found. Please run seed_data first.")
        return
        
    tid = orgs.data[0]["id"]
    
    users = [
        {"email": "vishwa@ishirock.dev", "display_name": "Vishwa Vish", "role": "transformation_office", "title": "VP Transformation"},
        {"email": "aksha@ishirock.dev", "display_name": "Aksha Rock", "role": "initiative_owner", "title": "Digital Ops Lead"},
        {"email": "mark@ishirock.dev", "display_name": "Mark Spencer", "role": "workstream_lead", "title": "Financial Controller"}
    ]
    
    for u in users:
        payload = {**u, "tenant_id": tid, "id": str(uuid.uuid4()), "status": "active"}
        client.table("users").upsert(payload).execute()
        print(f"Seeded user: {u['display_name']}")

if __name__ == "__main__":
    seed()
