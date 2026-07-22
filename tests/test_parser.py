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


def test_extracts_ats_company_and_role_from_title_subject():
    message = email(
        "Web Content Coordinator|R0428959 at DaVita",
        "Thank you for applying!",
        "Dani from DaVita Kidney Care <DavitaRecruiting@paradox.ai>",
    )

    company = extract_company(message)
    assert company == "DaVita"
    assert extract_role(message, company) == "Web Content Coordinator"


def test_extracts_company_from_boilerplate_rejection_subject():
    message = email(
        "Thanks for applying to Roblox - we hope to connect again soon",
        "We have now filled all of our openings for this role and will not "
        "be moving forward with your candidacy at this time.",
        "no-reply@roblox.com",
    )

    assert extract_company(message) == "Roblox"


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


def test_rejected_match_can_fall_back_to_single_company_row():
    message = email(
        "Thank you for your interest ReliaQuest!",
        "Thank you for taking the time to apply for the Associate Software "
        "Engineer position. After reviewing your background, we've decided "
        "to move forward with other candidates.",
        "reliaquest@myworkday.com",
    )
    record = application("ReliaQuest", "Unknown Role")

    match = find_matching_application(
        message,
        "ReliaQuest",
        "Associate Software Engineer",
        [record],
        proposed_status="Rejected",
    )

    assert match is record


def test_matches_boilerplate_company_variants():
    message = email(
        "Thank you for your interest in Signals",
        "We regret to inform you that we selected another candidate for the "
        "role.",
        "Pete Ketchum II <notifications@app.bamboohr.com>",
    )
    record = application("Signals and", "UX/UI Creator")

    match = find_matching_application(
        message,
        "Signals",
        "Unknown Role",
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
