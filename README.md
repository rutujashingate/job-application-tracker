# Job Application Email Tracker

A privacy-first Python tool that reads real job-application lifecycle emails
from Gmail and keeps a Google Sheet up to date.

## Accuracy-first behavior

Only strong application-confirmation language can create a row in
`Applications`.

Assessment, interview, rejection, and offer messages update a row only when
they match an existing application. Unmatched updates go to `Review`, so a
community assessment or consultancy marketing email cannot silently change an
application.

The tracker excludes job alerts, recommended openings, talent-community
newsletters, practice assessments, and career-coaching marketing.

## Sheet tabs

- `Applications`: one row per application.
- `Review`: strong update wording that could not be safely matched.
- `ProcessedEmails`: Gmail message IDs already inspected.

`Status` is user editable. `Auto Status` records the tracker's latest decision.
A manual `Status` change is preserved.

## Structure

```text
tracker.py
job_tracker/
  app.py
  auth.py
  classifier.py
  config.py
  gmail_client.py
  models.py
  parser.py
  sheets_client.py
scripts/
  install_launch_agent.sh
  uninstall_launch_agent.sh
tests/
  test_classifier.py
```

## Install

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

Keep your private Desktop OAuth file in the project directory as:

```text
credentials.json
```

Create local configuration:

```bash
cp .env.example .env
```

Set:

```env
SPREADSHEET_ID=YOUR_REAL_SPREADSHEET_ID
START_DATE=2025/06/01
```

## Preview

```bash
python3 tracker.py --dry-run --verbose
```

## Rebuild incorrect old results

Back up your sheet first, then run:

```bash
python3 tracker.py --rebuild --confirm-rebuild
```

This clears values from the three tracker tabs and rebuilds from `START_DATE`.

## Normal run

```bash
python3 tracker.py
```

## Tests

```bash
pytest
```

## Automatic background updates on macOS

After one successful manual run:

```bash
chmod +x scripts/*.sh
./scripts/install_launch_agent.sh 600
```

This installs a LaunchAgent that starts after login and runs every 10 minutes.

Status:

```bash
launchctl print gui/$(id -u)/com.rutuja.jobapplicationtracker
```

Logs:

```bash
tail -f logs/job-tracker.log
tail -f logs/job-tracker-error.log
```

Uninstall:

```bash
./scripts/uninstall_launch_agent.sh
```

A local process cannot run while the Mac is shut down or asleep. It resumes
when the user session is active again. Always-online, near-real-time updates
require a hosted service and Gmail push notifications through Cloud Pub/Sub.

## Custom blocking

Add unwanted sender domains to your private `.env`:

```env
BLOCKED_SENDER_DOMAINS=consultancy.example,community.example
```

## GitHub safety

Never commit:

```text
credentials.json
token.json
.env
venv/
logs/
```

Before pushing:

```bash
git status
git diff --cached
git check-ignore -v credentials.json token.json .env
```

Safe initial add:

```bash
git init
git add tracker.py job_tracker scripts tests README.md LICENSE \
  requirements.txt .gitignore .env.example
git status
git commit -m "Initial modular release"
```
