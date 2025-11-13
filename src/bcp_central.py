import argparse
import asyncio
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus

from dotenv import load_dotenv
from playwright.async_api import Browser, Page, async_playwright

load_dotenv()

DEFAULT_REPORTS = [
    "International Air Traffic Data",
    "Average Number Of Trains Run Daily upto 2013-14",
]

ROOT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", ROOT_DIR / "downloads")).resolve()
LOG_DIR = Path(os.getenv("LOG_DIR", ROOT_DIR / "logs")).resolve()
HEADLESS_ENV = os.getenv("HEADLESS", "true").lower() != "false"
NAVIGATION_TIMEOUT_MS = int(os.getenv("NAVIGATION_TIMEOUT_MS", "45000"))
BASE_URL = os.getenv("PORTAL_BASE_URL", "https://www.data.gov.in/")
SEARCH_TEMPLATE = os.getenv(
    "PORTAL_SEARCH_URL",
    "https://www.data.gov.in/search?query={query}",
)
RESOURCE_SELECTOR = os.getenv(
    "RESOURCE_SELECTOR",
    'a[href$=".csv"], a[href$=".xls"], a[href$=".xlsx"], '
    'a[href$=".geojson"], a[href$=".kml"], a[href$=".kmz"], '
    'a.download-resource, a.btn.btn-primary[href]',
)
RESOURCE_PRE_CLICK_SELECTOR = os.getenv("RESOURCE_PRE_CLICK_SELECTOR")
SEARCH_INPUT_SELECTOR = os.getenv("SEARCH_INPUT_SELECTOR")
SEARCH_SUBMIT_SELECTOR = os.getenv("SEARCH_SUBMIT_SELECTOR")
logger = logging.getLogger("dataset_downloader")

LOGIN_CONFIG = {
    "url": os.getenv("PORTAL_LOGIN_URL"),
    "username": os.getenv("PORTAL_USERNAME"),
    "password": os.getenv("PORTAL_PASSWORD"),
    "username_selector": os.getenv("PORTAL_USERNAME_SELECTOR"),
    "password_selector": os.getenv("PORTAL_PASSWORD_SELECTOR"),
    "submit_selector": os.getenv("PORTAL_SUBMIT_SELECTOR"),
    "post_login_selector": os.getenv("PORTAL_POST_LOGIN_SELECTOR"),
}


def setup_logging() -> Path:
    """Initialize dual console/file logging and return the log file path."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = LOG_DIR / f"run-{timestamp}.log"
    handlers = [
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        force=True,
    )
    logger.info("Log file initialized at %s", log_path)
    return log_path


def parse_reports(cli_reports: List[str]) -> List[str]:
    """Merge CLI report names with .env defaults while preserving order."""
    env_reports = [part.strip() for part in os.getenv("REPORTS", "").split("|") if part.strip()]
    combined = [*cli_reports, *env_reports]
    if combined:
        return list(dict.fromkeys(combined))
    return DEFAULT_REPORTS


def build_search_url(query: str) -> str:
    """Convert a dataset title into a portal-specific search URL."""
    encoded = quote_plus(query)
    if "{query}" in SEARCH_TEMPLATE:
        return SEARCH_TEMPLATE.replace("{query}", encoded)
    return f"{SEARCH_TEMPLATE}{encoded}"


def sanitize_filename(label: str) -> str:
    """Slugify dataset titles so saved files have filesystem-safe names."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", label).strip("-")
    return slug.lower() or "report"


def ensure_output_dir() -> None:
    """Create the output directory tree if it does not already exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def perform_login(page: Page) -> bool:
    """Optionally authenticate on the portal when login settings are provided."""
    if not LOGIN_CONFIG.get("url"):
        return False

    required = [
        LOGIN_CONFIG.get("username_selector"),
        LOGIN_CONFIG.get("password_selector"),
        LOGIN_CONFIG.get("submit_selector"),
    ]
    if any(not selector for selector in required):
        logger.warning("[login] Skipped: missing selectors in configuration")
        return False

    if not LOGIN_CONFIG.get("username") or not LOGIN_CONFIG.get("password"):
        logger.warning("[login] Skipped: missing credentials")
        return False

    await page.goto(LOGIN_CONFIG["url"], wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
    await page.fill(LOGIN_CONFIG["username_selector"], LOGIN_CONFIG["username"])
    await page.fill(LOGIN_CONFIG["password_selector"], LOGIN_CONFIG["password"])
    async with page.expect_navigation(timeout=NAVIGATION_TIMEOUT_MS) as nav:
        await page.click(LOGIN_CONFIG["submit_selector"])
    await nav.value
    if LOGIN_CONFIG.get("post_login_selector"):
        await page.wait_for_selector(LOGIN_CONFIG["post_login_selector"], timeout=NAVIGATION_TIMEOUT_MS)
    logger.info("[login] Successful")
    return True


def build_fuzzy_regex(title: str) -> re.Pattern:
    """Generate a loose regex that tolerates partial matches in link text."""
    tokens = [re.escape(token) for token in title.split() if token]
    if not tokens:
        return re.compile(re.escape(title), re.IGNORECASE)
    pattern = ".*".join(tokens[:5])
    return re.compile(pattern, re.IGNORECASE)


async def find_dataset_link(page: Page, report_title: str):
    """Return a locator pointing at the best matching dataset anchor tag."""
    exact_regex = re.compile(re.escape(report_title), re.IGNORECASE)
    locator = page.locator("a").filter(has_text=exact_regex).first
    if await locator.count() > 0:
        return locator

    fuzzy_regex = build_fuzzy_regex(report_title)
    locator = page.locator("a").filter(has_text=fuzzy_regex).first
    if await locator.count() > 0:
        return locator

    raise RuntimeError("Dataset link not found in search results")


async def open_dataset(page: Page, report_title: str) -> None:
    """Click the located dataset entry and wait for its detail page to load."""
    await page.wait_for_timeout(1000)
    locator = await find_dataset_link(page, report_title)
    async with page.expect_navigation(wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS):
        await locator.click(timeout=NAVIGATION_TIMEOUT_MS)
    await page.wait_for_load_state("networkidle", timeout=NAVIGATION_TIMEOUT_MS)


async def search_for_report(page: Page, report_title: str) -> None:
    """Navigate to the search results for a title, then open the dataset page."""
    if SEARCH_INPUT_SELECTOR:
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
        await page.wait_for_selector(SEARCH_INPUT_SELECTOR, timeout=NAVIGATION_TIMEOUT_MS)
        await page.fill(SEARCH_INPUT_SELECTOR, report_title)
        if SEARCH_SUBMIT_SELECTOR:
            await page.click(SEARCH_SUBMIT_SELECTOR, timeout=NAVIGATION_TIMEOUT_MS)
        else:
            await page.keyboard.press("Enter")
        await page.wait_for_load_state("domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
        await page.wait_for_load_state("networkidle", timeout=NAVIGATION_TIMEOUT_MS)
    else:
        search_url = build_search_url(report_title)
        await page.goto(search_url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
        await page.wait_for_load_state("networkidle", timeout=NAVIGATION_TIMEOUT_MS)
    await open_dataset(page, report_title)


def build_destination_filename(suggested: str, fallback_title: str) -> str:
    """Sanitize the suggested filename while preserving its extension."""
    path = Path(suggested)
    suffix = path.suffix or ""
    stem_source = path.stem or fallback_title
    safe_stem = sanitize_filename(stem_source)
    return f"{safe_stem}{suffix or '.dat'}"


async def download_resource(page: Page, report_title: str) -> Path:
    """Click the first matching resource link and persist the resulting download."""
    locator = page.locator(RESOURCE_SELECTOR)
    if await locator.count() == 0:
        raise RuntimeError("No downloadable resources detected")

    if RESOURCE_PRE_CLICK_SELECTOR:
        toggle_locator = page.locator(RESOURCE_PRE_CLICK_SELECTOR)
        if await toggle_locator.count() > 0:
            await toggle_locator.first.click(timeout=NAVIGATION_TIMEOUT_MS)

    target = locator.first
    handle = await target.element_handle()
    if handle is None:
        raise RuntimeError("Download link became unavailable before clicking")

    async with page.expect_download(timeout=NAVIGATION_TIMEOUT_MS) as download_info:
        await handle.evaluate("el => el.click()")
    download = await download_info.value
    suggested = download.suggested_filename or f"{sanitize_filename(report_title)}.dat"
    destination = OUTPUT_DIR / build_destination_filename(suggested, report_title)
    if destination.exists():
        destination.unlink()
    await download.save_as(destination)
    return destination


async def process_report(page: Page, report_title: str) -> Optional[Path]:
    """Search, open, and download a single dataset; return the saved path."""
    logger.info("[report] Processing: %s", report_title)
    await search_for_report(page, report_title)
    path = await download_resource(page, report_title)
    logger.info("[report] Saved to %s", path)
    return path


async def run_automation(reports: List[str], headless: bool) -> None:
    """Drive the full workflow for all requested datasets and summarize failures."""
    ensure_output_dir()
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
        await page.wait_for_timeout(500)

        await perform_login(page)

        failures = []
        for report in reports:
            try:
                await process_report(page, report)
            except Exception as exc:
                failures.append((report, str(exc)))
                logger.exception("[report] Failed %s: %s", report, exc)

        await browser.close()

        if failures:
            logger.error("Completed with %s failure(s)", len(failures))
            for name, msg in failures:
                logger.error(" - %s: %s", name, msg)
            raise SystemExit(1)
        logger.info("All requested reports downloaded successfully.")


def build_arg_parser() -> argparse.ArgumentParser:
    """Set up CLI arguments for report names and headed/headless overrides."""
    parser = argparse.ArgumentParser(
        description="Search datasets on a portal and download available CSV/XLS resources using Playwright.",
    )
    parser.add_argument("reports", nargs="*", help="Dataset titles to search for (falls back to defaults/.env)")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode (overrides HEADLESS env)",
    )
    return parser


def main() -> None:
    """Entry point: parse args, resolve settings, and launch the async flow."""
    parser = build_arg_parser()
    args = parser.parse_args()
    log_path = setup_logging()
    logger.info("Log file located at %s", log_path)
    reports = parse_reports(args.reports)
    if not reports:
        logger.error("No reports supplied via CLI or configuration.")
        raise SystemExit("No reports supplied via CLI or configuration.")

    headless = HEADLESS_ENV and not args.headed
    logger.info("Starting automation | headless=%s | reports=%s", headless, reports)
    try:
        asyncio.run(run_automation(reports, headless=headless))
    except Exception:
        logger.exception("Automation run failed")
        raise


if __name__ == "__main__":
    main()
