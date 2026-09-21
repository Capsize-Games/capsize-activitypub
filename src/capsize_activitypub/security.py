from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class SSRFError(ValueError):
    """Raised when a remote ActivityPub URL is unsafe to fetch."""


def _disallowed(ip: ipaddress._BaseAddress) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolved_ips(hostname: str, port: int) -> set[ipaddress._BaseAddress]:
    result: set[ipaddress._BaseAddress] = set()
    for family, _kind, _proto, _canonname, sockaddr in socket.getaddrinfo(hostname, port):
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
        try:
            result.add(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            continue
    return result


def validate_remote_url(url: str, *, resolve_dns: bool = False) -> None:
    """Reject unsafe outbound federation URLs before making a request.

    DNS resolution is opt-in because it adds latency and can make local tests
    nondeterministic. Production deployments that fetch arbitrary accounts
    should enable it.
    """

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SSRFError("only http and https URLs are allowed")
    if parsed.username or parsed.password:
        raise SSRFError("URL userinfo is not allowed")
    hostname = parsed.hostname
    if not hostname or hostname.lower() == "localhost":
        raise SSRFError("URL hostname is not allowed")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None:
        if _disallowed(address):
            raise SSRFError("private or local IP addresses are not allowed")
        return
    if not resolve_dns:
        return
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addresses = _resolved_ips(hostname, port)
    except socket.gaierror as exc:
        raise SSRFError("hostname could not be resolved") from exc
    if not addresses or any(_disallowed(address) for address in addresses):
        raise SSRFError("hostname resolves to a private or local address")
