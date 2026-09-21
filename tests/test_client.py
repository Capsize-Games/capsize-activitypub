from __future__ import annotations

import httpx

from capsize_activitypub.client import ActivityPubClient, ActivityPubError
from capsize_activitypub.security import SSRFError, validate_remote_url


def test_discover_fetches_actor_and_outbox() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/webfinger":
            return httpx.Response(200, json={"links": [{"rel": "self", "href": "https://example.test/users/alice"}]})
        if request.url.path == "/users/alice":
            return httpx.Response(200, json={"id": str(request.url), "type": "Person", "preferredUsername": "alice", "outbox": "https://example.test/users/alice/outbox"})
        if request.url.path == "/users/alice/outbox":
            return httpx.Response(200, json={"type": "OrderedCollection", "orderedItems": [{"type": "Create", "id": "https://example.test/activities/1"}]})
        return httpx.Response(404)

    with ActivityPubClient(transport=httpx.MockTransport(handler)) as client:
        actor = client.discover("@alice@example.test")
        assert actor.preferred_username == "alice"
        assert client.public_timeline(actor)[0]["type"] == "Create"


def test_invalid_account_is_rejected() -> None:
    with ActivityPubClient(transport=httpx.MockTransport(lambda _request: httpx.Response(200))) as client:
        try:
            client.discover("not-an-account")
        except ActivityPubError as exc:
            assert "@user@example.com" in str(exc)
        else:
            raise AssertionError("invalid account was accepted")


def test_private_urls_are_rejected() -> None:
    for url in ("http://127.0.0.1/users/alice", "http://10.0.0.2/users/alice", "file:///tmp/activity.json"):
        try:
            validate_remote_url(url)
        except SSRFError:
            pass
        else:
            raise AssertionError(f"unsafe URL was accepted: {url}")
