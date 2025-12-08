"""Utilities for displaying local server addresses."""

from __future__ import annotations

import socket
from typing import List, Optional, Tuple

ServerUrl = Tuple[str, str]


def build_server_urls(port: int, *, path_suffix: str = "", protocol: str = "http") -> List[ServerUrl]:
    """Return URLs that are reachable when binding to 0.0.0.0."""
    suffix = _normalize_path_suffix(path_suffix)
    urls: List[ServerUrl] = [
        ("Localhost", f"{protocol}://localhost:{port}{suffix}"),
        ("127.0.0.1", f"{protocol}://127.0.0.1:{port}{suffix}"),
    ]

    local_network_ip = _detect_local_network_ip()
    if local_network_ip:
        urls.append(("Local network", f"{protocol}://{local_network_ip}:{port}{suffix}"))

    return urls


def _normalize_path_suffix(path_suffix: str) -> str:
    if not path_suffix:
        return ""
    return path_suffix if path_suffix.startswith("/") else f"/{path_suffix}"


def _detect_local_network_ip() -> Optional[str]:
    """Best-effort detection of an externally reachable LAN IP."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            candidate = sock.getsockname()[0]
            if candidate and not candidate.startswith("127."):
                return candidate
    except OSError:
        pass

    try:
        host_info = socket.gethostbyname_ex(socket.gethostname())
        for candidate in host_info[2]:
            if candidate and not candidate.startswith("127."):
                return candidate
    except OSError:
        pass

    return None
