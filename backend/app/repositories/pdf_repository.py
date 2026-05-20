import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from app.models.pdf import GENERATED_PDF_COLLECTION

logger = logging.getLogger(__name__)


class PDFRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[GENERATED_PDF_COLLECTION]

    async def create_pdf_record(self, pdf_data: dict[str, Any]) -> dict[str, Any]:
        await self.get_collection().insert_one(pdf_data)
        return pdf_data

    async def get_by_id(self, pdf_id: str) -> dict[str, Any] | None:
        if not pdf_id:
            return None
        return await self.get_collection().find_one({"_id": pdf_id})

    async def list_by_visitor_id(
        self,
        visitor_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        cursor = (
            self.get_collection()
            .find({"visitor_id": visitor_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def list_by_user_id(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        cursor = (
            self.get_collection()
            .find({"user_id": user_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def attach_visitor_pdfs_to_user(
        self,
        visitor_id: str,
        user_id: str,
    ) -> int:
        result = await self.get_collection().update_many(
            {
                "visitor_id": visitor_id,
                "$or": [{"user_id": None}, {"user_id": {"$exists": False}}],
            },
            {
                "$set": {
                    "user_id": user_id,
                    "owner_type": "USER",
                    "generation_type": "AUTHENTICATED",
                }
            },
        )
        return int(result.modified_count)

    async def list_by_user_or_linked_visitors(
        self,
        user_id: str,
        visitor_ids: list[str],
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = {
            "$or": [
                {"user_id": user_id},
                {"visitor_id": {"$in": visitor_ids}},
            ]
        }
        cursor = (
            self.get_collection()
            .find(query)
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def list_all(self, limit: int = 50) -> list[dict[str, Any]]:
        cursor = self.get_collection().find({}).sort("created_at", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)

    async def count_pdfs(self, filter_query: dict[str, Any] | None = None) -> int:
        return await self.get_collection().count_documents(filter_query or {})


async def ensure_pdf_indexes() -> None:
    collection = PDFRepository().get_collection()
    await collection.create_index(
        [("visitor_id", ASCENDING)],
        name="idx_generated_pdfs_visitor_id",
    )
    await collection.create_index(
        [("user_id", ASCENDING)],
        name="idx_generated_pdfs_user_id",
    )
    await collection.create_index(
        [("created_at", DESCENDING)],
        name="idx_generated_pdfs_created_at",
    )
    await collection.create_index(
        [("generation_type", ASCENDING)],
        name="idx_generated_pdfs_generation_type",
    )
    await collection.create_index(
        [("owner_type", ASCENDING)],
        name="idx_generated_pdfs_owner_type",
    )
    logger.info("Ensured generated PDF collection indexes")
