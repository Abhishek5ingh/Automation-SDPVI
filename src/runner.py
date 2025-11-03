from __future__ import annotations

import asyncio
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from loguru import logger

from src.browser.browser_manager import BrowserManager
from src.browser.pages import (
    AccountSummaryPage,
    LoginPage,
    LoginSelectors,
    OtpPage,
    OtpSelectors,
    StatementSelectors,
    SummarySelectors,
)
from src.email.mailbox_client import MailboxClient
from src.io.excel_reader import AccountRecord, ExcelAccountReader
from src.io.results_writer import ResultRecord, ResultsWriter
from src.utils.config import AppConfig


@dataclass(slots=True)
class AccountOutcome:
    record: AccountRecord
    status: str
    details: str = ""
    screenshots: List[str] | None = None
    statements: List[str] | None = None

    def to_result_record(self) -> ResultRecord:
        return ResultRecord(
            username=self.record.username,
            status=self.status,
            details=self.details,
            screenshots=self.screenshots or [],
            statements=self.statements or [],
        )


class AutomationRunner:
    def __init__(
        self,
        config: AppConfig,
        selectors: Dict[str, Dict[str, str]],
        headless_override: Optional[bool] = None,
        limit: Optional[int] = None,
        single_account: Optional[str] = None,
    ) -> None:
        self.config = config
        self.selectors = selectors
        self.limit = limit or (config.max_accounts if config.max_accounts > 0 else None)
        self.single_account = single_account
        if headless_override is not None:
            self.config.browser.headless = headless_override

        self.browser_manager = BrowserManager(self.config)
        self.mailbox_client = MailboxClient(self.config.mailbox)
        self.results_writer = ResultsWriter(self.config.outputs.results_csv)

    async def run(self) -> None:
        accounts = self._load_accounts()
        logger.info("Starting automation for {} account(s)", len(accounts))

        try:
            await self.browser_manager.start()
            with self.mailbox_client:
                outcomes = []
                for idx, account in enumerate(accounts, start=1):
                    if self.limit and idx > self.limit:
                        logger.info("Hit configured account limit ({}). Stopping.", self.limit)
                        break
                    outcome = await self._process_account(account)
                    outcomes.append(outcome)
                    self.results_writer.append(outcome.to_result_record())
        finally:
            await self.browser_manager.stop()

    def _load_accounts(self) -> List[AccountRecord]:
        reader = ExcelAccountReader(self.config.excel_path)
        accounts = reader.read()
        if self.single_account:
            accounts = [acc for acc in accounts if acc.username == self.single_account]
        if not accounts:
            raise RuntimeError("No accounts available for processing.")
        return accounts

    def _build_login_page(self, page) -> LoginPage:
        login_selectors = LoginSelectors(**self.selectors["login"])
        return LoginPage(page, login_selectors)

    def _build_otp_page(self, page) -> OtpPage:
        otp_selectors = OtpSelectors(**self.selectors["otp"])
        return OtpPage(page, otp_selectors)

    def _build_summary_page(self, page) -> AccountSummaryPage:
        summary_selectors = SummarySelectors(**self.selectors["summary"])
        statement_selectors = StatementSelectors(**self.selectors["statements"])
        return AccountSummaryPage(page, summary_selectors, statement_selectors)

    async def _process_account(self, account: AccountRecord) -> AccountOutcome:
        logger.info("Processing account {}", account.username)
        screenshots: List[str] = []
        statements: List[str] = []

        download_dir = self.config.outputs.statements_dir / account.username
        screenshot_dir = self.config.outputs.screenshots_dir / account.username
        download_dir.mkdir(parents=True, exist_ok=True)
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        try:
            async with self.browser_manager.page(download_dir) as page:
                login_page = self._build_login_page(page)
                await login_page.goto(self.config.bank_base_url)
                await login_page.login(account.username, account.password)

                await page.wait_for_selector(self.selectors["otp"]["otp_input"])
                otp_request_time = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=5)

                otp = await asyncio.to_thread(
                    self.mailbox_client.poll_for_otp,
                    account.email or account.username,
                    otp_request_time,
                )
                if not otp:
                    error_details = "OTP timeout"
                    logger.error("Failed to retrieve OTP for {}: {}", account.username, error_details)
                    return AccountOutcome(account, status="FAILED", details=error_details)

                otp_page = self._build_otp_page(page)
                await otp_page.submit_otp(otp)

                summary_page = self._build_summary_page(page)
                await page.wait_for_selector(self.selectors["summary"]["summary_section"])

                summary_path = await summary_page.capture_summary(screenshot_dir, "overview")
                screenshots.append(str(summary_path))

                accounts = await summary_page.list_accounts()
                for account_meta in accounts:
                    account_id = account_meta.get("number", "unknown").replace(" ", "_")
                    account_path = await summary_page.capture_summary(screenshot_dir, account_id)
                    screenshots.append(str(account_path))

                    await summary_page.open_statements_tab()
                    statement_path = await summary_page.download_latest_statement(download_dir, account_id)
                    if statement_path:
                        statements.append(str(statement_path))

            logger.success("Completed account {}", account.username)
            return AccountOutcome(account, status="SUCCESS", screenshots=screenshots, statements=statements)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled exception for account {}", account.username)
            return AccountOutcome(account, status="FAILED", details=str(exc))
