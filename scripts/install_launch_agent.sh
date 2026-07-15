#!/bin/zsh
set -euo pipefail

INTERVAL_SECONDS="${1:-600}"
LABEL="com.rutuja.jobapplicationtracker"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_PYTHON_PATH="$PROJECT_DIR/venv/bin/python3"
RUNTIME_ROOT="$HOME/Library/Application Support/JobApplicationTracker"
RUNTIME_PROJECT_DIR="$RUNTIME_ROOT/app"
RUNTIME_VENV_DIR="$RUNTIME_ROOT/venv"
PYTHON_PATH="$RUNTIME_VENV_DIR/bin/python3"
TRACKER_PATH="$RUNTIME_PROJECT_DIR/tracker.py"
LOG_DIR="$RUNTIME_ROOT/logs"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

if [[ ! "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || \
   [[ "$INTERVAL_SECONDS" -lt 60 ]]; then
  echo "Interval must be an integer of at least 60 seconds."
  exit 1
fi

if [[ ! -x "$SOURCE_PYTHON_PATH" ]]; then
  echo "Virtual-environment Python not found: $SOURCE_PYTHON_PATH"
  exit 1
fi

if [[ ! -f "$PROJECT_DIR/.env" ]]; then
  echo ".env not found in $PROJECT_DIR"
  exit 1
fi

if [[ ! -f "$PROJECT_DIR/token.json" ]]; then
  echo "token.json not found."
  echo "Run 'python3 tracker.py --dry-run' manually once first."
  exit 1
fi

# A LaunchAgent cannot reliably read projects stored in macOS-protected
# Desktop/Documents folders. Deploy a private runtime under Application Support
# so the tracker continues after Terminal closes.
mkdir -p \
  "$RUNTIME_PROJECT_DIR" \
  "$LOG_DIR" \
  "$HOME/Library/LaunchAgents"
chmod 700 "$RUNTIME_ROOT" "$RUNTIME_PROJECT_DIR" "$LOG_DIR"

/usr/bin/ditto "$PROJECT_DIR/job_tracker" \
  "$RUNTIME_PROJECT_DIR/job_tracker"
/usr/bin/ditto "$PROJECT_DIR/tracker.py" \
  "$RUNTIME_PROJECT_DIR/tracker.py"
/usr/bin/ditto "$PROJECT_DIR/requirements.txt" \
  "$RUNTIME_PROJECT_DIR/requirements.txt"
/usr/bin/ditto "$PROJECT_DIR/venv" "$RUNTIME_VENV_DIR"

for private_file in .env token.json credentials.json; do
  if [[ -f "$PROJECT_DIR/$private_file" ]]; then
    /usr/bin/ditto "$PROJECT_DIR/$private_file" \
      "$RUNTIME_PROJECT_DIR/$private_file"
    chmod 600 "$RUNTIME_PROJECT_DIR/$private_file"
  fi
done

if [[ ! -x "$PYTHON_PATH" ]]; then
  echo "Runtime Python deployment failed: $PYTHON_PATH"
  exit 1
fi

"$PYTHON_PATH" - \
  "$PLIST_PATH" "$LABEL" "$RUNTIME_PROJECT_DIR" "$PYTHON_PATH" \
  "$TRACKER_PATH" "$LOG_DIR" "$INTERVAL_SECONDS" <<'PY'
import plistlib
import sys
from pathlib import Path

(
    plist_path,
    label,
    project_dir,
    python_path,
    tracker_path,
    log_dir,
    interval,
) = sys.argv[1:]

payload = {
    "Label": label,
    "ProgramArguments": [python_path, tracker_path],
    "WorkingDirectory": project_dir,
    "RunAtLoad": True,
    "StartInterval": int(interval),
    "ProcessType": "Background",
    "StandardOutPath": str(Path(log_dir) / "job-tracker.log"),
    "StandardErrorPath": str(
        Path(log_dir) / "job-tracker-error.log"
    ),
    "EnvironmentVariables": {"PYTHONUNBUFFERED": "1"},
}

with open(plist_path, "wb") as handle:
    plistlib.dump(payload, handle)
PY

launchctl bootout "$DOMAIN" "$PLIST_PATH" \
  >/dev/null 2>&1 || true
launchctl bootstrap "$DOMAIN" "$PLIST_PATH"
launchctl enable "$DOMAIN/$LABEL"
launchctl kickstart -k "$DOMAIN/$LABEL"

echo ""
echo "Installed and started $LABEL"
echo "Runs at login and every $INTERVAL_SECONDS seconds."
echo "Runtime: $RUNTIME_ROOT"
echo "Status: launchctl print $DOMAIN/$LABEL"
echo "Log: tail -f \"$LOG_DIR/job-tracker.log\""
echo "Errors: tail -f \"$LOG_DIR/job-tracker-error.log\""
