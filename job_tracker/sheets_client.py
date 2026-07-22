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

STATUS_COLUMN_INDEX = 3

STATUS_CELL_FORMATS: dict[str, dict[str, Any]] = {
    "Applied": {
        "backgroundColor": {"red": 1.0, "green": 0.93, "blue": 0.67},
    },
    "Assessment": {
        "backgroundColor": {"red": 0.84, "green": 0.93, "blue": 0.78},
    },
    "Interview": {
        "backgroundColor": {"red": 0.82, "green": 0.90, "blue": 0.97},
    },
    "Rejected": {
        "backgroundColor": {"red": 0.98, "green": 0.85, "blue": 0.85},
    },
    "Offer": {
        "backgroundColor": {"red": 0.84, "green": 0.93, "blue": 0.84},
    },
    "Withdrawn": {
        "backgroundColor": {"red": 0.92, "green": 0.92, "blue": 0.92},
    },
}


def _status_conditional_format_rule(
    sheet_id: int,
    status: str,
) -> dict[str, Any] | None:
    status_format = STATUS_CELL_FORMATS.get(status)
    if not status_format:
        return None

    return {
        "ranges": [
            {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "startColumnIndex": STATUS_COLUMN_INDEX,
                "endColumnIndex": STATUS_COLUMN_INDEX + 1,
            }
        ],
        "booleanRule": {
            "condition": {
                "type": "TEXT_EQ",
                "values": [{"userEnteredValue": status}],
            },
            "format": {
                **status_format,
                "textFormat": {"bold": True},
            },
        },
    }


def _rule_matches_status(
    rule: dict[str, Any],
    sheet_id: int,
    status: str,
) -> bool:
    condition = rule.get("booleanRule", {}).get("condition", {})
    if condition.get("type") != "TEXT_EQ":
        return False

    values = condition.get("values", [])
    if not values or values[0].get("userEnteredValue") != status:
        return False

    ranges = rule.get("ranges", [])
    if not ranges:
        return False

    first_range = ranges[0]
    return (
        first_range.get("sheetId") == sheet_id
        and first_range.get("startRowIndex", 1) == 1
        and first_range.get("startColumnIndex") == STATUS_COLUMN_INDEX
        and first_range.get("endColumnIndex", STATUS_COLUMN_INDEX + 1)
        == STATUS_COLUMN_INDEX + 1
    )


def _ensure_status_conditional_formats(
    sheets: Any,
    settings: Settings,
    sheet_id: int,
    existing_rules: list[dict[str, Any]],
) -> None:
    update_requests: list[dict[str, Any]] = []
    add_requests: list[dict[str, Any]] = []
    status_rule_indexes: dict[str, int] = {}

    for index, rule in enumerate(existing_rules):
        for status in STATUS_OPTIONS:
            if _rule_matches_status(rule, sheet_id, status):
                status_rule_indexes[status] = index
                break

    for status in STATUS_OPTIONS:
        desired_rule = _status_conditional_format_rule(sheet_id, status)
        if desired_rule is None:
            continue

        existing_index = status_rule_indexes.get(status)
        if existing_index is None:
            add_requests.append(
                {
                    "addConditionalFormatRule": {
                        "index": 0,
                        "rule": desired_rule,
                    }
                }
            )
            continue

        if existing_rules[existing_index] != desired_rule:
            update_requests.append(
                {
                    "updateConditionalFormatRule": {
                        "index": existing_index,
                        "rule": desired_rule,
                    }
                }
            )

    if update_requests:
        (
            sheets.spreadsheets()
            .batchUpdate(
                spreadsheetId=settings.spreadsheet_id,
                body={"requests": update_requests},
            )
            .execute()
        )

    if add_requests:
        (
            sheets.spreadsheets()
            .batchUpdate(
                spreadsheetId=settings.spreadsheet_id,
                body={"requests": add_requests},
            )
            .execute()
        )


def ensure_structure(sheets: Any, settings: Settings) -> int:
    metadata = (
        sheets.spreadsheets()
        .get(
            spreadsheetId=settings.spreadsheet_id,
            fields=(
                "sheets.properties.sheetId,"
                "sheets.properties.title,"
                "sheets.conditionalFormats"
            ),
        )
        .execute()
    )
    sheet_by_title = {
        sheet["properties"]["title"]: sheet
        for sheet in metadata.get("sheets", [])
    }
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

    _ensure_status_conditional_formats(
        sheets,
        settings,
        title_to_id[settings.applications_sheet],
        sheet_by_title.get(settings.applications_sheet, {}).get(
            "conditionalFormats", []
        ),
    )

    return title_to_id[settings.applications_sheet]


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


def _status_format_request(
    sheet_id: int,
    row_number: int,
    status: str,
) -> dict[str, Any] | None:
    status_format = STATUS_CELL_FORMATS.get(status)
    if not status_format:
        return None

    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row_number - 1,
                "endRowIndex": row_number,
                "startColumnIndex": STATUS_COLUMN_INDEX,
                "endColumnIndex": STATUS_COLUMN_INDEX + 1,
            },
            "cell": {
                "userEnteredFormat": {
                    **status_format,
                    "textFormat": {"bold": True},
                }
            },
            "fields": (
                "userEnteredFormat.backgroundColor,"
                "userEnteredFormat.textFormat.bold"
            ),
        }
    }


def _apply_status_formats(
    sheets: Any,
    settings: Settings,
    sheet_id: int,
    rows: Iterable[tuple[int, str]],
) -> None:
    requests = [
        request
        for row_number, status in rows
        if (request := _status_format_request(sheet_id, row_number, status))
    ]
    if not requests:
        return

    (
        sheets.spreadsheets()
        .batchUpdate(
            spreadsheetId=settings.spreadsheet_id,
            body={"requests": requests},
        )
        .execute()
    )


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
    if proposed_status == "Rejected":
        next_status = "Rejected"
    else:
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
    applications_sheet_id: int,
    existing_application_count: int,
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
    new_records = list(new_applications)
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

    new_values = [record.values for record in new_records]
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

    status_rows = [
        (record.row_number, record.values[3])
        for record in updates
        if record.row_number is not None
    ]
    status_rows.extend(
        (
            existing_application_count + 2 + index,
            record.values[3],
        )
        for index, record in enumerate(new_records)
    )
    _apply_status_formats(
        sheets,
        settings,
        applications_sheet_id,
        status_rows,
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
