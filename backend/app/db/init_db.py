from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import settings
from app.db.models import User, Conversation, FeatureFlag, AuditLog


async def init_db():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    await init_beanie(
        database=client.get_default_database(),
        document_models=[User, Conversation, FeatureFlag, AuditLog],
    )
    # Seed default feature flags
    if not await FeatureFlag.find_one(FeatureFlag.name == "ai_write_operations"):
        await FeatureFlag(
            name="ai_write_operations",
            enabled=settings.AI_WRITE_OPERATIONS,
            description="Allow AI agent to create/update tickets without manual confirmation",
        ).insert()
