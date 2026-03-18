from __future__ import annotations

import contextvars
import json
import subprocess
from dataclasses import dataclass
from typing import Any

_shellcheck_for_audit: contextvars.ContextVar[tuple[str, "ShellcheckResult"] | None] = (
    contextvars.ContextVar("shellcheck_for_audit", default=None)
)


@dataclass(frozen=True)
class ShellcheckResult:
    available: bool
    diagnostics: list[dict[str, Any]]
    stderr: str = ""


def run_shellcheck(command_text: str) -> ShellcheckResult:
    """
    Run shellcheck if available. If unavailable, return a graceful fallback result.
    """
    cmd = ["shellcheck", "--format", "json", "-"]
    try:
        proc = subprocess.run(
            cmd,
            input=command_text,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return ShellcheckResult(available=False, diagnostics=[], stderr="shellcheck not found")

    output = proc.stdout.strip()
    if not output:
        return ShellcheckResult(available=True, diagnostics=[], stderr=proc.stderr.strip())
    try:
        payload = json.loads(output)
        if isinstance(payload, list):
            return ShellcheckResult(available=True, diagnostics=payload, stderr=proc.stderr.strip())
        return ShellcheckResult(available=True, diagnostics=[], stderr=proc.stderr.strip())
    except json.JSONDecodeError:
        return ShellcheckResult(available=True, diagnostics=[], stderr=proc.stderr.strip())


def ensure_shellcheck_run(command_text: str) -> ShellcheckResult:
    """
    Run shellcheck if not already cached for this command. Store result for audit.
    Call from shell predicate/parsing layer. Graceful fallback when shellcheck unavailable.
    """
    if not command_text or not command_text.strip():
        return ShellcheckResult(available=False, diagnostics=[], stderr="")
    cached = _shellcheck_for_audit.get()
    if cached is not None and cached[0] == command_text:
        return cached[1]
    result = run_shellcheck(command_text)
    _shellcheck_for_audit.set((command_text, result))
    return result


def get_shellcheck_summary_for_audit() -> dict[str, Any] | None:
    """
    Return serializable shellcheck summary for runtime audit, then clear the stored result.
    """
    cached = _shellcheck_for_audit.get()
    _shellcheck_for_audit.set(None)
    if cached is None:
        return None
    command_text, result = cached
    level_counts: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
    for d in result.diagnostics:
        level = d.get("level", "info")
        if level in level_counts:
            level_counts[level] += 1
    return {
        "command_text": command_text,
        "available": result.available,
        "diagnostic_count": len(result.diagnostics),
        "level_counts": level_counts,
        "stderr": result.stderr or "",
        "diagnostics": result.diagnostics,
    }
