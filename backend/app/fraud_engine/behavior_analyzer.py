from datetime import timedelta
from typing import Any

from app.models.behavior import BehaviorEventType
from app.repositories.behavior_repository import BehaviorEventRepository
from app.utils.security import utc_now


class BehaviorAnalyzer:
    """Analyze stored visitor behavior events for fraud-related timing signals."""

    def __init__(self, repository: BehaviorEventRepository | None = None) -> None:
        """
        Initialize the behavior analyzer.

        Args:
            repository: Optional repository used to load behavior events.
        """
        self.repository = repository or BehaviorEventRepository()

    async def analyze(self, visitor_id: str, content_hash: str | None = None) -> dict[str, Any]:
        """
        Build derived behavior features for a visitor.

        Args:
            visitor_id: Visitor whose behavior history should be analyzed.
            content_hash: Optional content hash used to detect repeated generation attempts.

        Returns:
            Derived timing, repetition, and interaction metrics used by fraud scoring.
        """
        now = utc_now()
        events = await self.repository.list_by_visitor_id(visitor_id, limit=200)
        page_views = [e for e in events if e.get("event_type") == BehaviorEventType.PAGE_VIEW.value]
        generate_clicks = [
            e for e in events if e.get("event_type") == BehaviorEventType.GENERATE_CLICKED.value
        ]
        pdf_generated = [e for e in events if e.get("event_type") == BehaviorEventType.PDF_GENERATED.value]
        first_event = min((e.get("created_at") for e in events if e.get("created_at")), default=None)
        first_generate = min((e.get("created_at") for e in generate_clicks if e.get("created_at")), default=None)
        recent_generate_clicks = await self.repository.count_by_visitor(
            visitor_id,
            event_type=BehaviorEventType.GENERATE_CLICKED.value,
            since=now - timedelta(seconds=30),
        )
        repeated_content = await self.repository.count_same_content(
            visitor_id,
            content_hash,
            since=now - timedelta(hours=1),
        )
        time_to_first_generate = 999999.0
        if first_event is not None and first_generate is not None:
            time_to_first_generate = max((first_generate - first_event).total_seconds(), 0.0)

        generation_times = sorted(e.get("created_at") for e in pdf_generated if e.get("created_at"))
        intervals = [
            (generation_times[index] - generation_times[index - 1]).total_seconds()
            for index in range(1, len(generation_times))
        ]
        return {
            "time_to_first_generate_seconds": time_to_first_generate,
            "avg_time_between_generations": sum(intervals) / len(intervals) if intervals else 999999.0,
            "same_content_repeated_count": repeated_content,
            "api_only_usage_pattern": 1 if not events else 0,
            "page_views_before_generate": len(page_views),
            "generate_clicks_before_success": len(generate_clicks),
            "recent_generate_clicks_30s": recent_generate_clicks,
        }
