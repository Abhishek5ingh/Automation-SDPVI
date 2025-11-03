from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
from loguru import logger


@dataclass(slots=True)
class AccountRecord:
    username: str
    password: str
    email: Optional[str] = None
    metadata: dict | None = None


class ExcelAccountReader:
    """Read test accounts from an Excel workbook."""

    def __init__(self, path: Path | str, sheet_name: str | int = 0) -> None:
        self.path = Path(path)
        self.sheet_name = sheet_name

    def read(self) -> List[AccountRecord]:
        if not self.path.exists():
            raise FileNotFoundError(f"Account workbook not found: {self.path}")

        logger.debug("Loading accounts from {}", self.path)
        df = pd.read_excel(self.path, sheet_name=self.sheet_name).fillna("")

        required_columns = {"username", "password"}
        missing_cols = required_columns - {c.lower() for c in df.columns}
        if missing_cols:
            raise ValueError(f"Missing required columns in spreadsheet: {missing_cols}")

        normalized_df = df.rename(columns=str.lower)

        accounts: List[AccountRecord] = []
        for _, row in normalized_df.iterrows():
            username = str(row.get("username", "")).strip()
            password = str(row.get("password", "")).strip()
            if not username or not password:
                logger.warning("Skipping row with missing credentials: {}", row.to_dict())
                continue

            metadata = {
                key: row[key]
                for key in normalized_df.columns
                if key not in {"username", "password"} and row.get(key, "")
            }

            accounts.append(
                AccountRecord(
                    username=username,
                    password=password,
                    email=str(row.get("email", "")).strip() or None,
                    metadata=metadata or None,
                )
            )

        logger.info("Loaded {} account(s) from Excel", len(accounts))
        return accounts

    def iter_accounts(self) -> Iterable[AccountRecord]:
        yield from self.read()
