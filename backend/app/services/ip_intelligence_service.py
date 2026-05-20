import json
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.repositories.risk_repository import IPIntelligenceRepository
from app.utils.security import generate_uuid, utc_now


class IPIntelligenceService:
    def __init__(
        self,
        repository: IPIntelligenceRepository | None = None,
    ) -> None:
        self.settings = get_settings()
        self.repository = repository or IPIntelligenceRepository()

    async def check_ip(self, ip_address: str | None) -> dict[str, Any]:
        ip_address = (ip_address or "").strip()
        if not ip_address:
            return self._default_record("", "LOCAL_NONE")

        local_record = self._lookup_local_risk_list(ip_address)
        if local_record is not None:
            return await self.repository.upsert(local_record)

        if not self.settings.ENABLE_IP_INTELLIGENCE:
            return await self.repository.upsert(self._default_record(ip_address, "LOCAL_NONE"))

        return await self.repository.upsert(self._default_record(ip_address, "LOCAL"))

    def _lookup_local_risk_list(self, ip_address: str) -> dict[str, Any] | None:
        path = Path(self.settings.IP_RISK_LIST_PATH)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        raw = data.get(ip_address) if isinstance(data, dict) else None
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raw = {"is_known_abuser": True, "risk_score": 70}

        return {
            **self._default_record(ip_address, "LOCAL_LIST"),
            "is_vpn": bool(raw.get("is_vpn", False)),
            "is_proxy": bool(raw.get("is_proxy", False)),
            "is_tor": bool(raw.get("is_tor", False)),
            "is_datacenter": bool(raw.get("is_datacenter", False)),
            "is_known_abuser": bool(raw.get("is_known_abuser", False)),
            "asn": raw.get("asn"),
            "country": raw.get("country"),
            "risk_score": int(raw.get("risk_score", 70)),
            "provider": raw.get("provider", "LOCAL_LIST"),
        }

    def _default_record(self, ip_address: str, provider: str) -> dict[str, Any]:
        record_id = generate_uuid()
        return {
            "_id": record_id,
            "id": record_id,
            "ip_address": ip_address,
            "is_vpn": False,
            "is_proxy": False,
            "is_tor": False,
            "is_datacenter": False,
            "is_known_abuser": False,
            "asn": None,
            "country": None,
            "risk_score": 0,
            "provider": provider,
            "checked_at": utc_now(),
        }
