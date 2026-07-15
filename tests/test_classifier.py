from datetime import datetime, timezone
from pathlib import Path

from job_tracker.classifier import classify_email
from job_tracker.config import Settings
from job_tracker.models import EmailMessage


def settings() -> Settings:
    return Settings(
        base_dir=Path("."),
        spreadsheet_id="test",
        applications_sheet="Applications",
        processed_sheet="ProcessedEmails",
        review_sheet="Review",
        start_date="2025/06/01",
        credentials_file=Path("credentials.json"),
        token_file=Path("token.json"),
        lock_file=Path(".lock"),
        blocked_sender_domains=(),
        trusted_sender_domains=(),
    )


def email(
    subject: str,
    body: str,
    sender: str = "Acme Recruiting <jobs@acme.com>",
) -> EmailMessage:
    return EmailMessage(
        message_id="m1",
        thread_id="t1",
        sender=sender,
        subject=subject,
        body=body,
        timestamp=datetime.now(timezone.utc),
    )


def test_job_application_confirmation():
    result = classify_email(
        email(
            "Application received",
            "Thank you for applying for the Software Engineer position.",
        ),
        settings(),
    )
    assert result.status == "Applied"


def test_financial_aid_application_is_ignored():
    result = classify_email(
        email(
            "Application received",
            "Your Coursera financial aid application has been received.",
            "Coursera <no-reply@coursera.org>",
        ),
        settings(),
    )
    assert result.status is None


def test_loan_rejection_is_ignored():
    result = classify_email(
        email(
            "Unfortunately, we are not moving forward",
            "Your personal loan application was not approved.",
            "Finance Team <support@bank.example>",
        ),
        settings(),
    )
    assert result.status is None


def test_job_rejection():
    result = classify_email(
        email(
            "Update on your Software Engineer application",
            "Unfortunately, we will not be moving forward with your "
            "application for the Software Engineer position.",
        ),
        settings(),
    )
    assert result.status == "Rejected"


def test_other_candidates_rejection():
    result = classify_email(
        email(
            "Application update",
            "For this role, we are moving forward with other candidates.",
        ),
        settings(),
    )
    assert result.status == "Rejected"


def test_application_confirmation_with_hypothetical_rejection_is_applied():
    result = classify_email(
        email(
            "Thank you for applying to Glean",
            "We received your application for Software Engineer, AI "
            "Infrastructure, and we will review it. If you are not selected "
            "for this position, keep an eye on our jobs page.",
            "Glean <no-reply@us.greenhouse-mail.io>",
        ),
        settings(),
    )
    assert result.status == "Applied"


def test_regret_to_inform_rejection():
    result = classify_email(
        email(
            "Application update",
            "After careful consideration, we regret to inform you that we "
            "selected another candidate for this role.",
        ),
        settings(),
    )
    assert result.status == "Rejected"


def test_consultancy_offer_marketing_is_ignored():
    result = classify_email(
        email(
            "Let's get you your offer",
            "Book a consultation with our career services.",
            "Career Community <hello@coaching.example>",
        ),
        settings(),
    )
    assert result.status is None


def test_community_assessment_is_ignored():
    result = classify_email(
        email(
            "Weekly community coding assessment",
            "Join this week's community challenge and practice assessment.",
            "Builder Community <news@community.example>",
        ),
        settings(),
    )
    assert result.status is None


def test_direct_job_assessment():
    result = classify_email(
        email(
            "Technical assessment for your application",
            "The next step in the hiring process is an assessment. "
            "Please complete your technical assessment for the role.",
        ),
        settings(),
    )
    assert result.status == "Assessment"
    assert result.requires_existing_application
