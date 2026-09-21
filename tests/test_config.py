from __future__ import annotations

from pathlib import Path

from capsize_activitypub.config import configured_identity


def test_identity_reports_hosted_actor_without_exposing_private_key(monkeypatch, tmp_path: Path) -> None:
    key_file = tmp_path / "actor.pem"
    key_file.write_text("private", encoding="utf-8")
    monkeypatch.setenv("CAPSIZE_ACTIVITYPUB_ACTOR_URL", "https://capsize.online/ap/users/joe")
    monkeypatch.setenv("CAPSIZE_ACTIVITYPUB_INBOX_URL", "https://capsize.online/ap/users/joe/inbox")
    monkeypatch.setenv("CAPSIZE_ACTIVITYPUB_KEY_ID", "https://capsize.online/ap/users/joe#main-key")
    monkeypatch.setenv("CAPSIZE_ACTIVITYPUB_PRIVATE_KEY_FILE", str(key_file))

    identity = configured_identity().as_dict()

    assert identity["configured"] is True
    assert identity["domain"] == "capsize.online"
    assert identity["signed_delivery_ready"] is True
    assert "private" not in identity


def test_identity_is_unconfigured_by_default(monkeypatch) -> None:
    for name in (
        "CAPSIZE_ACTIVITYPUB_ACTOR_URL",
        "CAPSIZE_ACTIVITYPUB_INBOX_URL",
        "CAPSIZE_ACTIVITYPUB_KEY_ID",
        "CAPSIZE_ACTIVITYPUB_PRIVATE_KEY_FILE",
    ):
        monkeypatch.delenv(name, raising=False)

    identity = configured_identity().as_dict()

    assert identity["configured"] is False
    assert identity["actor_url"] is None
    assert identity["signed_delivery_ready"] is False
