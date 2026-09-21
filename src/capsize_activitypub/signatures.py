from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime, parsedate_to_datetime
from typing import Mapping

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key


_SIGNATURE_KV_RE = re.compile(r'(\w+)="([^"]*)"')


@dataclass(frozen=True)
class ParsedSignature:
    key_id: str
    algorithm: str
    headers: tuple[str, ...]
    signature_b64: str


def parse_signature_header(value: str) -> ParsedSignature | None:
    parts = {match.group(1): match.group(2) for match in _SIGNATURE_KV_RE.finditer(value or "")}
    key_id = parts.get("keyId") or parts.get("keyid")
    signature = parts.get("signature")
    if not key_id or not signature:
        return None
    headers = tuple(item.lower() for item in parts.get("headers", "(request-target) host date").split())
    return ParsedSignature(key_id, parts.get("algorithm", "rsa-sha256"), headers, signature)


def build_signing_string(*, request_target: str, headers: Mapping[str, str], signed_headers: tuple[str, ...]) -> str:
    lines: list[str] = []
    normalized = {key.lower(): value for key, value in headers.items()}
    for name in signed_headers:
        if name == "(request-target)":
            lines.append(f"(request-target): {request_target}")
            continue
        if name not in normalized:
            raise ValueError(f"missing signed header: {name}")
        lines.append(f"{name}: {normalized[name]}")
    return "\n".join(lines)


def digest_sha256(body: bytes) -> str:
    return "sha-256=" + base64.b64encode(hashlib.sha256(body).digest()).decode("ascii")


def sign_request(*, method: str, path_with_query: str, host: str, body: bytes, private_key_pem: str, key_id: str) -> dict[str, str]:
    date_value = format_datetime(datetime.now(timezone.utc), usegmt=True)
    headers: dict[str, str] = {"host": host, "date": date_value}
    signed = ["(request-target)", "host", "date"]
    if body:
        headers["digest"] = digest_sha256(body)
        signed.append("digest")
    signing_string = build_signing_string(
        request_target=f"{method.lower()} {path_with_query}",
        headers=headers,
        signed_headers=tuple(signed),
    )
    private_key = load_pem_private_key(private_key_pem.encode(), password=None)
    signature = private_key.sign(signing_string.encode(), padding.PKCS1v15(), hashes.SHA256())
    result = {
        "Date": date_value,
        "Host": host,
        "Signature": f'keyId="{key_id}",algorithm="rsa-sha256",headers="{" ".join(signed)}",signature="{base64.b64encode(signature).decode()}"',
    }
    if body:
        result["Digest"] = headers["digest"]
    return result


def verify_request(*, method: str, path_with_query: str, headers: Mapping[str, str], body: bytes, public_key_pem: str, max_skew: timedelta = timedelta(hours=12)) -> ParsedSignature:
    normalized = {key.lower(): value for key, value in headers.items()}
    parsed = parse_signature_header(normalized.get("signature", ""))
    if parsed is None:
        raise ValueError("missing or invalid Signature header")
    date_value = normalized.get("date")
    if not date_value:
        raise ValueError("missing Date header")
    try:
        signed_at = parsedate_to_datetime(date_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid Date header") from exc
    if signed_at.tzinfo is None:
        signed_at = signed_at.replace(tzinfo=timezone.utc)
    if abs(datetime.now(timezone.utc) - signed_at) > max_skew:
        raise ValueError("Date header outside allowed window")
    if method.upper() in {"POST", "PUT", "PATCH"} and normalized.get("digest") and normalized["digest"] != digest_sha256(body):
        raise ValueError("Digest mismatch")
    signing_string = build_signing_string(
        request_target=f"{method.lower()} {path_with_query}",
        headers=normalized,
        signed_headers=parsed.headers,
    )
    try:
        signature = base64.b64decode(parsed.signature_b64, validate=True)
        load_pem_public_key(public_key_pem.encode()).verify(signature, signing_string.encode(), padding.PKCS1v15(), hashes.SHA256())
    except Exception as exc:
        raise ValueError("signature verification failed") from exc
    return parsed
