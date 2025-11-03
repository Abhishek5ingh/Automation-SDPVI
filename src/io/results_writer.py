from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence

from loguru import logger


@dataclass(slots=True)
class ResultRecord:
    username: str
    status: str
    details: str
    screenshots: Sequence[str] = field(default_factory=list)
    statements: Sequence[str] = field(default_factory=list)


class ResultsWriter:
    """Persist run outcomes to a CSV file."""

    HEADER = ["username", "status", "details", "screenshots", "statements"]

    def __init__(self, csv_path: Path | str) -> None:
        self.csv_path = Path(csv_path)

    def initialize(self) -> None:
        if not self.csv_path.exists():
            logger.debug("Initializing results CSV at {}", self.csv_path)
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            with self.csv_path.open("w", newline="", encoding="utf-8") as fp:
                writer = csv.writer(fp)
                writer.writerow(self.HEADER)

    def append(self, result: ResultRecord) -> None:
        self.initialize()
        logger.debug("Recording result for {}", result.username)
        with self.csv_path.open("a", newline="", encoding="utf-8") as fp:
            writer = csv.writer(fp)
            writer.writerow(
                [
                    result.username,
                    result.status,
                    result.details,
                    ";".join(result.screenshots),
                    ";".join(result.statements),
                ]
            )

    def append_many(self, results: Iterable[ResultRecord]) -> None:
        for result in results:
            self.append(result)
