"""Conservative rule-based application lifecycle classifier."""

from __future__ import annotations

import re

from .config import Settings
from .models import Classification, EmailMessage


ATS_DOMAINS = (
    "greenhouse.io",
    "greenhouse-mail.io",
    "lever.co",
    "ashbyhq.com",
    "workday.com",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "icims.com",
    "jobvite.com",
    "teamtailor.com",
    "breezy.hr",
    "workablemail.com",
    "rippling.com",
    "bamboohr.com",
    "taleo.net",
    "oraclecloud.com",
    "successfactors.com",
    "eightfold.ai",
    "phenompeople.com",
)

# Strong evidence that the email is about employment, not another type of
# application such as financial aid, admissions, housing, or a course.
JOB_CONTEXT_PHRASES = [
    "job application",
    "applied for the job",
    "applied to the job",
    "applied for the role",
    "applied to the role",
    "applied for the position",
    "applied to the position",
    "your application for the role",
    "your application for the position",
    "the position",
    "the role",
    "job title",
    "candidate",
    "candidacy",
    "hiring process",
    "hiring team",
    "recruiting process",
    "recruiter",
    "employment",
    "interview",
]

EMPLOYMENT_SENDER_MARKERS = [
    "recruiting",
    "recruitment",
    "talent acquisition",
    "talent team",
    "hiring team",
    "careers",
    "jobs",
    "recruiter",
]

# Check these first. A non-job application should never become a job record,
# even when it contains words such as application, rejected, or unfortunately.
NON_JOB_APPLICATION_PHRASES = [
    "financial aid",
    "financial assistance",
    "tuition assistance",
    "student aid",
    "fafsa",
    "loan application",
    "personal loan",
    "student loan",
    "credit application",
    "credit card application",
    "mortgage application",
    "financing application",
    "rental application",
    "apartment application",
    "housing application",
    "admission application",
    "college application",
    "university application",
    "school application",
    "course application",
    "course enrollment",
    "enrollment application",
    "program application",
    "certificate program",
    "scholarship application",
    "grant application",
    "visa application",
    "passport application",
    "insurance application",
    "insurance claim",
    "membership application",
    "benefits application",
    "refund request",
    "payment application",
]

APPLICATION_PHRASES = [
    "thank you for applying",
    "thanks for applying",
    "application received",
    "we received your application",
    "received your application",
    "your application has been received",
    "application successfully submitted",
    "successfully submitted your application",
    "job application received",
    "you applied for the role",
    "you applied for the position",
    "you applied for this job",
]

REJECTION_PHRASES = [
    "unfortunately, we will not be moving forward",
    "unfortunately we will not be moving forward",
    "will not be moving forward with your application",
    "we have decided not to move forward",
    "decided not to proceed with your application",
    "moving forward with other candidates",
    "move forward with other candidates",
    "pursue other candidates",
    "not selected for the position",
    "not selected for this position",
    "your application has been rejected",
    "we are unable to move forward with your candidacy",
]

INTERVIEW_PHRASES = [
    "we would like to invite you to interview",
    "we'd like to invite you to interview",
    "invite you to interview",
    "invitation to interview",
    "schedule an interview",
    "interview availability",
    "schedule a phone screen",
    "schedule a recruiter screen",
    "schedule your technical interview",
    "meet with the hiring team",
]

ASSESSMENT_PHRASES = [
    "invited to complete the coding challenge",
    "invite you to complete the coding challenge",
    "complete your coding challenge",
    "complete the technical assessment",
    "complete your technical assessment",
    "assessment for your application",
    "next step in your application is an assessment",
    "next step in the hiring process is an assessment",
]

OFFER_PHRASES = [
    "we are pleased to offer you",
    "we're pleased to offer you",
    "pleased to extend you an offer",
    "extend an offer of employment",
    "offer of employment for the",
    "attached offer letter",
    "your formal offer letter",
    "congratulations on your offer",
]

MARKETING_AND_COMMUNITY_PHRASES = [
    "jobs you may like",
    "job recommendations",
    "recommended jobs",
    "recommended roles",
    "new jobs for you",
    "job alert",
    "weekly job",
    "daily job",
    "open roles",
    "roles you may be interested in",
    "talent community",
    "community newsletter",
    "career newsletter",
    "weekly challenge",
    "community challenge",
    "practice assessment",
    "mock assessment",
    "skills assessment practice",
    "certification assessment",
    "bootcamp assessment",
    "academy assessment",
    "webinar",
    "workshop",
    "let's get you your offer",
    "lets get you your offer",
    "land your dream offer",
    "get your next offer",
    "offer guaranteed",
    "placement assistance",
    "book a consultation",
    "our career services",
    "we help candidates",
]

SENDER_BLOCK_MARKERS = [
    "newsletter",
    "community",
    "bootcamp",
    "academy",
    "career coach",
    "career services",
    "placement services",
    "consultancy",
    "consulting services",
]


def _normalize(value: str) -> str:
    value = value.replace("’", "'").replace("–", "-")
    value = value.lower()
    return re.sub(r"\s+", " ", value).strip()


def _has_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _is_ats_domain(domain: str) -> bool:
    return any(
        domain == ats
        or domain.endswith(f".{ats}")
        for ats in ATS_DOMAINS
    )


def _has_job_context(
    email: EmailMessage,
    text: str,
    source: str,
) -> bool:
    if _has_any(text, JOB_CONTEXT_PHRASES):
        return True

    if _has_any(source, EMPLOYMENT_SENDER_MARKERS):
        return True

    if email.sender_domain and _is_ats_domain(
        email.sender_domain
    ):
        return True

    return False


def classify_email(
    email: EmailMessage,
    settings: Settings,
) -> Classification:
    text = _normalize(
        f"{email.subject}\n{email.body}"
    )
    source = _normalize(
        f"{email.sender}\n{email.subject}"
    )

    if (
        email.sender_domain
        and email.sender_domain
        in settings.blocked_sender_domains
    ):
        return Classification(
            None,
            "Sender domain is in BLOCKED_SENDER_DOMAINS.",
        )

    if _has_any(text, NON_JOB_APPLICATION_PHRASES):
        return Classification(
            None,
            "A financial, education, housing, admissions, or other "
            "non-employment application was detected.",
        )

    if _has_any(source, SENDER_BLOCK_MARKERS):
        return Classification(
            None,
            "Sender appears to be a community, coaching, or marketing source.",
        )

    if _has_any(
        text,
        MARKETING_AND_COMMUNITY_PHRASES,
    ):
        return Classification(
            None,
            "Marketing, community, practice, or job-alert language detected.",
        )

    if not _has_job_context(email, text, source):
        return Classification(
            None,
            "Lifecycle wording appeared without clear job, role, position, "
            "candidate, hiring, recruiting, or employment context.",
        )

    if _has_any(text, OFFER_PHRASES):
        return Classification(
            "Offer",
            "Direct formal employment-offer wording detected.",
            requires_existing_application=True,
        )

    if _has_any(text, REJECTION_PHRASES):
        return Classification(
            "Rejected",
            "Direct job-rejection wording detected.",
            requires_existing_application=True,
        )

    if _has_any(text, INTERVIEW_PHRASES):
        return Classification(
            "Interview",
            "Direct job-interview invitation detected.",
            requires_existing_application=True,
        )

    if _has_any(text, ASSESSMENT_PHRASES):
        return Classification(
            "Assessment",
            "Direct job assessment tied to an application.",
            requires_existing_application=True,
        )

    if _has_any(text, APPLICATION_PHRASES):
        return Classification(
            "Applied",
            "Direct job-application confirmation detected.",
            requires_existing_application=False,
        )

    return Classification(
        None,
        "No direct job-application lifecycle wording detected.",
    )