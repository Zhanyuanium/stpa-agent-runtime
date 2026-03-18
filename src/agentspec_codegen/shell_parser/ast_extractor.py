from __future__ import annotations

from dataclasses import dataclass
import re
import shlex


_SENSITIVE_PATHS = (
    "/etc",
    "/root",
    "/var/log",
    "/usr/bin",
    "/boot",
    "/proc",
)


@dataclass(frozen=True)
class ParsedShellCommand:
    raw: str
    argv: list[str]
    binaries: list[str]
    paths: list[str]
    has_pipe: bool
    has_redirect: bool
    risk_flags: list[str]


def _extract_paths(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t.startswith("/") or t.startswith("./") or t.startswith("../")]


def _detect_risk_flags(tokens: list[str], raw: str) -> list[str]:
    text = raw.lower()
    flags: list[str] = []
    if re.search(r"\brm\b", text) and any(x in tokens for x in ["-rf", "-fr", "--no-preserve-root"]):
        flags.append("destructive_delete")
    if any(tok in ("sudo", "su") for tok in tokens):
        flags.append("privilege_command")
    if any(p in text for p in [".bashrc", ".zshrc", "/etc/profile", "/etc/bash.bashrc"]):
        flags.append("profile_tamper")
    if any(tok in ("curl", "wget", "nc") for tok in tokens):
        flags.append("network_transfer")
    if any(path.startswith(prefix) for path in _extract_paths(tokens) for prefix in _SENSITIVE_PATHS):
        flags.append("sensitive_path")
    return sorted(set(flags))


def extract_command_features(command: str) -> ParsedShellCommand:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        # Keep behavior deterministic even for malformed user text.
        tokens = command.split()
    binaries = [tokens[0]] if tokens else []
    paths = _extract_paths(tokens)
    risk_flags = _detect_risk_flags(tokens, command)
    return ParsedShellCommand(
        raw=command,
        argv=tokens,
        binaries=binaries,
        paths=paths,
        has_pipe="|" in command,
        has_redirect=(">" in command or "<" in command),
        risk_flags=risk_flags,
    )
