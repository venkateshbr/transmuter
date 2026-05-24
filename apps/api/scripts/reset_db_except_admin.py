import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

# Load env from root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

def reset_db():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not found in .env")
        sys.exit(1)
        
    supabase: Client = create_client(url, key)
    
    # Tables to wipe in reverse order of dependency
    tables_to_wipe = [
        "audit_log",
        "agent_metrics",
        "agent_corrections",
        "agent_audit_log",
        "action_items",
        "meeting_artifacts",
        "meeting_external_events",
        "agenda_items",
        "meeting_sessions",
        "meeting_initiatives",
        "meeting_attendees",
        "meetings",
        "gate_submissions",
        "stage_gates",
        "nudge_log",
        "status_updates",
        "financial_cost_lines",
        "financial_entries",
        "risks",
        "kpi_entries",
        "kpis",
        "milestone_dependencies",
        "milestone_checklist",
        "milestones",
        "initiative_team",
        "initiatives",
        "user_workstreams",
        "workstreams",
        "business_units",
        "financial_cell_assumptions",
        "gate_criteria"
    ]
    
    print("--- Starting Database Reset (Preserving Admin) ---")
    
    for table in tables_to_wipe:
        try:
            print(f"Wiping {table}...")
            # Use a filter that matches all rows (id != '00000000-0000-0000-0000-000000000000')
            supabase.table(table).delete().neq("tenant_id", "00000000-0000-0000-0000-000000000000").execute()
        except Exception as e:
            print(f"  Warning: Could not wipe {table}: {e}")

    # Delete users except admin@ishirock.dev
    print("Cleaning up users...")
    try:
        # 1. Find all platform users except admin
        users_resp = supabase.table("users").select("id, email").neq("email", "admin@ishirock.dev").execute()
        users_to_delete = users_resp.data or []
        
        for u in users_to_delete:
            user_id = u["id"]
            email = u["email"]
            print(f"  Deleting user {email} ({user_id})...")
            
            # Delete from auth (this will cascade to platform users table)
            try:
                supabase.auth.admin.delete_user(user_id)
            except Exception as auth_err:
                print(f"    Warning: Could not delete auth user {email}: {auth_err}")
                # Fallback: delete from platform users table directly if auth delete fails
                supabase.table("users").delete().eq("id", user_id).execute()
                
    except Exception as e:
        print(f"  Error cleaning up users: {e}")

    print("--- Reset Complete ---")
    print("Admin user 'admin@ishirock.dev' and Organization 'Ishirock' have been preserved.")

if __name__ == "__main__":
    reset_db()
