"""Configuration loaded from the local .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _csv_env(name: str) -> tuple[str, ...]:
    value = os.getenv(name, "")
    return tuple(
        item.strip().lower()
        for item in value.split(",")
        if item.strip()
    )


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    spreadsheet_id: str
    applications_sheet: str
    processed_sheet: str
    review_sheet: str
    start_date: str
    credentials_file: Path
    token_file: Path
    lock_file: Path
    blocked_sender_domains: tuple[str, ...]
    trusted_sender_domains: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        spreadsheet_id = os.getenv("SPREADSHEET_ID", "").strip()
        start_date = os.getenv("START_DATE", "2025/06/01").strip()

        try:
            datetime.strptime(start_date, "%Y/%m/%d")
        except ValueError as exc:
            raise ValueError(
                "START_DATE must use YYYY/MM/DD, for example 2025/06/01."
            ) from exc

        return cls(
            base_dir=BASE_DIR,
            spreadsheet_id=spreadsheet_id,
            applications_sheet=os.getenv(
                "APPLICATIONS_SHEET", "Applications"
            ).strip(),
            processed_sheet=os.getenv(
                "PROCESSED_SHEET", "ProcessedEmails"
            ).strip(),
            review_sheet=os.getenv("REVIEW_SHEET", "Review").strip(),
            start_date=start_date,
            credentials_file=Path(
                os.getenv(
                    "GOOGLE_CREDENTIALS_FILE",
                    str(BASE_DIR / "credentials.json"),
                )
            ).expanduser(),
            token_file=Path(
                os.getenv(
                    "GOOGLE_TOKEN_FILE",
                    str(BASE_DIR / "token.json"),
                )
            ).expanduser(),
            lock_file=Path(
                os.getenv(
                    "LOCK_FILE",
                    str(BASE_DIR / ".job_tracker.lock"),
                )
            ).expanduser(),
            blocked_sender_domains=_csv_env("BLOCKED_SENDER_DOMAINS"),
            trusted_sender_domains=_csv_env("TRUSTED_SENDER_DOMAINS"),
        )

    def validate(self) -> None:
        if not self.spreadsheet_id:
            raise ValueError(
                "SPREADSHEET_ID is missing. Copy .env.example to .env "
                "and add the value from your Google Sheet URL."
            )
