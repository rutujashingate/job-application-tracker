<div align="center">

# Job Application Tracker

**Automatically turn Gmail application emails into an organized Google Sheets pipeline.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python\&logoColor=white)](#requirements)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](#contributing)
[![Gmail](https://img.shields.io/badge/Gmail-read--only-EA4335?logo=gmail\&logoColor=white)](#privacy-and-security)
[![Local First](https://img.shields.io/badge/privacy-local--first-6f42c1.svg)](#privacy-and-security)

[Getting Started](#getting-started) ·
[Google OAuth Setup](#google-cloud-and-oauth-setup) ·
[Usage](#usage) ·
[Contributing](#contributing)

</div>

---

## Overview

Job Application Tracker is a local-first Python application that scans Gmail for employment application updates and organizes them in Google Sheets.

It detects application confirmations, assessments, interviews, rejections, and offers while filtering out unrelated messages such as job alerts, course applications, financial-aid emails, community assessments, and career-marketing messages.

The tracker runs locally, uses read-only Gmail access, and does not send your email content to an external AI service.

## Features

* Track job applications from Gmail
* Detect application confirmations and status changes
* Extract company, role, sender, subject, and email dates
* Maintain one Google Sheets row per application
* Preserve manually edited statuses
* Send uncertain matches to a review queue
* Prevent duplicate email processing
* Configure blocked and trusted sender domains
* Rebuild application history from a selected date
* Run automatically in the background on macOS
* Keep OAuth credentials and tokens local

## How it works

The tracker searches Gmail for job-related lifecycle emails.

Application confirmations can create new rows. Assessments, interviews, rejections, and offers update a row only when they can be safely matched to an existing application.

Messages that appear relevant but cannot be matched confidently are placed in the `Review` tab instead of changing an application incorrectly.

## Google Sheets output

The tracker creates and maintains three tabs:

* `Applications` — your application pipeline
* `Review` — relevant emails that could not be matched safely
* `ProcessedEmails` — Gmail message IDs used to prevent duplicates

The `Status` column in `Applications` remains manually editable.

---

## Requirements

Before installing the tracker, make sure you have:

* Python 3.10 or newer
* Git
* A Google account with Gmail
* A Google Cloud project
* A blank Google Sheet
* macOS to use the included background automation scripts

Check your versions:

```bash
python3 --version
git --version
```

---

## Getting started

### 1. Clone the repository

Using HTTPS:

```bash
git clone https://github.com/rutujashingate/job-application-tracker.git
cd job-application-tracker
```

Using SSH:

```bash
git clone git@github.com:rutujashingate/job-application-tracker.git
cd job-application-tracker
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
```

Activate it on macOS or Linux:

```bash
source venv/bin/activate
```

Your terminal should now begin with:

```text
(venv)
```

### 3. Install dependencies

```bash
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create your private environment file

```bash
cp .env.example .env
```

Your real configuration belongs in `.env`.

Do not place private values inside `.env.example`.

---

## Google Cloud and OAuth setup

Each user must create their own Google Cloud project and OAuth credentials.

This repository does not include shared Google credentials.

### 1. Create a Google Cloud project

Open the [Google Cloud Console](https://console.cloud.google.com/).

1. Sign in with the Google account whose Gmail you want to track.
2. Open the project selector at the top.
3. Click **New Project**.
4. Enter a project name such as:

```text
Job Application Tracker
```

5. Click **Create**.
6. Make sure the new project is selected.

### 2. Enable the Gmail API

In Google Cloud Console, open:

```text
APIs & Services
→ Library
```

Search for:

```text
Gmail API
```

Open it and click **Enable**.

### 3. Enable the Google Sheets API

Return to:

```text
APIs & Services
→ Library
```

Search for:

```text
Google Sheets API
```

Open it and click **Enable**.

Both APIs must be enabled in the same Google Cloud project.

### 4. Configure Google Auth Platform

Open:

```text
Google Auth Platform
→ Branding
```

If prompted, click **Get Started**.

Enter:

```text
App name: Job Application Tracker
User support email: your Google account
Developer contact email: your Google account
```

Save the configuration.

### 5. Configure the audience

Open:

```text
Google Auth Platform
→ Audience
```

For a personal Gmail account, select:

```text
External
```

Keep the application in testing mode while using it personally.

Under **Test users**:

1. Click **Add users**.
2. Add the Gmail address you will use with the tracker.
3. Save the changes.

### 6. Configure OAuth data access

Open:

```text
Google Auth Platform
→ Data Access
```

Add the following scopes:

```text
https://www.googleapis.com/auth/gmail.readonly
```

```text
https://www.googleapis.com/auth/spreadsheets
```

The Gmail permission is read-only. The tracker cannot send, delete, archive, label, or modify your emails.

The Sheets permission allows the tracker to create tabs and update spreadsheet values.

### 7. Create a Desktop OAuth client

Open:

```text
Google Auth Platform
→ Clients
```

Click **Create Client**.

Select:

```text
Application type: Desktop app
```

Enter a name such as:

```text
Job Tracker Desktop Client
```

Click **Create**.

Do not choose:

```text
Web application
Service account
API key
```

### 8. Download your OAuth credentials

Download the JSON file for the Desktop app client.

The filename may look like:

```text
client_secret_123456789.apps.googleusercontent.com.json
```

Move it into the project directory and rename it:

```bash
mv ~/Downloads/client_secret_*.json credentials.json
```

Your repository should now contain:

```text
job-application-tracker/
├── credentials.json
├── tracker.py
├── requirements.txt
└── ...
```

Never commit `credentials.json`.

---

## Create a Google Sheet

Create a new blank Google Sheet.

The URL will look similar to:

```text
https://docs.google.com/spreadsheets/d/1ABC123XYZ456/edit
```

The spreadsheet ID is the value between `/d/` and `/edit`:

```text
1ABC123XYZ456
```

You do not need to create the tabs manually. The tracker creates:

```text
Applications
ProcessedEmails
Review
```

---

## Configure the tracker

Open `.env` in your preferred editor.

Using Nano:

```bash
nano .env
```

Using VS Code:

```bash
code .env
```

Add your configuration:

```env
SPREADSHEET_ID=YOUR_GOOGLE_SPREADSHEET_ID

APPLICATIONS_SHEET=Applications
PROCESSED_SHEET=ProcessedEmails
REVIEW_SHEET=Review

START_DATE=2025/06/01

BLOCKED_SENDER_DOMAINS=
TRUSTED_SENDER_DOMAINS=
```

### Spreadsheet ID

Replace:

```env
SPREADSHEET_ID=YOUR_GOOGLE_SPREADSHEET_ID
```

with your actual spreadsheet ID:

```env
SPREADSHEET_ID=1ABC123XYZ456
```

Do not include the complete Google Sheets URL.

### Start date

`START_DATE` determines how far back the tracker searches Gmail.

Use this format:

```text
YYYY/MM/DD
```

Example:

```env
START_DATE=2025/06/01
```

### Blocked sender domains

Add domains that should always be ignored:

```env
BLOCKED_SENDER_DOMAINS=example-consultancy.com,community.example
```

Use a comma-separated list of domains.

Do not include:

```text
https://
email usernames
URL paths
```

### Trusted sender domains

You can optionally add domains that should receive stronger consideration:

```env
TRUSTED_SENDER_DOMAINS=greenhouse.io,lever.co,ashbyhq.com
```

Leave this blank unless you need custom behavior.

---

## First authorization

Make sure the virtual environment is active:

```bash
source venv/bin/activate
```

Run a dry preview:

```bash
python3 tracker.py --dry-run --verbose
```

The tracker will print a Google authorization URL in Terminal.

1. Copy and open the URL.
2. Sign in using the account added as a test user.
3. Approve Gmail read-only access.
4. Approve Google Sheets access.
5. Return to Terminal.
6. Wait for the authorization process to complete.

After successful authorization, the tracker creates:

```text
token.json
```

This file stores your local OAuth session so you do not need to authorize every run.

Never commit `token.json`.

---

## Usage

### Preview without changing Google Sheets

```bash
python3 tracker.py --dry-run
```

### Preview with detailed classification output

```bash
python3 tracker.py --dry-run --verbose
```

### Run the tracker

```bash
python3 tracker.py
```

### Reprocess previously inspected emails

```bash
python3 tracker.py --dry-run --verbose --reprocess
```

This is useful when testing updated classification rules.

### Rebuild the spreadsheet

Back up your spreadsheet before rebuilding.

```bash
python3 tracker.py --rebuild --confirm-rebuild
```

The rebuild command clears tracker-managed values from:

```text
Applications
ProcessedEmails
Review
```

It then rescans Gmail beginning from `START_DATE`.

Manual changes inside tracker-managed rows may be removed during a rebuild.

---

## Automatic background updates on macOS

The repository includes a macOS LaunchAgent installer.

It allows the tracker to run automatically without keeping Terminal open.

Complete at least one successful manual run before installing the background service.

### Make the scripts executable

```bash
chmod +x scripts/install_launch_agent.sh
chmod +x scripts/uninstall_launch_agent.sh
```

### Install the background service

Run every 10 minutes:

```bash
./scripts/install_launch_agent.sh 600
```

The number represents seconds.

Examples:

```bash
# Every 5 minutes
./scripts/install_launch_agent.sh 300
```

```bash
# Every 15 minutes
./scripts/install_launch_agent.sh 900
```

### Check the service status

```bash
launchctl print \
  gui/$(id -u)/com.rutuja.jobapplicationtracker
```

### Trigger an immediate run

```bash
launchctl kickstart -k \
  gui/$(id -u)/com.rutuja.jobapplicationtracker
```

### View activity logs

```bash
tail -50 logs/job-tracker.log
```

Follow the log continuously:

```bash
tail -f logs/job-tracker.log
```

### View error logs

```bash
tail -50 logs/job-tracker-error.log
```

Follow errors continuously:

```bash
tail -f logs/job-tracker-error.log
```

### Remove the background service

```bash
./scripts/uninstall_launch_agent.sh
```

Removing the LaunchAgent does not delete your source code, configuration, OAuth files, spreadsheet, or application history.

### macOS limitation

The local background tracker runs only while your Mac is:

* Powered on
* Logged in
* Awake
* Connected to the internet

When the Mac becomes available again, the next run checks for new matching emails.

---

## Project structure

```text
job-application-tracker/
├── tracker.py
├── job_tracker/
│   ├── __init__.py
│   ├── app.py
│   ├── auth.py
│   ├── classifier.py
│   ├── config.py
│   ├── gmail_client.py
│   ├── models.py
│   ├── parser.py
│   └── sheets_client.py
├── scripts/
│   ├── install_launch_agent.sh
│   └── uninstall_launch_agent.sh
├── tests/
│   └── test_classifier.py
├── .env.example
├── .gitignore
├── LICENSE
├── MAC_SETUP.md
├── README.md
└── requirements.txt
```

---

## Testing

Activate the virtual environment:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the tests:

```bash
pytest
```

Run with detailed output:

```bash
pytest -v
```

Tests and bug reports should use synthetic or fully redacted email examples.

Never include real emails, OAuth tokens, spreadsheet IDs, or application details in public test files.

---

## Privacy and security

This project is local-first.

### Gmail access

The tracker requests:

```text
https://www.googleapis.com/auth/gmail.readonly
```

It can read the email content required for classification, but it cannot:

* Send emails
* Delete emails
* Archive emails
* Modify labels
* Mark messages as read
* Change Gmail settings

### Google Sheets access

The tracker requests:

```text
https://www.googleapis.com/auth/spreadsheets
```

This allows it to create tabs and update spreadsheets accessible to the authorized Google account.

### Private files

The following files must never be committed:

```text
.env
credentials.json
token.json
venv/
logs/
.job_tracker.lock
```

The included `.gitignore` excludes these files.

Before committing, verify that private files are ignored:

```bash
git check-ignore -v \
  .env \
  credentials.json \
  token.json \
  venv/ \
  logs/ \
  .job_tracker.lock
```

Review staged files before pushing:

```bash
git status
git diff --cached
```

Confirm credentials are not tracked:

```bash
git ls-files | grep -E \
  'credentials\.json|token\.json|^\.env$'
```

That command should return no output.

### If a credential was committed accidentally

Deleting the file or adding it to `.gitignore` is not enough after it has entered Git history.

Immediately:

1. Revoke or delete the exposed OAuth client.
2. Delete the exposed OAuth token.
3. Remove the secret from Git history.
4. Generate replacement credentials.
5. Review GitHub secret-scanning alerts.

---

## Troubleshooting

### `credentials.json` was not found

Confirm that the file exists in the repository root:

```bash
ls -la credentials.json
```

It must be named exactly:

```text
credentials.json
```

### Google authorization shows an access error

Confirm that:

* The OAuth audience is `External`
* The application is in testing mode
* Your Gmail account is listed as a test user
* The OAuth client type is `Desktop app`
* Gmail and Sheets APIs are enabled
* Both required scopes are configured

Delete the existing token and authorize again:

```bash
rm -f token.json
python3 tracker.py --dry-run --verbose
```

### Only Gmail permission was approved

Delete the incomplete token:

```bash
rm -f token.json
```

Authorize again:

```bash
python3 tracker.py --dry-run --verbose
```

Approve both Gmail and Google Sheets permissions.

### The spreadsheet did not change

Dry-run mode intentionally makes no spreadsheet changes:

```bash
python3 tracker.py --dry-run
```

Run the real tracker:

```bash
python3 tracker.py
```

### Incorrect old rows remain

Back up your spreadsheet and rebuild:

```bash
python3 tracker.py --rebuild --confirm-rebuild
```

### A non-job email was included

Run a verbose reprocessing preview:

```bash
python3 tracker.py --dry-run --verbose --reprocess
```

Add unwanted sender domains to `.env`:

```env
BLOCKED_SENDER_DOMAINS=unwanted.example
```

When reporting classification bugs, use synthetic or fully redacted email content.

### The background service is not running

Check its status:

```bash
launchctl print \
  gui/$(id -u)/com.rutuja.jobapplicationtracker
```

Check errors:

```bash
tail -100 logs/job-tracker-error.log
```

Reinstall it:

```bash
./scripts/install_launch_agent.sh 600
```

---

## Roadmap

Potential contribution areas include:

* [ ] Additional applicant-tracking-system support
* [ ] Improved company and role extraction
* [ ] Configurable classification rules
* [ ] Expanded synthetic test coverage
* [ ] Windows Task Scheduler support
* [ ] Linux systemd support
* [ ] Docker support
* [ ] Gmail push notifications
* [ ] Optional hosted deployment
* [ ] Improved spreadsheet formatting
* [ ] Application analytics
* [ ] Manual application imports

Roadmap items are proposals and are not guaranteed release commitments.

---

## Contributing

Contributions are welcome.

Useful contribution areas include:

* Fixing false positives or false negatives
* Adding ATS-specific parsing
* Improving company and role extraction
* Adding synthetic tests
* Supporting Windows or Linux automation
* Improving setup documentation
* Strengthening privacy and security
* Improving Google Sheets formatting

### Contribution workflow

Fork the repository and clone your fork:

```bash
git clone git@github.com:YOUR_USERNAME/job-application-tracker.git
cd job-application-tracker
```

Create a branch:

```bash
git checkout -b feature/your-feature-name
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Make your changes and run the test suite:

```bash
pytest
```

Stage your changes:

```bash
git add .
```

Review everything before committing:

```bash
git status
git diff --cached
```

Commit your changes:

```bash
git commit -m "Add: describe your contribution"
```

Push the branch:

```bash
git push origin feature/your-feature-name
```

Open a pull request against the `main` branch.

### Contribution guidelines

Please:

* Use synthetic email examples
* Add tests for classification changes
* Explain the issue being fixed
* Keep Gmail access read-only
* Avoid unnecessary external services
* Never include OAuth credentials or tokens
* Never include real emails or application information
* Never include personal spreadsheet IDs
* Keep changes focused and documented

For significant architecture changes, open an issue before beginning implementation.

---

## Reporting issues

Open an issue through the repository’s [GitHub Issues](https://github.com/rutujashingate/job-application-tracker/issues) page.

Include:

* Operating system
* Python version
* Command used
* Relevant error output
* Expected behavior
* Actual behavior
* Synthetic or redacted email examples when relevant

Do not include:

* `credentials.json`
* `token.json`
* OAuth authorization URLs
* Real spreadsheet IDs
* Real email addresses
* Unredacted email content
* Private application details

---

## License

This project is released under the [MIT License](LICENSE).

You may use, modify, and distribute it under the terms of the license.

---

<div align="center">

Built and maintained by [Rutuja Shingate](https://github.com/rutujashingate).

**Open to contributions, bug reports, and thoughtful feature proposals.**

</div>
