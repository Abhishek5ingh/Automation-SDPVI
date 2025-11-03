from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from loguru import logger

from src.runner import AutomationRunner
from src.utils.config import AppConfig, load_config, load_selectors


def configure_logging(config: AppConfig, verbose: bool = False) -> None:
    logger.remove()
    level = "DEBUG" if verbose else config.log_level
    logger.add(
        config.outputs.log_file,
        level=level,
        rotation="5 MB",
        retention=10,
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )
    logger.add(lambda msg: print(msg, end=""), level=level, colorize=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bank login automation runner")
    parser.add_argument("--env-file", type=Path, default=None, help="Path to .env file")
    parser.add_argument("--selectors", type=Path, default=Path("configs/selectors.json"), help="Selectors JSON file")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of accounts to process")
    parser.add_argument("--account", type=str, default=None, help="Process a single username/email")
    parser.add_argument("--headless", dest="headless", action="store_true", help="Force headless mode")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Force headed mode")
    parser.set_defaults(headless=None)
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    config = load_config(args.env_file)
    configure_logging(config, verbose=args.verbose)

    selectors = load_selectors(args.selectors)
    config.set_selectors(selectors)

    runner = AutomationRunner(
        config=config,
        selectors=selectors,
        headless_override=args.headless,
        limit=args.limit,
        single_account=args.account,
    )
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
