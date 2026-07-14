# macOS automatic setup

## 1. Complete one manual run

```bash
source venv/bin/activate
pip install -r requirements.txt
python3 tracker.py --dry-run
python3 tracker.py
```

Confirm `.env`, `credentials.json`, `token.json`, and `venv/bin/python3` exist.

## 2. Install the LaunchAgent

```bash
chmod +x scripts/*.sh
./scripts/install_launch_agent.sh 600
```

`600` means every 10 minutes.

## 3. Verify

```bash
launchctl print \
  gui/$(id -u)/com.rutuja.jobapplicationtracker
```

```bash
tail -50 logs/job-tracker.log
tail -50 logs/job-tracker-error.log
```

## 4. Change frequency

Every 5 minutes:

```bash
./scripts/install_launch_agent.sh 300
```

Every 15 minutes:

```bash
./scripts/install_launch_agent.sh 900
```

## 5. Remove

```bash
./scripts/uninstall_launch_agent.sh
```

The tracker does not need an open Terminal window. It can run only while the
Mac is on, the user is logged in, and the machine is awake.
