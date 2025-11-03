from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import dotenv_values
from loguru import logger


@dataclass(slots=True)
class MailboxConfig:
    host: str
    username: str
    password: str
    port: int = 993
    folder: str = "INBOX"
    sender_filter: Optional[str] = None
    otp_regex: str = r"\b(\d{6})\b"
    poll_timeout: int = 60
    poll_interval: float = 5.0


@dataclass(slots=True)
class BrowserConfig:
    headless: bool = True
    download_wait_seconds: int = 30
    viewport_width: int = 1280
    viewport_height: int = 720


@dataclass(slots=True)
class OutputConfig:
    root_dir: Path
    screenshots_dir: Path
    statements_dir: Path
    results_csv: Path
    log_file: Path

    def ensure_directories(self) -> None:
        for path in {self.root_dir, self.screenshots_dir, self.statements_dir, self.log_file.parent}:
            if not path.exists():
                logger.debug("Creating output directory {}", path)
                path.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class AppConfig:
    bank_base_url: str
    excel_path: Path
    mailbox: MailboxConfig
    browser: BrowserConfig
    outputs: OutputConfig
    log_level: str = "INFO"
    max_accounts: int = 0

    @property
    def selectors_config(self) -> Dict[str, Any]:
        """Return cached selectors if available."""
        if not hasattr(self, "_selectors"):
            raise AttributeError("Selectors configuration not loaded")
        return getattr(self, "_selectors")

    def set_selectors(self, selectors: Dict[str, Any]) -> None:
        setattr(self, "_selectors", selectors)


def _coerce_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _get_env(env: Dict[str, str], key: str, default: Optional[str] = None) -> str:
    value = env.get(key, os.getenv(key, default))
    if value is None:
        raise ValueError(f"Missing required configuration key: {key}")
    return value


def load_config(env_file: Optional[Path] = None) -> AppConfig:
    """Load configuration from .env file (if present) merged with environment variables."""
    env: Dict[str, str] = {}
    if env_file:
        env_file_path = Path(env_file)
        if env_file_path.exists():
            env = {**env, **dotenv_values(env_file_path)}
        else:
            logger.warning("Provided env file {} does not exist", env_file_path)
    # Overlay with real environment variables
    env = {**env, **os.environ}

    bank_base_url = _get_env(env, "BANK_BASE_URL")
    excel_path = Path(_get_env(env, "EXCEL_PATH"))

    mailbox = MailboxConfig(
        host=_get_env(env, "IMAP_HOST"),
        username=_get_env(env, "IMAP_USERNAME"),
        password=_get_env(env, "IMAP_PASSWORD"),
        port=int(env.get("IMAP_PORT", 993)),
        folder=env.get("IMAP_FOLDER", "INBOX"),
        sender_filter=env.get("IMAP_SENDER_FILTER"),
        otp_regex=env.get("IMAP_OTP_REGEX", r"\b(\d{6})\b"),
        poll_timeout=int(env.get("IMAP_POLL_TIMEOUT", 60)),
        poll_interval=float(env.get("IMAP_POLL_INTERVAL", 5)),
    )

    browser = BrowserConfig(
        headless=_coerce_bool(env.get("HEADLESS", "true")),
        download_wait_seconds=int(env.get("DOWNLOAD_WAIT_SECONDS", 30)),
        viewport_width=int(env.get("DEFAULT_VIEWPORT_WIDTH", 1280)),
        viewport_height=int(env.get("DEFAULT_VIEWPORT_HEIGHT", 720)),
    )

    outputs = OutputConfig(
        root_dir=Path(env.get("OUTPUT_DIR", "outputs")).resolve(),
        screenshots_dir=Path(env.get("SCREENSHOT_DIR", "outputs/screenshots")).resolve(),
        statements_dir=Path(env.get("STATEMENT_DIR", "outputs/statements")).resolve(),
        results_csv=Path(env.get("RESULTS_CSV", "outputs/run_results.csv")).resolve(),
        log_file=Path(env.get("LOG_FILE", "outputs/automation.log")).resolve(),
    )

    config = AppConfig(
        bank_base_url=bank_base_url,
        excel_path=excel_path,
        mailbox=mailbox,
        browser=browser,
        outputs=outputs,
        log_level=env.get("LOG_LEVEL", "INFO"),
        max_accounts=int(env.get("MAX_ACCOUNTS", 0)),
    )

    outputs.ensure_directories()

    return config


def load_selectors(path: Path | str) -> Dict[str, Any]:
    selectors_path = Path(path)
    if not selectors_path.exists():
        raise FileNotFoundError(f"Selectors config not found: {selectors_path}")
    with selectors_path.open("r", encoding="utf-8") as fp:
        return json.load(fp)
