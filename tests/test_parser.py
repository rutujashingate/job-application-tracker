from datetime import datetime, timezone

from job_tracker.models import ApplicationRecord, EmailMessage
from job_tracker.parser import (
    application_key,
    extract_company,
    extract_role,
    find_matching_application,
)


def email(
    subject: str,
    body: str,
    sender: str = "OpenAI Hiring Team <no-reply@ashbyhq.com>",
    thread_id: str = "rejection-thread",
) -> EmailMessage:
    return EmailMessage(
        message_id="message-1",
        thread_id=thread_id,
        sender=sender,
        subject=subject,
        body=body,
        timestamp=datetime(2026, 7, 10, tzinfo=timezone.utc),
    )


def application(
    company: str,
    role: str,
    status: str = "Applied",
    row_number: int = 2,
    thread_id: str = "application-thread",
) -> ApplicationRecord:
    return ApplicationRecord(
        row_number=row_number,
        values=[
            "2026-07-08",
            company,
            role,
            status,
            "2026-07-08",
            "sender@example.com",
            "Application received",
            "https://example.com",
            "2026-07-08 12:00:00",
            "old-message",
            application_key(company, role),
            status,
            thread_id,
            "openai.com",
        ],
    )


def test_extracts_company_and_role_from_rejection():
    message = email(
        "OpenAI Application Update for Candidate",
        "Thanks for applying to OpenAI! We appreciate the time you invested "
        "in applying for Full-Stack Software Engineer, Applied Foundations. "
        "After careful consideration, we regret to inform you that we have "
        "decided not to move forward with your candidacy.",
    )

    company = extract_company(message)
    assert company == "OpenAI"
    assert extract_role(message, company) == (
        "Full-Stack Software Engineer, Applied Foundations"
    )


def test_extracts_role_without_confirmation_boilerplate():
    message = email(
        "Thank you for applying to Glean",
        "We received your application for Software Engineer, AI "
        "Infrastructure, and we are delighted that you considered our team.",
        "Glean <no-reply@us.greenhouse-mail.io>",
    )

    company = extract_company(message)
    assert company == "Glean"
    assert extract_role(message, company) == "Software Engineer, AI Infrastructure"


def test_extracts_workday_company_and_role_from_rejection():
    message = email(
        "Thank you for your interest ReliaQuest!",
        "Thank you for taking the time to apply for the Associate Software "
        "Engineer position. After reviewing your background, we've decided "
        "to move forward with other candidates. We appreciate your interest "
        "in joining our team. ReliaQuest Business Process: Job Application: "
        "Candidate - R15047 Associate Software Engineer",
        "reliaquest@myworkday.com",
    )

    company = extract_company(message)
    assert company == "ReliaQuest"
    assert extract_role(message, company) == "Associate Software Engineer"


def test_matches_unique_company_row_when_old_role_is_unknown():
    message = email(
        "OpenAI Application Update for Candidate",
        "Thanks for applying to OpenAI. We regret to inform you that we "
        "decided not to move forward with your candidacy.",
    )
    record = application("OpenAI", "Unknown Role")

    match = find_matching_application(
        message,
        "OpenAI",
        "Full-Stack Software Engineer",
        [record],
    )

    assert match is record


def test_does_not_match_unknown_email_to_unknown_application():
    message = email(
        "Application update",
        "We regret to inform you that we selected another candidate for the role.",
    )
    record = application("Unknown Company", "Unknown Role")

    assert (
        find_matching_application(
            message,
            "Unknown Company",
            "Unknown Role",
            [record],
        )
        is None
    )
