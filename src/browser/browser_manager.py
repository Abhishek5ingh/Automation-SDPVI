from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from src.utils.config import AppConfig


class BrowserManager:
    """Create Playwright browser contexts ready for automation."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._playwright = None
        self._browser: Optional[Browser] = None

    async def start(self) -> None:
        if self._playwright is None:
            logger.debug("Launching Playwright")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.config.browser.headless
            )

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    @asynccontextmanager
    async def context(self, download_dir: Path) -> AsyncIterator[BrowserContext]:
        if not self._browser:
            await self.start()
        assert self._browser is not None
        download_dir.mkdir(parents=True, exist_ok=True)
        context = await self._browser.new_context(
            accept_downloads=True,
            viewport={
                "width": self.config.browser.viewport_width,
                "height": self.config.browser.viewport_height,
            },
            record_video_dir=None,
        )
        context.set_default_timeout(self.config.browser.download_wait_seconds * 1000)
        context.set_default_navigation_timeout(self.config.browser.download_wait_seconds * 1000)
        try:
            yield context
        finally:
            await context.close()

    @asynccontextmanager
    async def page(self, download_dir: Path) -> AsyncIterator[Page]:
        async with self.context(download_dir) as ctx:
            page = await ctx.new_page()
            try:
                yield page
            finally:
                await page.close()
