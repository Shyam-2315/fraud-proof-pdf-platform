import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    global _client, _database

    settings = get_settings()
    _client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
    _database = _client[settings.MONGODB_DB_NAME]
    await ping_mongo()
    logger.info("Connected to MongoDB database=%s", settings.MONGODB_DB_NAME)


async def close_mongo_connection() -> None:
    global _client, _database

    if _client is not None:
        _client.close()
        logger.info("Closed MongoDB connection")

    _client = None
    _database = None


def get_database() -> AsyncIOMotorDatabase:
    if _database is None:
        raise RuntimeError("MongoDB is not connected")
    return _database


async def ping_mongo() -> bool:
    if _client is None:
        raise RuntimeError("MongoDB client is not initialized")

    await _client.admin.command("ping")
    return True
