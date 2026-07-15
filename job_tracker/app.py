"""CLI orchestration."""

from __future__ import annotations

import argparse
import fcntl
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from googleapiclient.errors import HttpError

from .auth import build_services
from .classifier import classify_email
from .config import Settings
from .gmail_client import build_query, list_message_ids, read_message
from .models import ApplicationRecord
from .parser import (
    extract_company,
    extract_role,
    find_matching_application,
)
from .sheets_client import (
    clear_tracking_data,
    create_application,
    ensure_structure,
    get_applications,
    get_processed_ids,
    review_row,
    update_application,
    write_changes,
)


@contextmanager
def single_instance(lock_file: Path) -> Iterator[None]:
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with lock_file.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(
                handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
            )
        except BlockingIOError:
            print("Another tracker run is already active; exiting.")
            raise SystemExit(0)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track real Gmail job-application updates in Google Sheets."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview decisions without writing any rows.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print ignored-message reasons.",
    )
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Classify all matching history again.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help=(
            "Clear tracker-created rows and rebuild from START_DATE. "
            "Requires --confirm-rebuild."
        ),
    )
    parser.add_argument(
        "--confirm-rebuild",
        action="store_true",
        help="Required safety flag for --rebuild.",
    )
    return parser.parse_args()


def _record_change(
    record: ApplicationRecord,
    changed_existing: dict[int, ApplicationRecord],
) -> None:
    if record.row_number is not None:
        changed_existing[record.row_number] = record


def run(args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    settings.validate()

    if args.rebuild and args.dry_run:
        raise ValueError("--rebuild cannot be combined with --dry-run.")
    if args.rebuild and not args.confirm_rebuild:
        raise ValueError(
            "--rebuild deletes tracker-created row values. "
            "Run with --confirm-rebuild after backing up the sheet."
        )

    gmail, sheets = build_services(settings)
    ensure_structure(sheets, settings)

    if args.rebuild:
        clear_tracking_data(sheets, settings)
        print("Cleared tracker rows; rebuilding from START_DATE.")

    processed_ids = (
        set()
        if args.reprocess or args.rebuild
        else get_processed_ids(sheets, settings)
    )
    records = get_applications(sheets, settings)

    candidate_ids = list_message_ids(
        gmail, build_query(settings.start_date)
    )
    pending_ids = [
        message_id
        for message_id in candidate_ids
        if message_id not in processed_ids
    ]
    print(
        f"Gmail returned {len(candidate_ids)} candidates; "
        f"{len(pending_ids)} need inspection."
    )

    emails = []
    failed_reads = 0
    for message_id in pending_ids:
        try:
            emails.append(read_message(gmail, message_id))
        except HttpError as exc:
            failed_reads += 1
            print(f"Could not read Gmail message {message_id}: {exc}")

    emails.sort(key=lambda item: item.timestamp)

    changed_existing: dict[int, ApplicationRecord] = {}
    new_records: list[ApplicationRecord] = []
    reviews: list[list[str]] = []
    processed_rows: list[list[str]] = []
    ignored = applied = updated = 0

    for email in emails:
        classification = classify_email(email, settings)

        if not classification.included:
            ignored += 1
            if args.verbose:
                print(
                    f"IGNORE | {email.subject} | {classification.reason}"
                )
            if not args.dry_run:
                processed_rows.append(
                    [
                        email.message_id,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        email.subject,
                    ]
                )
            continue

        company = extract_company(email)
        role = extract_role(email, company)
        match = find_matching_application(
            email, company, role, records
        )

        if classification.status == "Applied":
            if match is None:
                record = create_application(
                    email, company, role, classification.status
                )
                records.append(record)
                new_records.append(record)
                applied += 1
                print(
                    f"NEW    | {email.date} | {company} | {role} | Applied"
                )
            elif update_application(
                match, email, company, role, classification.status
            ):
                _record_change(match, changed_existing)
                updated += 1

        elif match is not None:
            if update_application(
                match, email, company, role, classification.status
            ):
                _record_change(match, changed_existing)
                updated += 1
                print(
                    f"UPDATE | {email.date} | {match.company} | "
                    f"{match.role} | {classification.status}"
                )
        else:
            reviews.append(
                review_row(
                    email,
                    classification.status,
                    company,
                    role,
                    (
                        "Strong lifecycle wording was found, but no "
                        "existing application matched. Kept out of Applications."
                    ),
                )
            )
            print(
                f"REVIEW | {email.date} | {company} | {role} | "
                f"{classification.status}"
            )

        if not args.dry_run:
            processed_rows.append(
                [
                    email.message_id,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    email.subject,
                ]
            )

    if args.dry_run:
        print(
            "\nDry run complete; Sheets were not changed.\n"
            f"New applications: {applied}\n"
            f"Matched status updates: {updated}\n"
            f"Sent to Review: {len(reviews)}\n"
            f"Ignored: {ignored}\n"
            f"Failed reads: {failed_reads}"
        )
        return 0

    write_changes(
        sheets,
        settings,
        changed_existing.values(),
        new_records,
        reviews,
        processed_rows,
    )
    print(
        "\nDone.\n"
        f"New applications: {len(new_records)}\n"
        f"Updated applications: {len(changed_existing)}\n"
        f"Sent to Review: {len(reviews)}\n"
        f"Ignored: {ignored}\n"
        f"Processed records: {len(processed_rows)}\n"
        f"Failed reads: {failed_reads}"
    )
    return 0


def main() -> int:
    args = parse_args()
    try:
        settings = Settings.from_env()
        with single_instance(settings.lock_file):
            return run(args)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except HttpError as exc:
        print(f"Google API error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1
