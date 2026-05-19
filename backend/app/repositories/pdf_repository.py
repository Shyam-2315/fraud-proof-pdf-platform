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
    logger.info("Ensured generated PDF collection indexes")
