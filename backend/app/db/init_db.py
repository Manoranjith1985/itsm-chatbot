from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import structlog

from app.core.config import settings
from app.db.models import User, Conversation, FeatureFlag, AuditLog

logger = structlog.get_logger()


async def init_db():
    logger.info("Connecting to MongoDB...")
    client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
    )
    # Verify connection before proceeding
    try:
        await client.admin.command("ping")
        logger.info("MongoDB connection successful")
    except Exception as e:
        logger.error("MongoDB connection failed", error=str(e))
        raise RuntimeError(f"Cannot connect to MongoDB: {e}")

    await init_beanie(
        database=client.get_default_database(),
        document_models=[User, Conversation, FeatureFlag, AuditLog],
    )
    logger.info("Beanie ODM initialised")

    # Seed default feature flags
    if not await FeatureFlag.find_one(FeatureFlag.name == "ai_write_operations"):
        await FeatureFlag(
            name="ai_write_operations",
            enabled=settings.AI_WRITE_OPERATIONS,
            description="Allow AI agent to create/update tickets without manual confirmation",
        ).insert()
        logger.info("Seeded feature flags")
