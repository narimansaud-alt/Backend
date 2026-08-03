import hashlib
import re
from dataclasses import dataclass

TOKEN_PATTERN = re.compile(r"(?i)(authorization|api[-_ ]?key|token|secret|password)(\s*[:=]\s*)([^\s,;]+)")
BEARER_PATTERN = re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]+")
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def sanitize_text(value: str | None, *, limit: int) -> str | None:
    if value is None:
        return None
    # A generic ``Authorization:`` rule would otherwise consume only the
    # ``Bearer`` scheme and leave the credential itself in the message.
    cleaned = BEARER_PATTERN.sub("Bearer [REDACTED]", value)
    cleaned = TOKEN_PATTERN.sub(r"\1\2[REDACTED]", cleaned)
    cleaned = EMAIL_PATTERN.sub("[EMAIL]", cleaned)
    return cleaned[:limit]


@dataclass(frozen=True)
class SanitizedClientError:
    route: str
    release: str
    browser: str | None
    message: str
    stack: str | None
    component_stack: str | None
    request_id: str | None
    fingerprint: str


def sanitize_client_error(
    *,
    route: str,
    release: str,
    browser: str | None,
    message: str,
    stack: str | None,
    component_stack: str | None,
    request_id: str | None,
) -> SanitizedClientError:
    safe_route = sanitize_text(route, limit=512) or "/"
    safe_release = sanitize_text(release, limit=128) or "unknown"
    safe_message = sanitize_text(message, limit=1024) or "Client error"
    safe_stack = sanitize_text(stack, limit=16_384)
    safe_component = sanitize_text(component_stack, limit=16_384)
    basis = f"{safe_route}\n{safe_message}\n{(safe_stack or '').splitlines()[0:2]}"
    fingerprint = hashlib.sha256(basis.encode()).hexdigest()
    return SanitizedClientError(
        route=safe_route,
        release=safe_release,
        browser=sanitize_text(browser, limit=256),
        message=safe_message,
        stack=safe_stack,
        component_stack=safe_component,
        request_id=sanitize_text(request_id, limit=64),
        fingerprint=fingerprint,
    )
