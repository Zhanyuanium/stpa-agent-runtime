from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any


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
