"""Company/role extraction and conservative record matching."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from email.utils import parseaddr
from typing import Iterable, Optional

from .models import ApplicationRecord, EmailMessage


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

GENERIC_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "hotmail.com",
    "yahoo.com",
}

GENERIC_DISPLAY_NAMES = {
    "recruiting",
    "recruitment",
    "talent",
    "talent team",
    "talent acquisition",
    "careers",
    "hiring team",
    "human resources",
    "hr",
    "jobs",
    "no reply",
    "noreply",
}


def _clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .,:;-–|")


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _domain_is_ats(domain: str) -> bool:
    return any(
        domain == ats or domain.endswith(f".{ats}")
        for ats in ATS_DOMAINS
    )


def _company_from_text(text: str) -> Optional[str]:
    patterns = [
        r"thank you for applying to\s+([A-Z][A-Za-z0-9&.'\- ]{1,70})",
        r"application (?:to|with|at)\s+([A-Z][A-Za-z0-9&.'\- ]{1,70})",
        r"your application with\s+([A-Z][A-Za-z0-9&.'\- ]{1,70})",
        r"interest in joining\s+([A-Z][A-Za-z0-9&.'\- ]{1,70})",
        r"invited by\s+([A-Z][A-Za-z0-9&.'\- ]{1,70})",
        r"on behalf of\s+([A-Z][A-Za-z0-9&.'\- ]{1,70})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        company = re.split(
            r"[.!|,\n]|\s+for\s+(?:the\s+)?",
            match.group(1),
            maxsplit=1,
        )[0]
        company = _clean(company)
        if 2 <= len(company) <= 70:
            return company
    return None


def extract_company(email: EmailMessage) -> str:
    text = f"{email.subject}\n{email.body[:4000]}"
    parsed_from_text = _company_from_text(text)

    if _domain_is_ats(email.sender_domain):
        return parsed_from_text or "Unknown Company"

    display_name = parseaddr(email.sender)[0]
    display_name = re.sub(
        r"\b(recruiting|recruitment|talent acquisition|"
        r"talent team|careers|hiring team|human resources|"
        r"hr team|jobs)\b",
        "",
        display_name,
        flags=re.IGNORECASE,
    )
    display_name = _clean(display_name)

    if (
        display_name
        and _normalize(display_name) not in GENERIC_DISPLAY_NAMES
        and len(display_name) >= 2
    ):
        return display_name

    if parsed_from_text:
        return parsed_from_text

    domain = email.sender_domain
    if domain and domain not in GENERIC_DOMAINS:
        return domain.split(".")[0].replace("-", " ").title()

    return "Unknown Company"


def extract_role(email: EmailMessage) -> str:
    text = f"{email.subject}\n{email.body[:5000]}"
    patterns = [
        r"(?:job title|position|role)\s*[:\-]\s*([^\n|]{2,100})",
        r"application for (?:the )?(.+?)(?: position| role| at | with |\||\n|$)",
        r"applied (?:for|to) (?:the )?(.+?)(?: position| role| at | with |\||\n|$)",
        r"your application for (?:the )?(.+?)(?: position| role| at | with |\||\n|$)",
        r"candidate for (?:the )?(.+?)(?: position| role| at | with |\||\n|$)",
        r"assessment for (?:the )?(.+?)(?: position| role| at | with |\||\n|$)",
        r"interview for (?:the )?(.+?)(?: position| role| at | with |\||\n|$)",
        r"offer for (?:the )?(.+?)(?: position| role| at | with |\||\n|$)",
    ]
    for pattern in patterns:
        match = re.search(
            pattern, text, flags=re.IGNORECASE | re.MULTILINE
        )
        if not match:
            continue
        role = _clean(match.group(1))
        role = re.sub(
            r"\b(application received|application confirmation|"
            r"application update|status update)\b",
            "",
            role,
            flags=re.IGNORECASE,
        )
        role = _clean(role)
        if 2 <= len(role) <= 100:
            return role

    subject_parts = re.split(r"\s[-–|:]\s", email.subject)
    ignored = (
        "application",
        "thank you",
        "interview",
        "assessment",
        "update",
        "received",
        "candidate",
        "offer",
    )
    for part in subject_parts:
        role = _clean(part)
        if (
            3 <= len(role) <= 100
            and not any(term in role.lower() for term in ignored)
        ):
            return role
    return "Unknown Role"


def application_key(company: str, role: str) -> str:
    raw = f"{company}|{role}".lower()
    return re.sub(r"[^a-z0-9]+", "-", raw).strip("-")


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(
        None, _normalize(left), _normalize(right)
    ).ratio()


def find_matching_application(
    email: EmailMessage,
    company: str,
    role: str,
    records: Iterable[ApplicationRecord],
) -> Optional[ApplicationRecord]:
    candidates = list(records)

    same_thread = [
        record
        for record in candidates
        if record.thread_id and record.thread_id == email.thread_id
    ]
    if len(same_thread) == 1:
        return same_thread[0]

    key = application_key(company, role)
    exact = [
        record for record in candidates if record.application_key == key
    ]
    if len(exact) == 1:
        return exact[0]

    scored: list[tuple[float, ApplicationRecord]] = []
    for record in candidates:
        company_score = _similarity(company, record.company)
        role_score = _similarity(role, record.role)
        domain_bonus = (
            0.12
            if email.sender_domain
            and record.sender_domain
            and email.sender_domain == record.sender_domain
            else 0.0
        )

        if role == "Unknown Role":
            if company_score >= 0.88:
                scored.append((company_score + domain_bonus, record))
            continue

        if company == "Unknown Company":
            if role_score >= 0.88 and domain_bonus:
                scored.append((role_score + domain_bonus, record))
            continue

        score = 0.55 * company_score + 0.45 * role_score + domain_bonus
        if company_score >= 0.72 and role_score >= 0.62:
            scored.append((score, record))

    if not scored:
        return None

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best = scored[0]
    if len(scored) > 1 and best_score - scored[1][0] < 0.08:
        return None
    return best if best_score >= 0.76 else None
