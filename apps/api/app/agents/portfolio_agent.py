from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.database import get_supabase_admin
from uuid import UUID

# Configure OpenAI client for OpenRouter
client = AsyncOpenAI(
    base_url=settings.openrouter_base_url,
    api_key=settings.openrouter_api_key,
)

provider = OpenAIProvider(openai_client=client)
model = OpenAIChatModel(
    settings.default_model,
    provider=provider,
)

# Define the agent
portfolio_agent = Agent(
    model,
    deps_type=UUID,
    system_prompt=(
        "You are Transmuter AI, a specialized assistant for Transformation Offices. "
        "You have access to the portfolio of transformation initiatives, milestones, and risks. "
        "Answer questions accurately based on the data provided by your tools. "
        "Maintain a professional, executive tone. Use purple-themed metaphors if appropriate."
    )
)

@portfolio_agent.tool
async def get_portfolio_summary(ctx: RunContext[UUID]) -> dict:
    """Get a high-level summary of the entire portfolio."""
    client = get_supabase_admin()
    tid = str(ctx.deps)
    inits = client.table("initiatives").select("id, rag_status, stage").eq("tenant_id", tid).execute()
    return {
        "total_initiatives": len(inits.data),
        "at_risk": len([i for i in inits.data if i["rag_status"] == "red"]),
        "stages": {
            "scoping": len([i for i in inits.data if i["stage"] == "scoping"]),
            "in_progress": len([i for i in inits.data if i["stage"] == "in_progress"]),
            "complete": len([i for i in inits.data if i["stage"] == "complete"]),
        }
    }

@portfolio_agent.tool
async def get_at_risk_initiatives(ctx: RunContext[UUID]) -> list[dict]:
    """List initiatives that are currently marked as RED or AMBER."""
    client = get_supabase_admin()
    tid = str(ctx.deps)
    res = client.table("initiatives").select("initiative_code, name, rag_status").eq("tenant_id", tid).in_("rag_status", ["red", "amber"]).execute()
    return res.data or []
