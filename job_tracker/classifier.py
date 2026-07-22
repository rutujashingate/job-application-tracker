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

REJECTION_PATTERNS = [
    r"\bwe (?:have )?(?:decided|chosen) not to (?:move forward|proceed)\b",
    r"\bwe (?:will not|won't) be moving forward\b",
    r"\bwe (?:cannot|can't|are unable to) move forward\b",
    r"\bwill not be moving forward with your (?:application|candidacy)\b",
    r"\bnot moving forward with your (?:application|candidacy)\b",
    r"\bdecided not to proceed with your application\b",
    r"\bdecided to move forward with other candidates\b",
    r"\bdecided to move ahead with other candidates\b",
    r"\bwe've decided to move forward with other candidates\b",
    r"\bwe have now filled all of our openings for this role\b",
    r"\bwe have offered this position to another applicant\b",
    r"\bwe have since filled the position\b",
    r"\b(?:moving|move|proceeding) forward with other candidates\b",
    r"\b(?:pursue|proceed with) other candidates?\b",
    r"\b(?:selected|chosen) (?:another|an other|other) candidate\b",
    r"\b(?:you (?:were|are|have been)|your application (?:was|has been)) "
    r"not selected\b",
    r"\byour application has been rejected\b",
    r"\bwe regret to inform you\b",
    r"\bwe regret to advise\b",
    r"\bwe are sorry to inform you\b",
    r"\bthere (?:is|isn't|is not|was|wasn't|was not) an ideal fit at this time\b",
    r"\bwe won't be moving forward with it this time\b",
    r"\bwe will not be moving forward with it this time\b",
    r"\bthe position has been filled\b",
    r"\bwe will not be progressing (?:with )?your (?:application|candidacy)\b",
    r"\bwill not be moving forward with your candidacy at this time\b",
    r"\bwill not be moving forward with your application at this time\b",
    r"\byou were not selected for the next step in the application process\b",
]

# Application confirmations often contain boilerplate such as "If you are not
# selected ...". Remove that conditional wording before looking for a direct
# rejection so an Applied email does not become a false Rejected update.
HYPOTHETICAL_REJECTION_PATTERNS = [
    r"\bif you are not selected for (?:this|the) position\b",
    r"\bif your application is not selected\b",
    r"\bshould you not be selected for (?:this|the) position\b",
    r"\bonly (?:the )?candidates selected (?:for|to)\b",
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


def _has_rejection_language(text: str) -> bool:
    direct_text = text
    for pattern in HYPOTHETICAL_REJECTION_PATTERNS:
        direct_text = re.sub(pattern, " ", direct_text)
    return any(
        re.search(pattern, direct_text)
        for pattern in REJECTION_PATTERNS
    )


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

    if _has_rejection_language(text):
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
