"""Google Sheets storage and status-preservation logic."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from .config import Settings
from .models import (
    APPLICATION_HEADERS,
    PROCESSED_HEADERS,
    REVIEW_HEADERS,
    ApplicationRecord,
    EmailMessage,
)
from .parser import application_key


STATUS_OPTIONS = [
    "Applied",
    "Assessment",
    "Interview",
    "Rejected",
    "Offer",
    "Withdrawn",
]


def ensure_structure(sheets: Any, settings: Settings) -> None:
    metadata = (
        sheets.spreadsheets()
        .get(
            spreadsheetId=settings.spreadsheet_id,
            fields="sheets.properties.sheetId,sheets.properties.title",
        )
        .execute()
    )
    title_to_id = {
        sheet["properties"]["title"]: sheet["properties"]["sheetId"]
        for sheet in metadata.get("sheets", [])
    }
    missing = [
        title
        for title in (
            settings.applications_sheet,
            settings.processed_sheet,
            settings.review_sheet,
        )
        if title not in title_to_id
    ]

    if missing:
        response = (
            sheets.spreadsheets()
            .batchUpdate(
                spreadsheetId=settings.spreadsheet_id,
                body={
                    "requests": [
                        {"addSheet": {"properties": {"title": title}}}
                        for title in missing
                    ]
                },
            )
            .execute()
        )
        for reply in response.get("replies", []):
            properties = reply.get("addSheet", {}).get("properties", {})
            if properties:
                title_to_id[properties["title"]] = properties["sheetId"]

    (
        sheets.spreadsheets()
        .values()
        .batchUpdate(
            spreadsheetId=settings.spreadsheet_id,
            body={
                "valueInputOption": "RAW",
                "data": [
                    {
                        "range": f"'{settings.applications_sheet}'!A1:N1",
                        "values": [APPLICATION_HEADERS],
                    },
                    {
                        "range": f"'{settings.processed_sheet}'!A1:C1",
                        "values": [PROCESSED_HEADERS],
                    },
                    {
                        "range": f"'{settings.review_sheet}'!A1:J1",
                        "values": [REVIEW_HEADERS],
                    },
                ],
            },
        )
        .execute()
    )

    (
        sheets.spreadsheets()
        .batchUpdate(
            spreadsheetId=settings.spreadsheet_id,
            body={
                "requests": [
                    {
                        "setDataValidation": {
                            "range": {
                                "sheetId": title_to_id[
                                    settings.applications_sheet
                                ],
                                "startRowIndex": 1,
                                "startColumnIndex": 3,
                                "endColumnIndex": 4,
                            },
                            "rule": {
                                "condition": {
                                    "type": "ONE_OF_LIST",
                                    "values": [
                                        {"userEnteredValue": value}
                                        for value in STATUS_OPTIONS
                                    ],
                                },
                                "strict": False,
                                "showCustomUi": True,
                            },
                        }
                    }
                ]
            },
        )
        .execute()
    )


def clear_tracking_data(sheets: Any, settings: Settings) -> None:
    for range_name in (
        f"'{settings.applications_sheet}'!A2:N",
        f"'{settings.processed_sheet}'!A2:C",
        f"'{settings.review_sheet}'!A2:J",
    ):
        (
            sheets.spreadsheets()
            .values()
            .clear(
                spreadsheetId=settings.spreadsheet_id,
                range=range_name,
                body={},
            )
            .execute()
        )


def get_processed_ids(sheets: Any, settings: Settings) -> set[str]:
    response = (
        sheets.spreadsheets()
        .values()
        .get(
            spreadsheetId=settings.spreadsheet_id,
            range=f"'{settings.processed_sheet}'!A2:A",
        )
        .execute()
    )
    return {
        row[0] for row in response.get("values", []) if row
    }


def get_applications(
    sheets: Any, settings: Settings
) -> list[ApplicationRecord]:
    response = (
        sheets.spreadsheets()
        .values()
        .get(
            spreadsheetId=settings.spreadsheet_id,
            range=f"'{settings.applications_sheet}'!A2:N",
        )
        .execute()
    )
    return [
        ApplicationRecord(row_number=row_number, values=row)
        for row_number, row in enumerate(
            response.get("values", []), start=2
        )
    ]


def _should_replace_auto_status(old_status: str, new_status: str) -> bool:
    if not old_status or old_status == new_status:
        return True
    if new_status == "Applied":
        return old_status == "Applied"
    if new_status == "Assessment" and old_status in {
        "Interview",
        "Rejected",
        "Offer",
    }:
        return False
    if old_status in {"Rejected", "Offer"}:
        return new_status in {"Rejected", "Offer"}
    return True


def _display_status(
    current_manual_status: str,
    previous_auto_status: str,
    next_auto_status: str,
) -> str:
    if (
        current_manual_status
        and previous_auto_status
        and current_manual_status != previous_auto_status
    ):
        return current_manual_status
    return next_auto_status


def create_application(
    email: EmailMessage, company: str, role: str, status: str
) -> ApplicationRecord:
    return ApplicationRecord(
        row_number=None,
        values=[
            email.date,
            company,
            role,
            status,
            email.date,
            email.sender,
            email.subject,
            email.gmail_link,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            email.message_id,
            application_key(company, role),
            status,
            email.thread_id,
            email.sender_domain,
        ],
    )


def update_application(
    record: ApplicationRecord,
    email: EmailMessage,
    company: str,
    role: str,
    proposed_status: str,
) -> bool:
    old_auto = record.auto_status or record.status
    if not _should_replace_auto_status(old_auto, proposed_status):
        return False

    next_company = (
        company
        if record.company == "Unknown Company"
        and company != "Unknown Company"
        else record.company
    )
    next_role = (
        role
        if record.role == "Unknown Role" and role != "Unknown Role"
        else record.role
    )
    next_status = _display_status(
        record.status, record.auto_status, proposed_status
    )

    application_date = record.application_date or email.date
    if proposed_status == "Applied":
        try:
            existing_date = datetime.strptime(
                application_date, "%Y-%m-%d"
            ).date()
            application_date = min(
                existing_date, email.timestamp.date()
            ).strftime("%Y-%m-%d")
        except ValueError:
            application_date = email.date

    record.values = [
        application_date,
        next_company,
        next_role,
        next_status,
        email.date,
        email.sender,
        email.subject,
        email.gmail_link,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        email.message_id,
        application_key(next_company, next_role),
        proposed_status,
        email.thread_id or record.thread_id,
        email.sender_domain or record.sender_domain,
    ]
    return True


def review_row(
    email: EmailMessage,
    status: str,
    company: str,
    role: str,
    reason: str,
) -> list[str]:
    return [
        email.date,
        status,
        company,
        role,
        email.sender,
        email.subject,
        email.gmail_link,
        reason,
        email.message_id,
        email.thread_id,
    ]


def write_changes(
    sheets: Any,
    settings: Settings,
    existing_updates: Iterable[ApplicationRecord],
    new_applications: Iterable[ApplicationRecord],
    review_rows: list[list[str]],
    processed_rows: list[list[str]],
) -> None:
    updates = [
        record
        for record in existing_updates
        if record.row_number is not None
    ]
    if updates:
        (
            sheets.spreadsheets()
            .values()
            .batchUpdate(
                spreadsheetId=settings.spreadsheet_id,
                body={
                    "valueInputOption": "USER_ENTERED",
                    "data": [
                        {
                            "range": (
                                f"'{settings.applications_sheet}'!"
                                f"A{record.row_number}:N{record.row_number}"
                            ),
                            "values": [record.values],
                        }
                        for record in updates
                    ],
                },
            )
            .execute()
        )

    new_values = [record.values for record in new_applications]
    if new_values:
        (
            sheets.spreadsheets()
            .values()
            .append(
                spreadsheetId=settings.spreadsheet_id,
                range=f"'{settings.applications_sheet}'!A:N",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": new_values},
            )
            .execute()
        )

    if review_rows:
        (
            sheets.spreadsheets()
            .values()
            .append(
                spreadsheetId=settings.spreadsheet_id,
                range=f"'{settings.review_sheet}'!A:J",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": review_rows},
            )
            .execute()
        )

    if processed_rows:
        (
            sheets.spreadsheets()
            .values()
            .append(
                spreadsheetId=settings.spreadsheet_id,
                range=f"'{settings.processed_sheet}'!A:C",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": processed_rows},
            )
            .execute()
        )
