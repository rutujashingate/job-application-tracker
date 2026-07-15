from datetime import datetime, timezone

from job_tracker.models import ApplicationRecord, EmailMessage
from job_tracker.sheets_client import update_application


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
