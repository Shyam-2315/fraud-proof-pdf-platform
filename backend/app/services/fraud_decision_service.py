from typing import Any

from fastapi import Request

from app.config import get_settings
from app.fraud_engine.decision_engine import FraudEngineDecisionService


class FraudDecisionService:
    def __init__(
        self,
        engine: FraudEngineDecisionService | None = None,
    ) -> None:
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
