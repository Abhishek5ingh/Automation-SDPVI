from __future__ import annotations

from dataclasses import dataclass

SENSITIVE_KEYS = {"password", "otp", "token", "secret"}


@dataclass(slots=True)
class Redaction:
    mask: str = "****"

    def redact(self, value: str | None) -> str:
        if value is None:
            return self.mask
        if len(value) <= 4:
            return self.mask
        return f"{value[:2]}{self.mask}{value[-2:]}"


def redact_dict(payload: dict, redaction: Redaction | None = None) -> dict:
    """Return a shallow copy with sensitive keys masked."""
    redaction = redaction or Redaction()
    return {
        key: redaction.redact(value) if key.lower() in SENSITIVE_KEYS else value
        for key, value in payload.items()
    }
