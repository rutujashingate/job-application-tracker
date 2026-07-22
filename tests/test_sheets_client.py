from datetime import datetime, timezone

from job_tracker.models import ApplicationRecord, EmailMessage
from job_tracker.sheets_client import (
    _status_format_request,
    _status_conditional_format_rule,
    update_application,
)


def test_rejection_changes_applied_row_in_place():
    record = ApplicationRecord(
        row_number=7,
        values=[
            "2026-07-08",
            "OpenAI",
            "Full-Stack Software Engineer",
            "Applied",
            "2026-07-08",
            "sender@example.com",
            "Application received",
            "https://example.com/old",
            "2026-07-08 12:00:00",
            "old-message",
            "openai-full-stack-software-engineer",
            "Applied",
            "application-thread",
            "openai.com",
        ],
    )
    rejection = EmailMessage(
        message_id="rejection-message",
        thread_id="rejection-thread",
        sender="OpenAI Hiring Team <no-reply@ashbyhq.com>",
        subject="OpenAI Application Update",
        body="We decided not to move forward with your candidacy.",
        timestamp=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )

    changed = update_application(
        record,
        rejection,
        "OpenAI",
        "Full-Stack Software Engineer",
        "Rejected",
    )

    assert changed
    assert record.row_number == 7
    assert record.status == "Rejected"
    assert record.auto_status == "Rejected"
    assert record.values[9] == "rejection-message"


def test_rejection_overwrites_manual_status():
    record = ApplicationRecord(
        row_number=7,
        values=[
            "2026-07-08",
            "OpenAI",
            "Full-Stack Software Engineer",
            "Interview",
            "2026-07-08",
            "sender@example.com",
            "Application received",
            "https://example.com/old",
            "2026-07-08 12:00:00",
            "old-message",
            "openai-full-stack-software-engineer",
            "Applied",
            "application-thread",
            "openai.com",
        ],
    )
    rejection = EmailMessage(
        message_id="rejection-message",
        thread_id="rejection-thread",
        sender="OpenAI Hiring Team <no-reply@ashbyhq.com>",
        subject="OpenAI Application Update",
        body="We decided not to move forward with your candidacy.",
        timestamp=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )

    changed = update_application(
        record,
        rejection,
        "OpenAI",
        "Full-Stack Software Engineer",
        "Rejected",
    )

    assert changed
    assert record.status == "Rejected"
    assert record.auto_status == "Rejected"


def test_status_format_request_targets_data_row():
    request = _status_format_request(42, 7, "Rejected")

    assert request is not None
    cell_range = request["repeatCell"]["range"]
    assert cell_range["sheetId"] == 42
    assert cell_range["startRowIndex"] == 6
    assert cell_range["endRowIndex"] == 7
    assert cell_range["startColumnIndex"] == 3
    assert cell_range["endColumnIndex"] == 4


def test_status_conditional_format_rule_targets_status_column():
    rule = _status_conditional_format_rule(42, "Rejected")

    assert rule is not None
    cell_range = rule["ranges"][0]
    assert cell_range["sheetId"] == 42
    assert cell_range["startRowIndex"] == 1
    assert cell_range["startColumnIndex"] == 3
    assert cell_range["endColumnIndex"] == 4

    condition = rule["booleanRule"]["condition"]
    assert condition["type"] == "TEXT_EQ"
    assert condition["values"][0]["userEnteredValue"] == "Rejected"

    cell_format = rule["booleanRule"]["format"]
    assert cell_format["backgroundColor"] == {
        "red": 0.98,
        "green": 0.85,
        "blue": 0.85,
    }
    assert cell_format["textFormat"]["bold"] is True
