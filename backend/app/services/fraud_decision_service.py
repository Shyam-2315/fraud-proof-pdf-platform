from typing import Any

from fastapi import Request

from app.config import get_settings
from app.fraud_engine.decision_engine import FraudEngineDecisionService


class FraudDecisionService:
    """Facade around the fraud engine decision pipeline."""

    def __init__(
        self,
        engine: FraudEngineDecisionService | None = None,
    ) -> None:
        """
        Initialize the fraud decision service.

        Args:
            engine: Optional fraud engine implementation to delegate to.
        """
        self.settings = get_settings()
        self.engine = engine or FraudEngineDecisionService()

    async def decide(
        self,
        visitor: dict[str, Any],
        request: Request | None,
        action_type: str,
        user: dict[str, Any] | None = None,
        payload: Any | None = None,
        context: dict[str, Any] | None = None,
        normal_flow: bool = False,
    ) -> dict[str, Any]:
        """
        Evaluate a visitor action through the fraud engine and return a serializable decision.

        Args:
            visitor: Visitor document being scored.
            request: Incoming request associated with the action, when available.
            action_type: Logical action type such as identify or PDF generation.
            user: Optional authenticated user performing the action.
            payload: Optional request payload contributing fraud features.
            context: Optional extra fraud signals computed by surrounding services.
            normal_flow: Whether the action occurred in a known-good customer flow.

        Returns:
            Dictionary representation of the fraud engine decision.
        """
        result = await self.engine.decide(
            visitor=visitor,
            request=request,
            action_type=action_type,
            user=user,
            payload=payload,
            context=context,
            normal_flow=normal_flow,
        )
        return result.as_dict()
