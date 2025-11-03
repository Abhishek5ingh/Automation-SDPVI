from __future__ import annotations

import re
from email.message import EmailMessage
from typing import Iterable, Optional

OTP_DEFAULT_REGEX = re.compile(r"\b(\d{6})\b")


def extract_otp_from_text(text: str, pattern: str | re.Pattern[str] | None = None) -> Optional[str]:
    if not text:
        return None
    regex = re.compile(pattern) if isinstance(pattern, str) else (pattern or OTP_DEFAULT_REGEX)
    match = regex.search(text)
    if match:
        return match.group(1)
    return None


def extract_otp_from_email(message: EmailMessage, pattern: str | re.Pattern[str] | None = None) -> Optional[str]:
    payloads: Iterable[str] = []
    if message.is_multipart():
        payloads = (
            part.get_payload(decode=True).decode(part.get_content_charset("utf-8"), errors="ignore")
            for part in message.walk()
            if part.get_content_type() in {"text/plain", "text/html"}
        )
    else:
        payloads = [
            message.get_payload(decode=True).decode(message.get_content_charset("utf-8"), errors="ignore")
        ]

    for payload in payloads:
        otp = extract_otp_from_text(payload, pattern)
        if otp:
            return otp
    return None
