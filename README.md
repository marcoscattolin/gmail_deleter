# Gmail Cleanup Script

This project contains a Python script (`gmail_cleanup.py`) that uses the **Gmail API** to automatically identify and delete (by moving to Trash or permanently deleting) emails older than 10 years, or any criteria set with a Gmail query.

## 🚀 Setup

### 1. Enable Gmail API
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or use an existing one).
3. Go to **APIs & Services → Library**.
4. Search for **Gmail API** → click **Enable**.

### 2. Create OAuth credentials
1. Go to **APIs & Services → Credentials**.
2. Click **Create credentials → OAuth client ID**.
3. Application type: **Desktop App**.
4. Download the `credentials.json` file.
5. Place `credentials.json` in the same folder as the script.

### 3. Install Python dependencies
Make sure you have Python 3.13+ installed, then run:

```bash
uv venv
uv sync
```

### 4. First run (authentication)

On first execution, the script will open your browser and ask you to authorize access to your Gmail.
A `token.json` file will be created containing the access token and will be reused in subsequent runs.

---

## ⚙️ Usage

### Basic command (simulation, no changes, count emails older than 10 years).

```bash
uv run gmail_cleanup.py
```

Shows only how many emails match the query without deleting or moving them to Trash.

### TRASH mode: actually move emails to trash folder.

```bash
uv run gmail_cleanup.py --trash
```

### HARD DELETE mode: immediate and irreversible deletion.

```bash
uv run gmail_cleanup.py --hard-delete
```

⚠️ Warning: messages don't go through Trash, they are deleted immediately.

### Limit the number of processed messages

```bash
uv run gmail_cleanup.py --trash --limit 200
```

### Modify the Gmail query

The query uses the same syntax as Gmail's search bar.
Examples:

```bash
# Only emails older than 2 years in the inbox folder
uv run gmail_cleanup.py --query "older_than:2y in:inbox"

# Emails older than January 1st, 2023 excluding emails in spam and trash
uv run gmail_cleanup.py --query "before:2023/01/01 -in:spam -in:trash"

# Exclude emails from a sender excluding emails in spam and trash
uv run gmail_cleanup.py --query "older_than:2y -from:boss@company.com -in:spam -in:trash"
```

### Protect emails with certain labels

```bash
uv run gmail_cleanup.py --protect-label Invoices --protect-label Keep
```

Emails that have one of these labels **will NOT be deleted**.

---

## 🛠 Generated files

* `credentials.json` → your OAuth credentials downloaded from Google Cloud (don't share them).
* `token.json` → token saved after first login (regenerable by deleting it).
* `gmail_cleanup.py` → the Python script.

---

## 📅 Automation

You can schedule the script to run periodically:

* **Linux/macOS** → add a line to your `crontab` (example: run every 1st of the month at 03:00):

  ```bash
  0 3 1 * * /usr/bin/python3 /path/gmail_cleanup.py
  ```
* **Windows** → use the **Task Scheduler** to run it monthly.

---

## ⚠️ Important notes

* By default, script is not removing emails.
* Specify `--trash` if you actually want to move emails in trash folder
* If you use `--hard-delete`, messages are permanently deleted and **cannot be recovered**.
* The script works at the **single message level** (not entire thread), based on what the query returns.
* Respects Gmail API quota limits (the script includes automatic retry and backoff for 429/500).

---

## ✅ Quick example

```bash
# Simulation: how many messages older than 2 years would be deleted
uv run gmail_cleanup.py

# Actually delete by moving to Trash
uv run gmail_cleanup.py --trash
```
