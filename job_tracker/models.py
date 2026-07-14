"""Shared data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.utils import parseaddr
from typing import Optional


APPLICATION_HEADERS = [
    "Application Date",
    "Company",
    "Role",
    "Status",
    "Last Email Date",
    "Sender",
    "Subject",
    "Gmail Link",
    "Last Updated",
    "Latest Message ID",
    "Application Key",
    "Auto Status",
    "Thread ID",
    "Sender Domain",
]

PROCESSED_HEADERS = ["Message ID", "Processed At", "Subject"]

REVIEW_HEADERS = [
    "Email Date",
    "Proposed Status",
    "Company",
    "Role",
    "Sender",
    "Subject",
    "Gmail Link",
    "Reason",
    "Message ID",
    "Thread ID",
]


@dataclass(frozen=True)
class EmailMessage:
    message_id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    timestamp: datetime

    @property
    def date(self) -> str:
        return self.timestamp.strftime("%Y-%m-%d")

    @property
    def sender_address(self) -> str:
        return parseaddr(self.sender)[1].lower()

    @property
    def sender_domain(self) -> str:
        address = self.sender_address
        return address.split("@", 1)[1] if "@" in address else ""

    @property
    def gmail_link(self) -> str:
        return f"https://mail.google.com/mail/u/0/#all/{self.thread_id}"


@dataclass(frozen=True)
class Classification:
    status: Optional[str]
    reason: str
    requires_existing_application: bool = False

    @property
    def included(self) -> bool:
        return self.status is not None


@dataclass
class ApplicationRecord:
    row_number: Optional[int]
    values: list[str]

    def __post_init__(self) -> None:
        missing = len(APPLICATION_HEADERS) - len(self.values)
        if missing > 0:
            self.values.extend([""] * missing)
        self.values = self.values[: len(APPLICATION_HEADERS)]

    @property
    def application_date(self) -> str:
        return self.values[0]

    @property
    def company(self) -> str:
        return self.values[1]

    @property
    def role(self) -> str:
        return self.values[2]

    @property
    def status(self) -> str:
        return self.values[3]

    @property
    def last_email_date(self) -> str:
        return self.values[4]

    @property
    def application_key(self) -> str:
        return self.values[10]

    @property
    def auto_status(self) -> str:
        return self.values[11]

    @property
    def thread_id(self) -> str:
        return self.values[12]

    @property
    def sender_domain(self) -> str:
        return self.values[13]
