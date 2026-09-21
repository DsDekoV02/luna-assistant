"""
Luna JARVIS - Security Module
Prompt injection protection and input sanitization.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("luna.tools.security")

# Patterns that indicate prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above)\s+(instructions|prompts)",
    r"you\s+are\s+now\s+",
    r"forget\s+(everything|all|previous)",
    r"new\s+instructions?\s*:",
    r"system\s*:\s*",
    r"\[INST\]",
    r"\[/INST\]",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"ignore\s+safety",
    r"bypass\s+(filter|safety|restriction)",
    r"act\s+as\s+if\s+you\s+(are|were)",
    r"pretend\s+you\s+(are|were|have)",
    r"do\s+anything\s+now",
    r"DAN\s+mode",
    r"jailbreak",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def check_injection(text: str) -> Optional[str]:
    """Check if text contains prompt injection patterns.

    Returns None if safe, or the matched pattern if injection detected.
    """
    for pattern in COMPILED_PATTERNS:
        match = pattern.search(text)
        if match:
            logger.warning(f"Injection detected: {match.group()} in: {text[:100]}...")
            return match.group()
    return None


def sanitize_input(text: str) -> str:
    """Sanitize user input before sending to the model.

    - Removes control characters
    - Limits length
    - Strips excessive whitespace
    """
    # Remove control characters except newlines
    text = re.sub(r'[\x00-\x09\x0b-\x1f\x7f]', '', text)

    # Limit length
    max_len = 2000
    if len(text) > max_len:
        text = text[:max_len]
        logger.warning(f"Input truncated to {max_len} chars")

    # Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def validate_command(command: str, params: dict) -> tuple[bool, str]:
    """Validate a tool command before execution.

    Returns (is_valid, error_message).
    """
    # Check if command is in the allowlist (defense in depth)
    from tools.allowlist import get_allowlist
    allowlist = get_allowlist()
    if not allowlist.is_allowed(command):
        return False, f"Command '{command}' is not in the allowlist"

    # Check for injection in params
    for key, value in params.items():
        if isinstance(value, str):
            injection = check_injection(value)
            if injection:
                return False, f"Suspicious input in {key}: contains '{injection}'"

    # Validate path parameters
    for key in ("path", "directory"):
        if key in params:
            path = str(params[key])
            # Block access to sensitive directories
            blocked = ["windows", "system32", "program files", ".ssh", "credentials"]
            for b in blocked:
                if b in path.lower():
                    return False, f"Access to '{b}' directory is blocked"

    # Validate app names
    if command == "openapp":
        app = params.get("app_name", "")
        dangerous_apps = ["regedit", "format", "diskpart", "netsh", "taskkill"]
        if any(d in app.lower() for d in dangerous_apps):
            return False, f"Application '{app}' is not allowed"

    # Validate readfile paths - block sensitive dirs
    if command == "readfile":
        path = str(params.get("path", ""))
        blocked_exts = [".key", ".pem", ".env", ".credentials", ".secret", ".p12", ".pfx"]
        for ext in blocked_exts:
            if path.lower().endswith(ext):
                return False, f"Access to {ext} files is blocked"

    # Validate clipboard set - limit text size
    if command == "clipboard" and params.get("action") == "set":
        text = str(params.get("text", ""))
        if len(text) > 5000:
            return False, "Clipboard text too large (max 5000 chars)"

    # Validate webfetch URLs
    if command == "webfetch":
        url = str(params.get("url", ""))
        if not url.startswith(("http://", "https://")):
            return False, "Only HTTP/HTTPS URLs allowed"

    return True, ""
