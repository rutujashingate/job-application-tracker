"""Gmail querying and MIME parsing."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Any

from bs4 import BeautifulSoup

from .models import EmailMessage


# A candidate email must match one lifecycle phrase...
LIFECYCLE_SEARCH_PHRASES = [
    "thank you for applying",
    "thanks for applying",
    "thank you for your interest",
    "thank you for your interest in",
    "application received",
    "application update",
    "application outcome",
    "candidacy update",
    "regarding your application",
    "follow up to your application",
    "we received your application",
    "your application has been received",
    "application successfully submitted",
    "job application",
    "job application update",
    "you applied for",
    "not moving forward",
    "won't be moving forward",
    "unable to move forward",
    "moving forward with other candidates",
    "proceed with other candidates",
    "regret to inform",
    "not selected for the position",
    "not selected for this position",
    "not selected at this time",
    "selected another candidate",
    "position has been filled",
    "position filled",
    "filled all of our openings",
    "offered this position to another applicant",
    "not progressing with your application",
    "invite you to interview",
    "schedule an interview",
    "technical assessment",
    "coding challenge",
    "offer of employment",
    "offer letter",
]

# ...and one employment-context phrase or known ATS sender.
EMPLOYMENT_SEARCH_TERMS = [
    '"job"',
    '"job application"',
    '"position"',
    '"role"',
    '"candidate"',
    '"candidacy"',
    '"hiring"',
    '"recruiting"',
    '"recruiter"',
    '"employment"',
    '"interview"',
    "from:greenhouse.io",
    "from:greenhouse-mail.io",
    "from:lever.co",
    "from:ashbyhq.com",
    "from:workday.com",
    "from:myworkdayjobs.com",
    "from:myworkday.com",
    "from:smartrecruiters.com",
    "from:icims.com",
    "from:jobvite.com",
    "from:teamtailor.com",
    "from:breezy.hr",
    "from:workablemail.com",
    "from:rippling.com",
    "from:bamboohr.com",
    "from:successfactors.com",
    "from:pageuppeople.com",
    "from:paradox.ai",
    "from:applytojob.com",
]

# Remove obvious non-employment applications before downloading messages.
NON_JOB_QUERY_EXCLUSIONS = [
    "financial aid",
    "financial assistance",
    "loan application",
    "credit application",
    "credit card application",
    "mortgage application",
    "rental application",
    "apartment application",
    "admission application",
    "college application",
    "university application",
    "course application",
    "program application",
    "scholarship application",
    "grant application",
    "visa application",
    "insurance application",
    "membership application",
    "benefits application",
    "enrollment application",
    "tuition assistance",
]

GENERAL_QUERY_EXCLUSIONS = [
    "jobs you may like",
    "job recommendations",
    "recommended jobs",
    "new jobs for you",
    "job alert",
    "weekly job",
    "daily job",
    "open roles",
]


def build_query(start_date: str) -> str:
    """
    Build a conservative Gmail query.

    Gmail's after: operator is exclusive, so one day is subtracted to include
    START_DATE itself.
    """
    parsed = datetime.strptime(start_date, "%Y/%m/%d")
    inclusive_after = (parsed - timedelta(days=1)).strftime("%Y/%m/%d")

    lifecycle_group = " ".join(
        f'"{phrase}"'
        for phrase in LIFECYCLE_SEARCH_PHRASES
    )
    employment_group = " ".join(EMPLOYMENT_SEARCH_TERMS)

    exclusions = " ".join(
        f'-"{phrase}"'
        for phrase in (
            GENERAL_QUERY_EXCLUSIONS
            + NON_JOB_QUERY_EXCLUSIONS
        )
    )

    # Spaces between brace groups mean AND. Items inside each group mean OR.
    return (
        f"after:{inclusive_after} "
        f"{{{lifecycle_group}}} "
        f"{{{employment_group}}} "
        f"{exclusions}"
    )


def list_message_ids(gmail: Any, query: str) -> list[str]:
    ids: list[str] = []
    page_token: str | None = None

    while True:
        response = (
            gmail.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=500,
                pageToken=page_token,
            )
            .execute()
        )

        ids.extend(
            item["id"]
            for item in response.get("messages", [])
        )

        page_token = response.get("nextPageToken")
        if not page_token:
            return ids


def _decode(data: str | None) -> str:
    if not data:
        return ""

    try:
        padded = data + ("=" * (-len(data) % 4))
        raw = base64.urlsafe_b64decode(
            padded.encode("utf-8")
        )
        return raw.decode("utf-8", errors="replace")
    except (ValueError, UnicodeDecodeError):
        return ""


def _extract_body(payload: dict[str, Any]) -> str:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime_type == "text/plain" and body_data:
        return _decode(body_data)

    if mime_type == "text/html" and body_data:
        return BeautifulSoup(
            _decode(body_data),
            "html.parser",
        ).get_text(" ", strip=True)

    plain_parts: list[str] = []
    html_parts: list[str] = []

    for part in payload.get("parts", []):
        text = _extract_body(part)
        if not text:
            continue

        if part.get("mimeType") == "text/html":
            html_parts.append(text)
        else:
            plain_parts.append(text)

    return " ".join(plain_parts or html_parts)


def _header(
    headers: list[dict[str, str]],
    name: str,
) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def read_message(
    gmail: Any,
    message_id: str,
) -> EmailMessage:
    raw = (
        gmail.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="full",
        )
        .execute()
    )

    payload = raw.get("payload", {})
    headers = payload.get("headers", [])
    unix_seconds = int(raw.get("internalDate", "0")) / 1000

    return EmailMessage(
        message_id=message_id,
        thread_id=raw.get("threadId", ""),
        sender=_header(headers, "From"),
        subject=_header(headers, "Subject"),
        body=_extract_body(payload),
        timestamp=datetime.fromtimestamp(
            unix_seconds,
            tz=timezone.utc,
        ),
    )
