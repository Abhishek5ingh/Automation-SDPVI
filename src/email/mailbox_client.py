from __future__ import annotations

import contextlib
import datetime as dt
import email
from typing import Optional

from imapclient import IMAPClient
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed

from src.email.parser import extract_otp_from_email
from src.utils.config import MailboxConfig


class MailboxClient:
    """Thin wrapper around IMAPClient to poll for OTP emails."""

    def __init__(self, config: MailboxConfig) -> None:
        self.config = config
        self._client: Optional[IMAPClient] = None

    def connect(self) -> None:
        logger.debug("Connecting to IMAP server {}", self.config.host)
        self._client = IMAPClient(self.config.host, port=self.config.port, ssl=True)
        self._client.login(self.config.username, self.config.password)
        self._client.select_folder(self.config.folder)

    def disconnect(self) -> None:
        if self._client:
            logger.debug("Closing IMAP connection")
            with contextlib.suppress(Exception):
                self._client.logout()
            self._client = None

    def __enter__(self) -> "MailboxClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    def _search_query(self, since: Optional[dt.datetime], recipient: Optional[str]) -> list:
        criteria = ["UNSEEN"]
        if since:
            criteria.extend(["SINCE", since.strftime("%d-%b-%Y")])
        if self.config.sender_filter:
            criteria.extend(["FROM", self.config.sender_filter])
        if recipient:
            criteria.extend(["TO", recipient])
        return criteria

    def fetch_latest_otp(self, recipient: Optional[str] = None, since: Optional[dt.datetime] = None) -> Optional[str]:
        if not self._client:
            raise RuntimeError("IMAP client not connected")

        logger.debug("Polling mailbox for OTP (recipient={}, since={})", recipient, since)
        message_uids = self._client.search(self._search_query(since, recipient))
        if not message_uids:
            logger.debug("No new OTP messages found yet")
            return None

        # fetch newest first
        latest_uid = max(message_uids)
        raw_messages = self._client.fetch([latest_uid], ["RFC822"])
        raw_email = raw_messages[latest_uid][b"RFC822"]
        email_message = email.message_from_bytes(raw_email)
        otp = extract_otp_from_email(email_message, self.config.otp_regex)
        if otp:
            logger.info("Extracted OTP for {} from UID {}", recipient or "unknown recipient", latest_uid)
        else:
            logger.warning("Failed to parse OTP from UID {}", latest_uid)
        return otp

    @retry(
        retry=retry_if_exception_type(RuntimeError),
        wait=wait_fixed(2),
        stop=stop_after_delay(10),
        reraise=True,
    )
    def assert_connected(self) -> None:
        if not self._client:
            raise RuntimeError("IMAP client not connected")

    def poll_for_otp(self, recipient: Optional[str] = None, since: Optional[dt.datetime] = None) -> Optional[str]:
        self.assert_connected()
        import time

        deadline = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=self.config.poll_timeout)
        while dt.datetime.now(dt.timezone.utc) < deadline:
            otp = self.fetch_latest_otp(recipient, since)
            if otp:
                return otp
            logger.debug("Waiting {}s before next mailbox poll", self.config.poll_interval)
            time.sleep(self.config.poll_interval)
        logger.error("OTP polling timed out after {} seconds", self.config.poll_timeout)
        return None
