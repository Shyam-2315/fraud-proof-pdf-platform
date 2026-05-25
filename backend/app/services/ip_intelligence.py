from typing import Any

from app.services.ip_intelligence_service import IPIntelligenceService


class IPIntelligence:
    def __init__(
        self,
        service: IPIntelligenceService | None = None,
    ) -> None:
        self.service = service or IPIntelligenceService()

    async def lookup(self, ip_address: str | None) -> dict[str, Any]:
        return await self.service.check_ip(ip_address)
