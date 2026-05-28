from typing import Any

from app.services.ip_intelligence_service import IPIntelligenceService


class IPIntelligence:
    """Compatibility wrapper around the main IP intelligence service."""

    def __init__(
        self,
        service: IPIntelligenceService | None = None,
    ) -> None:
        """
        Initialize the wrapper with an optional underlying service.

        Args:
            service: Optional IP intelligence service implementation.
        """
        self.service = service or IPIntelligenceService()

    async def lookup(self, ip_address: str | None) -> dict[str, Any]:
        """
        Look up risk information for an IP address.

        Args:
            ip_address: IP address to score, or ``None`` when unavailable.

        Returns:
            IP intelligence record describing VPN, proxy, TOR, and risk-score signals.
        """
        return await self.service.check_ip(ip_address)
