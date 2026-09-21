from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class PublicIdentity:
    """The public identity supplied by the hosted Capsize account service.

    The desktop bridge never becomes the public actor. The hosted account
    service owns the actor document, inbox, account lifecycle, and private
    keys; the bridge only reports the configured endpoints to local clients.
    """

    actor_url: str | None
    inbox_url: str | None
    key_id: str | None
    signed_delivery_ready: bool

    @property
    def configured(self) -> bool:
        return bool(self.actor_url)

    @property
    def domain(self) -> str | None:
        return urlparse(self.actor_url).hostname if self.actor_url else None

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "configured": self.configured,
            "domain": self.domain,
        }


def configured_identity() -> PublicIdentity:
    actor_url = os.environ.get("CAPSIZE_ACTIVITYPUB_ACTOR_URL", "").strip() or None
    inbox_url = os.environ.get("CAPSIZE_ACTIVITYPUB_INBOX_URL", "").strip() or None
    key_id = os.environ.get("CAPSIZE_ACTIVITYPUB_KEY_ID", "").strip() or None
    private_key_file = Path(
        os.environ.get("CAPSIZE_ACTIVITYPUB_PRIVATE_KEY_FILE", "")
    ).expanduser()
    key_available = bool(private_key_file and private_key_file.is_file())
    return PublicIdentity(
        actor_url=actor_url,
        inbox_url=inbox_url,
        key_id=key_id,
        signed_delivery_ready=bool(actor_url and inbox_url and key_id and key_available),
    )
