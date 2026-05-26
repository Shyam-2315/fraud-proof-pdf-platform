import asyncio
from datetime import UTC, datetime, timedelta

from app.repositories.anonymous_ip_usage_repository import AnonymousIPUsageRepository


class _CapturingCollection:
    def __init__(self) -> None:
        self.selector = None
        self.update_document = None
        self.upsert = None
        self.return_document = None

    async def find_one_and_update(self, selector, update_document, *, upsert, return_document):
        self.selector = selector
        self.update_document = update_document
        self.upsert = upsert
        self.return_document = return_document
        return {"_id": "usage-window"}


def test_upsert_usage_window_uses_safe_operators_without_null_array_entries() -> None:
    collection = _CapturingCollection()

    class RepositoryUnderTest(AnonymousIPUsageRepository):
        def get_collection(self):
            return collection

        async def find_active_windows(self, ip_address: str, now: datetime):
            return []

    now = datetime.now(UTC)
    repository = RepositoryUnderTest()
    asyncio.run(
        repository.upsert_usage_window(
            ip_address="203.0.113.10",
            now=now,
            window_start=now,
            window_end=now + timedelta(hours=24),
            visitor_id="visitor-123",
            anon_id=None,
            fingerprint_hash="fingerprint-123",
            user_agent="PDFCraftTest/1.0",
        )
    )

    assert collection.selector == {
        "ip_address": "203.0.113.10",
        "window_start": now,
    }
    assert collection.upsert is True
    assert collection.update_document["$inc"] == {"anonymous_pdf_count": 1}
    assert collection.update_document["$setOnInsert"] == {
        "ip_address": "203.0.113.10",
        "window_start": now,
        "window_end": now + timedelta(hours=24),
        "first_seen_at": now,
    }
    assert collection.update_document["$set"] == {
        "last_seen_at": now,
        "updated_at": now,
    }
    assert collection.update_document["$addToSet"] == {
        "visitor_ids": "visitor-123",
        "fingerprint_hashes": "fingerprint-123",
        "user_agents": "PDFCraftTest/1.0",
    }
    assert "anon_ids" not in collection.update_document["$addToSet"]


def test_get_usage_count_sums_multiple_active_windows() -> None:
    class RepositoryUnderTest(AnonymousIPUsageRepository):
        async def find_active_windows(self, ip_address: str, now: datetime):
            return [
                {"anonymous_pdf_count": 1},
                {"anonymous_pdf_count": 2},
            ]

    repository = RepositoryUnderTest()
    count = asyncio.run(
        repository.get_usage_count(
            ip_address="203.0.113.20",
            now=datetime.now(UTC),
        )
    )

    assert count == 3
