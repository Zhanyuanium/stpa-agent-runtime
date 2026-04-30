"""Shell-aware predicate implementations.

Each grammar-compatible predicate exported here delegates to the Python-domain
implementation in :mod:`rules.manual.pythonrepl` first and then ORs in
shell-specific detection logic. This union pattern preserves the Python-domain
behaviour (so the code-domain experiments are unaffected) while letting the
same predicate token also fire on bash/shell command text.

Performance note: this module maintains two per-batch caches to avoid redundant
``shlex.split`` + risk-flag extraction and repeated shellcheck invocations.
Call ``clear_command_caches()`` at the start of each new case batch.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from agentspec_codegen.predicates.os_checks import (
    has_backup_for_target,
    is_network_target_untrusted,
    is_permission_change_risky,
    is_sensitive_path,
)
from agentspec_codegen.shell_parser import (
    ParsedShellCommand,
    extract_command_features,
    ensure_shellcheck_run,
)
from rules.manual import pythonrepl as _py

# ---------------------------------------------------------------------------
# Per-batch caches – cleared via clear_command_caches() between cases
# ---------------------------------------------------------------------------
_command_feature_cache: dict[str, ParsedShellCommand] = {}
_shellcheck_done: set[str] = set()
_shell_text_hint_cache: dict[str, bool] = {}


def clear_command_caches() -> None:
    """Clear the per-command feature and shellcheck caches.

    Call this at the beginning of each new evaluation case so that
    predicates always see fresh state for a new command text.
    """
    _command_feature_cache.clear()
    _shellcheck_done.clear()
    _shell_text_hint_cache.clear()


def _shell_text_hint(text: str) -> bool:
    """Cached :func:`_is_shell_text` result for a command string."""
    if text not in _shell_text_hint_cache:
        _shell_text_hint_cache[text] = _is_shell_text(text)
    return _shell_text_hint_cache[text]


def _shell_skip_python_delegate(text: str) -> bool:
    """If True, skip calling Python-domain predicates (shell microbench baseline: set ``AGENTSPEC_SHELL_SHORTCIRCUIT_PY=0``)."""
    if os.environ.get("AGENTSPEC_SHELL_SHORTCIRCUIT_PY", "1").lower() in ("0", "false", "no"):
        return False
    return _shell_text_hint(text)


def _as_text(tool_input: object) -> str:
    if tool_input is None:
        return ""
    return str(tool_input)


def _get_cached_features(cmd: str) -> ParsedShellCommand:
    """Return parsed shell features, computing them once per unique command."""
    if cmd not in _command_feature_cache:
        _command_feature_cache[cmd] = extract_command_features(cmd)
    return _command_feature_cache[cmd]


def _ensure_shellcheck(cmd: str) -> None:
    """Trigger shellcheck at most once per unique command text per batch."""
    if cmd and cmd not in _shellcheck_done:
        ensure_shellcheck_run(cmd)
        _shellcheck_done.add(cmd)


# ---------------------------------------------------------------------------
# Helper shell-only checks (kept private). They are invoked by the predicate
# overrides defined further below.
# ---------------------------------------------------------------------------

def _is_shell_text(text: str) -> bool:
    """Heuristically decide whether the input looks like a shell command."""
    indicators = ("#!/bin/bash", "#!/bin/sh", "function ", "#!/usr/bin/env bash")
    if any(text.startswith(indicator) for indicator in indicators):
        return True
    bash_signals = re.search(r"\b(bash|sh|zsh|chmod|chown|systemctl|service|wget|curl|cp|mv|rm)\b", text)
    return bool(bash_signals) and "import " not in text and "def " not in text


def _shell_post_request(text: str) -> bool:
    if re.search(r"curl\b[^|;\n]*(-X\s*POST|--data|--data-raw|--data-urlencode|--data-binary)", text, re.IGNORECASE):
        return True
    if re.search(r"wget\b[^|;\n]*--post-(data|file)", text, re.IGNORECASE):
        return True
    if re.search(r"\bnc\b[^|;\n]*-q", text, re.IGNORECASE):
        return True
    return False


def _shell_external_url(text: str) -> bool:
    if not re.search(r"\b(curl|wget|nc|scp|ftp|sftp)\b", text, re.IGNORECASE):
        return False
    pattern = re.compile(r"https?://([\w\-\.]+)")
    matches = pattern.findall(text)
    if not matches:
        return False
    whitelist = {"google.com", "localhost", "127.0.0.1"}
    for host in matches:
        if any(safe in host for safe in whitelist):
            continue
        return True
    return False


def _shell_encoding(text: str) -> bool:
    if re.search(r"\bbase64\b", text, re.IGNORECASE):
        return True
    if re.search(r"\bxxd\s+-p\b", text, re.IGNORECASE):
        return True
    if re.search(r"\b(uuencode|uudecode)\b", text, re.IGNORECASE):
        return True
    return False


def _shell_copy(text: str) -> bool:
    return bool(re.search(r"\b(cp|scp|rsync)\b\s", text))


def _shell_read(text: str) -> bool:
    return bool(re.search(r"\b(cat|head|tail|less|more|awk\s+|sed\s+-n)\b", text))


def _shell_write(text: str) -> bool:
    if ">>" in text or re.search(r"(?<!2)>(?!\d)", text):
        return True
    if re.search(r"\b(tee|dd\s+if=)\b", text):
        return True
    return False


def _shell_list_directory(text: str) -> bool:
    return bool(re.search(r"\b(ls|find|tree|dir|stat)\b", text))


def _shell_execute_script(text: str) -> bool:
    if re.search(r"\b(eval|source|bash|sh|zsh)\b\s", text):
        return True
    if re.search(r"\.\s*/[\w\./-]+\.sh\b", text):
        return True
    return False


def _shell_side_channel(text: str) -> bool:
    if re.search(r"\bsleep\s+\d+", text):
        return True
    if re.search(r"\bread\b\s+-t\s*\d+", text):
        return True
    return False


def _shell_crypto(text: str) -> bool:
    weak_algorithms = (
        r"\b(md5sum|sha1sum)\b",
        r"openssl\s+(md5|sha1|rc4|des|md4)",
        r"openssl\s+enc\b[^|;\n]*-(des|rc4|aes-128-ecb)",
    )
    if any(re.search(p, text, re.IGNORECASE) for p in weak_algorithms):
        return True
    if re.search(r"password\s*=\s*['\"]?[^\s'\";]+", text, re.IGNORECASE):
        return True
    return False


def _shell_process_management(text: str) -> bool:
    if re.search(r"\bkill\b[^|;\n]*-9", text):
        return True
    if re.search(r"\bpkill\b[^|;\n]*-f", text):
        return True
    if re.search(r"\bkillall\b", text):
        return True
    return False


def _shell_unsafe_deserialization(text: str) -> bool:
    if re.search(r"\beval\b\s+", text):
        return True
    if re.search(r"\bsource\b\s+", text):
        return True
    if re.search(r"<<<\s*\$\(", text):
        return True
    if re.search(r"\$\(.*\)\s*\|\s*(bash|sh)", text):
        return True
    return False


def _shell_duplicate_keys(text: str) -> bool:
    """Detect declare -A associative arrays with duplicate keys at the source level."""
    matches = re.findall(r"\(((?:\s*\[\s*[^\]]+\s*\]\s*=\s*[^\s\)]+)+)\s*\)", text)
    for body in matches:
        keys = re.findall(r"\[\s*([^\]]+?)\s*\]\s*=", body)
        normalised = [k.strip().strip("'\"") for k in keys]
        if len(normalised) != len(set(normalised)):
            return True
    array_keys: dict[str, set[str]] = {}
    duplicate_pairs = re.findall(r"^\s*(\w+)\s*\[\s*['\"]?([^\]'\"]+)['\"]?\s*\]\s*=", text, re.MULTILINE)
    for arr, key in duplicate_pairs:
        bucket = array_keys.setdefault(arr, set())
        if key in bucket:
            return True
        bucket.add(key)
    return False


def _shell_prng_buggy(text: str) -> bool:
    if re.search(r"\$RANDOM", text):
        return True
    if re.search(r"\bRANDOM\s*=\s*\d", text):
        return True
    return False


def _shell_amplification(text: str) -> bool:
    if re.search(r"\*\s*10000", text):
        return True
    if re.search(r"for\s+\w+\s+in\s+\$\(seq\s+1\s+\d{4,}\)", text):
        return True
    return False


def _shell_buggy_ip_validation(text: str) -> bool:
    if not re.search(r"(ip\s*=|validate.*ip|ipv4|ip_addr|inet_aton)", text, re.IGNORECASE):
        return False
    if re.search(r"\\d\+|\[0-9\]\+", text) and not re.search(r"\^", text):
        return True
    return False


def _iter_bash_case_blocks(text: str):
    """Yield each top-level ``case ... esac`` span (inclusive) in source order."""
    i = 0
    n = len(text)
    while i < n:
        m = re.search(r"\bcase\b", text[i:])
        if not m:
            break
        block_start = i + m.start()
        j = i + m.end()
        depth = 1
        while j < n:
            sub = text[j:]
            mc = re.search(r"\bcase\b", sub)
            me = re.search(r"\besac\b", sub)
            if me is None:
                return
            esac_rel_start = j + me.start()
            case_rel_start = j + mc.start() if mc else None
            if case_rel_start is not None and case_rel_start < esac_rel_start:
                depth += 1
                j = j + mc.end()
            else:
                depth -= 1
                j = j + me.end()
                if depth == 0:
                    yield text[block_start:j]
                    break
        else:
            break
        i = j


def _case_inner_from_block(block: str) -> str | None:
    """Return the branch region between the first ``in`` and the final ``esac``."""
    esacs = list(re.finditer(r"\besac\b", block))
    if not esacs:
        return None
    inner_end = esacs[-1].start()
    in_m = re.search(r"\bin\b", block)
    if not in_m or in_m.end() > inner_end:
        return None
    return block[in_m.end() : inner_end]


def _strip_nested_case_esac(inner: str) -> str:
    """Replace nested ``case ... esac`` regions with spaces so outer ``*)`` is visible."""
    parts: list[str] = []
    i = 0
    while i < len(inner):
        m = re.search(r"\bcase\b", inner[i:])
        if not m:
            parts.append(inner[i:])
            break
        start = i + m.start()
        parts.append(inner[i:start])
        j = start + m.end()
        depth = 1
        while j < len(inner):
            sub = inner[j:]
            mc = re.search(r"\bcase\b", sub)
            me = re.search(r"\besac\b", sub)
            if me is None:
                parts.append(inner[start:])
                return "".join(parts)
            esac_rel_start = j + me.start()
            case_rel_start = j + mc.start() if mc else None
            if case_rel_start is not None and case_rel_start < esac_rel_start:
                depth += 1
                j = j + mc.end()
            else:
                depth -= 1
                j = j + me.end()
                if depth == 0:
                    parts.append(" ")
                    i = j
                    break
        else:
            parts.append(inner[start:])
            break
    return "".join(parts)


def _has_bash_case_catch_all(stripped: str) -> bool:
    """True if a branch uses ``*`` as a pattern alternative before ``)``."""
    return bool(re.search(r"(?:^|[\n;|])\s*\*+\s*\)", stripped, re.MULTILINE))


def _shell_missing_default_case(text: str) -> bool:
    """Detect ``case`` / ``esac`` without a catch-all ``*)`` branch (bash analogue of Python match-default)."""
    if not re.search(r"\bcase\b", text):
        return False
    for block in _iter_bash_case_blocks(text):
        inner = _case_inner_from_block(block)
        if inner is None:
            continue
        flattened = _strip_nested_case_esac(inner)
        if not _has_bash_case_catch_all(flattened):
            return True
    return False


# ---------------------------------------------------------------------------
# Standalone shell-only predicates that do not have a Python counterpart.
# These are intentionally kept; they are not parser tokens but are usable
# from rule_compiler defaults.
# ---------------------------------------------------------------------------

def shell_is_destructive_delete(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    _ensure_shellcheck(cmd)
    parsed = _get_cached_features(cmd)
    return "destructive_delete" in parsed.risk_flags


def shell_touches_sensitive_path(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    _ensure_shellcheck(cmd)
    parsed = _get_cached_features(cmd)
    return any(is_sensitive_path(path) for path in parsed.paths)


def shell_requires_privilege(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    _ensure_shellcheck(cmd)
    return bool(re.search(r"\b(sudo|su)\b", cmd.lower()))


def shell_missing_change_ticket(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    _ensure_shellcheck(cmd)
    prompt = _as_text(user_input)
    return "chg-" not in prompt.lower()


def shell_modifies_profile_startup(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    _ensure_shellcheck(cmd)
    cmd = cmd.lower()
    profile_markers = [".bashrc", ".zshrc", "/etc/profile", "/etc/bash.bashrc"]
    return any(marker in cmd for marker in profile_markers)


def shell_untrusted_network_target(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    _ensure_shellcheck(cmd)
    return is_network_target_untrusted(cmd)


def shell_permission_change_risky(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    _ensure_shellcheck(cmd)
    return is_permission_change_risky(cmd)


def shell_target_has_backup(user_input, tool_input, intermediate_steps) -> bool:
    cmd = _as_text(tool_input)
    _ensure_shellcheck(cmd)
    parsed = _get_cached_features(cmd)
    for path in parsed.paths:
        if has_backup_for_target(path):
            return True
    return False


# ---------------------------------------------------------------------------
# Grammar-compatible predicate overrides. Each delegates to the Python-domain
# implementation first to preserve code-domain behaviour, then ORs in the
# shell-aware logic above.
# ---------------------------------------------------------------------------

def submit_post_request(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.submit_post_request(user_input, text, intermediate_steps):
        return True
    return _shell_post_request(text)


def request_untrusted_source(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.request_untrusted_source(user_input, text, intermediate_steps):
        return True
    return _shell_external_url(text)


def encode_data(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.encode_data(user_input, text, intermediate_steps):
        return True
    return _shell_encoding(text)


def copy_file(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.copy_file(user_input, text, intermediate_steps):
        return True
    return _shell_copy(text)


def read_io(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.read_io(user_input, text, intermediate_steps):
        return True
    return _shell_read(text)


def write_to_io(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.write_to_io(user_input, text, intermediate_steps):
        return True
    return _shell_write(text)


def list_directory(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.list_directory(user_input, text, intermediate_steps):
        return True
    return _shell_list_directory(text)


def execute_script(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.execute_script(user_input, text, intermediate_steps):
        return True
    return _shell_execute_script(text)


def destuctive_os_inst(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.destuctive_os_inst(user_input, text, intermediate_steps):
        return True
    if re.search(r"\b(rm|unlink)\b", text):
        return True
    return shell_is_destructive_delete(user_input, text, intermediate_steps)


def involve_system_file(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.involve_system_file(user_input, text, intermediate_steps):
        return True
    parsed = _get_cached_features(text)
    return any(is_sensitive_path(path) for path in parsed.paths)


def involve_system_dir(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.involve_system_dir(user_input, text, intermediate_steps):
        return True
    parsed = _get_cached_features(text)
    return any(is_sensitive_path(path) for path in parsed.paths)


def is_improper_execution_privilege_code(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.is_improper_execution_privilege_code(user_input, text, intermediate_steps):
        return True
    return shell_requires_privilege(user_input, text, intermediate_steps) or shell_permission_change_risky(
        user_input, text, intermediate_steps
    )


def involve_bash_rc(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.involve_bash_rc(user_input, text, intermediate_steps):
        return True
    return shell_modifies_profile_startup(user_input, text, intermediate_steps)


def is_side_channel_vulnerable(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.is_side_channel_vulnerable(user_input, text, intermediate_steps):
        return True
    return _shell_side_channel(text)


def is_crypto_buggy(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.is_crypto_buggy(user_input, text, intermediate_steps):
        return True
    return _shell_crypto(text)


def is_buggy_process_management(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.is_buggy_process_management(user_input, text, intermediate_steps):
        return True
    return _shell_process_management(text)


def detect_unsafe_deserialization(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.detect_unsafe_deserialization(user_input, text, intermediate_steps):
        return True
    return _shell_unsafe_deserialization(text)


def detect_duplicate_keys_in_code(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.detect_duplicate_keys_in_code(user_input, text, intermediate_steps):
        return True
    return _shell_duplicate_keys(text)


def is_prng_buggy(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.is_prng_buggy(user_input, text, intermediate_steps):
        return True
    return _shell_prng_buggy(text)


def is_amplification(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.is_amplification(user_input, text, intermediate_steps):
        return True
    return _shell_amplification(text)


def is_buggy_ip_validation_code(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.is_buggy_ip_validation_code(user_input, text, intermediate_steps):
        return True
    return _shell_buggy_ip_validation(text)


def detect_missing_default_case(user_input, tool_input, intermediate_steps) -> bool:
    text = _as_text(tool_input)
    _ensure_shellcheck(text)
    if not _shell_skip_python_delegate(text) and _py.detect_missing_default_case(user_input, text, intermediate_steps):
        return True
    return _shell_missing_default_case(text)


shell_predicates = {
    # standalone shell-only predicates
    "shell_is_destructive_delete": shell_is_destructive_delete,
    "shell_touches_sensitive_path": shell_touches_sensitive_path,
    "shell_requires_privilege": shell_requires_privilege,
    "shell_missing_change_ticket": shell_missing_change_ticket,
    "shell_modifies_profile_startup": shell_modifies_profile_startup,
    "shell_untrusted_network_target": shell_untrusted_network_target,
    "shell_permission_change_risky": shell_permission_change_risky,
    "shell_target_has_backup": shell_target_has_backup,
    # grammar-compatible overrides (Python OR Shell)
    "submit_post_request": submit_post_request,
    "request_untrusted_source": request_untrusted_source,
    "encode_data": encode_data,
    "copy_file": copy_file,
    "read_io": read_io,
    "write_to_io": write_to_io,
    "list_directory": list_directory,
    "execute_script": execute_script,
    "destuctive_os_inst": destuctive_os_inst,
    "involve_system_file": involve_system_file,
    "involve_system_dir": involve_system_dir,
    "is_improper_execution_privilege_code": is_improper_execution_privilege_code,
    "involve_bash_rc": involve_bash_rc,
    "is_side_channel_vulnerable": is_side_channel_vulnerable,
    "is_crypto_buggy": is_crypto_buggy,
    "is_buggy_process_management": is_buggy_process_management,
    "detect_unsafe_deserialization": detect_unsafe_deserialization,
    "detect_duplicate_keys_in_code": detect_duplicate_keys_in_code,
    "is_prng_buggy": is_prng_buggy,
    "is_amplification": is_amplification,
    "is_buggy_ip_validation_code": is_buggy_ip_validation_code,
    "detect_missing_default_case": detect_missing_default_case,
}
