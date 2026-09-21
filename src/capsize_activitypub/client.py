from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

from .security import validate_remote_url


ACTIVITY_JSON = 'application/activity+json, application/ld+json; profile="https://www.w3.org/ns/activitystreams"'


class ActivityPubError(RuntimeError):
    """A safe, user-facing ActivityPub client error."""


@dataclass(frozen=True)
class Actor:
    id: str
    name: str
    preferred_username: str
    summary: str
    inbox: str | None
    outbox: str | None
    followers: str | None
    following: str | None
    image: str | None
    domain: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _actor_from_json(payload: dict[str, Any], actor_url: str) -> Actor:
    endpoints = payload.get("endpoints") if isinstance(payload.get("endpoints"), dict) else {}
    image = payload.get("icon") if isinstance(payload.get("icon"), dict) else {}
    image_url = image.get("url") if isinstance(image, dict) else None
    return Actor(
        id=str(payload.get("id") or actor_url),
        name=str(payload.get("name") or payload.get("preferredUsername") or actor_url),
        preferred_username=str(payload.get("preferredUsername") or ""),
        summary=str(payload.get("summary") or ""),
        inbox=str(payload.get("inbox")) if payload.get("inbox") else None,
        outbox=str(payload.get("outbox")) if payload.get("outbox") else None,
        followers=str(payload.get("followers")) if payload.get("followers") else None,
        following=str(payload.get("following")) if payload.get("following") else None,
        image=str(image_url) if image_url else None,
        domain=urlparse(actor_url).hostname or "",
    )


class ActivityPubClient:
    """Read public ActivityPub identities and collections from remote servers."""

    def __init__(self, *, timeout: float = 15.0, resolve_dns: bool = False, transport: httpx.BaseTransport | None = None) -> None:
        self.resolve_dns = resolve_dns
        self.http = httpx.Client(timeout=timeout, follow_redirects=False, transport=transport)

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> "ActivityPubClient":
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.close()

    def _get_json(self, url: str, *, accept: str = ACTIVITY_JSON) -> dict[str, Any]:
        validate_remote_url(url, resolve_dns=self.resolve_dns)
        try:
            response = self.http.get(url, headers={"Accept": accept})
            if 300 <= response.status_code < 400:
                raise ActivityPubError("The remote ActivityPub service returned a redirect.")
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise ActivityPubError("The remote ActivityPub service could not be reached.") from exc
        except ValueError as exc:
            raise ActivityPubError("The remote ActivityPub service returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise ActivityPubError("The remote ActivityPub response was not an object.")
        return payload

    def discover(self, acct: str) -> Actor:
        normalized = acct.strip().lstrip("@")
        match = re.fullmatch(r"([^@\s]+)@([^@\s]+)", normalized)
        if not match:
            raise ActivityPubError("Enter an account as @user@example.com.")
        username, domain = match.groups()
        discovery_url = f"https://{domain}/.well-known/webfinger?{urlencode({'resource': f'acct:{username}@{domain}'})}"
        payload = self._get_json(discovery_url, accept="application/jrd+json, application/json")
        links = payload.get("links")
        if not isinstance(links, list):
            raise ActivityPubError("WebFinger did not return any links.")
        actor_url = next((link.get("href") for link in links if isinstance(link, dict) and link.get("rel") == "self" and isinstance(link.get("href"), str)), None)
        if not actor_url:
            raise ActivityPubError("WebFinger did not return an ActivityPub actor.")
        return self.actor(actor_url)

    def actor(self, actor_url: str) -> Actor:
        payload = self._get_json(actor_url)
        return _actor_from_json(payload, actor_url)

    def collection(self, collection_url: str, *, limit: int = 25) -> list[dict[str, Any]]:
        payload = self._get_json(collection_url)
        items = payload.get("orderedItems") or payload.get("items") or []
        if not isinstance(items, list):
            return []
        return [item for item in items[:limit] if isinstance(item, dict)]

    def public_timeline(self, actor: Actor, *, limit: int = 25) -> list[dict[str, Any]]:
        if not actor.outbox:
            return []
        return self.collection(actor.outbox, limit=limit)
