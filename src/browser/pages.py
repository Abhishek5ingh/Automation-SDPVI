from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from loguru import logger
from playwright.async_api import Locator, Page


@dataclass(slots=True)
class LoginSelectors:
    username_input: str
    password_input: str
    login_button: str
    error_banner: str | None = None


@dataclass(slots=True)
class OtpSelectors:
    otp_input: str
    submit_button: str
    resend_link: str | None = None


@dataclass(slots=True)
class SummarySelectors:
    account_rows: str
    account_name: str
    account_number: str
    account_balance: str
    summary_section: str


@dataclass(slots=True)
class StatementSelectors:
    tab_selector: str
    statement_rows: str
    download_button: str
    date_cell: str


class LoginPage:
    def __init__(self, page: Page, selectors: LoginSelectors) -> None:
        self.page = page
        self.selectors = selectors

    async def goto(self, url: str) -> None:
        logger.debug("Navigating to {}", url)
        await self.page.goto(url)

    async def login(self, username: str, password: str) -> None:
        logger.debug("Attempting login for {}", username)
        await self.page.fill(self.selectors.username_input, username)
        await self.page.fill(self.selectors.password_input, password)
        await self.page.click(self.selectors.login_button)

    async def read_error(self) -> str | None:
        if not self.selectors.error_banner:
            return None
        banner = self.page.locator(self.selectors.error_banner)
        if await banner.count():
            return await banner.inner_text()
        return None


class OtpPage:
    def __init__(self, page: Page, selectors: OtpSelectors) -> None:
        self.page = page
        self.selectors = selectors

    async def submit_otp(self, otp: str) -> None:
        logger.debug("Submitting OTP")
        await self.page.fill(self.selectors.otp_input, otp)
        await self.page.click(self.selectors.submit_button)


class AccountSummaryPage:
    def __init__(self, page: Page, selectors: SummarySelectors, statement_selectors: StatementSelectors) -> None:
        self.page = page
        self.summary_selectors = selectors
        self.statement_selectors = statement_selectors

    async def capture_summary(self, output_dir: Path, account_id: str) -> Path:
        summary_locator = self.page.locator(self.summary_selectors.summary_section)
        await summary_locator.wait_for()
        screenshot_path = output_dir / f"{account_id}_summary.png"
        logger.debug("Capturing summary screenshot {}", screenshot_path)
        await summary_locator.screenshot(path=str(screenshot_path))
        return screenshot_path

    async def list_accounts(self) -> List[Dict[str, str]]:
        rows = self.page.locator(self.summary_selectors.account_rows)
        count = await rows.count()
        accounts: List[Dict[str, str]] = []
        for index in range(count):
            row = rows.nth(index)
            accounts.append(
                {
                    "name": await row.locator(self.summary_selectors.account_name).inner_text(),
                    "number": await row.locator(self.summary_selectors.account_number).inner_text(),
                    "balance": await row.locator(self.summary_selectors.account_balance).inner_text(),
                }
            )
        return accounts

    async def open_statements_tab(self) -> None:
        logger.debug("Opening statements tab")
        await self.page.click(self.statement_selectors.tab_selector)

    async def download_latest_statement(self, download_dir: Path, account_id: str) -> Path | None:
        rows = self.page.locator(self.statement_selectors.statement_rows)
        if not await rows.count():
            logger.warning("No statements found for {}", account_id)
            return None

        first_row: Locator = rows.first
        download_button = first_row.locator(self.statement_selectors.download_button)
        date_text = await first_row.locator(self.statement_selectors.date_cell).inner_text()
        safe_date = "".join(char if char.isalnum() else "_" for char in date_text)
        logger.debug("Downloading statement for {} dated {}", account_id, date_text)
        with self.page.expect_download() as download_info:
            await download_button.click()
        download = await download_info.value
        target_path = download_dir / f"{account_id}_{safe_date}.pdf"
        await download.save_as(target_path)
        return target_path
