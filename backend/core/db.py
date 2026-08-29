import os
from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]


async def create_indexes():
    await db.users.create_index("email", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier")
    await db.analyses.create_index("workspace_id")
    await db.documents.create_index("workspace_id")
    await db.requirements.create_index("analysis_id")
    await db.risks.create_index("analysis_id")
    await db.action_items.create_index("analysis_id")
    await db.notifications.create_index("workspace_id")
    await db.audit_events.create_index("workspace_id")
    await db.opportunities.create_index("workspace_id")
    await db.capacity.create_index("workspace_id")
    await db.portfolio_scenarios.create_index("workspace_id")
