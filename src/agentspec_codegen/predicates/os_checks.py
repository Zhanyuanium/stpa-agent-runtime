from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse


SENSITIVE_PREFIXES = ("/etc", "/root", "/boot", "/proc", "/sys", "/usr/bin", "/var/log")
DEFAULT_TRUSTED_DOMAINS = {"localhost", "127.0.0.1", "intranet.local", "example.com"}


def is_sensitive_path(path: str) -> bool:
    p = path.strip()
    if not p:
        return False
    normalized = p if p.startswith("/") else str(Path(p))
    return any(normalized.startswith(prefix) for prefix in SENSITIVE_PREFIXES)


def is_permission_change_risky(command: str) -> bool:
    lowered = command.lower()
    if not re.search(r"\b(chmod|chown|chgrp)\b", lowered):
        return False
    # Common risky modes: full write/exec to all users.
    return any(token in lowered for token in ["777", "a+w", "a+rwx", "u+s"])


def has_backup_for_target(path: str) -> bool:
    candidate = Path(path)
    if not candidate.name:
        return False
    sibling_backup = candidate.with_suffix(candidate.suffix + ".bak")
    return sibling_backup.exists()


def is_network_target_untrusted(command: str, trusted_domains: set[str] | None = None) -> bool:
    domains = trusted_domains or DEFAULT_TRUSTED_DOMAINS
    urls = re.findall(r"https?://[^\s'\"<>]+", command)
    for url in urls:
        host = (urlparse(url).hostname or "").lower()
        if host and host not in domains:
            return True
    return False
