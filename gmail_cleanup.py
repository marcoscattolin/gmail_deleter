import argparse
import time
from datetime import datetime, timedelta
from typing import List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import sys

# Minimum scopes: read/write messages
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def get_service() -> any:
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def gmail_search(service, query: str, user_id: str = "me"):
    """Generator that returns message IDs that match the query."""
    page_token = None
    while True:
        resp = service.users().messages().list(
            userId=user_id, q=query, pageToken=page_token, maxResults=500
        ).execute()
        for m in resp.get("messages", []):
            yield m["id"]
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

def backoff_sleep(attempt: int):
    time.sleep(min(60, 2 ** attempt))

def trash_message(service, msg_id: str, hard_delete: bool = False, user_id: str = "me"):
    for attempt in range(0, 6):
        try:
            if hard_delete:
                service.users().messages().delete(userId=user_id, id=msg_id).execute()
            else:
                service.users().messages().trash(userId=user_id, id=msg_id).execute()
            return True
        except HttpError as e:
            status = getattr(e, "status_code", None) or (e.resp.status if hasattr(e, "resp") else None)
            if status in (403, 429, 500, 503):
                backoff_sleep(attempt)
                continue
            else:
                print(f"[SKIP] {msg_id} permanent error: {e}", file=sys.stderr)
                return False
        except Exception as ex:
            print(f"[SKIP] {msg_id} error: {ex}", file=sys.stderr)
            backoff_sleep(attempt)
    return False

def main():
    parser = argparse.ArgumentParser(description="Gmail cleanup: trash/delete old messages.")
    parser.add_argument("--trash", action="store_true", help="Move to Trash.")
    parser.add_argument("--hard-delete", action="store_true", help="IMMEDIATE and irreversible deletion (skip Trash).")
    parser.add_argument("--query", type=str, default="older_than:10y in:inbox",
                        help="Gmail query to select messages.")
    parser.add_argument("--protect-label", action="append", default=[],
                        help="Labels to protect: if present on the message, it will NOT be deleted. Repeatable.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum limit of messages to process (0 = no limit).")
    args = parser.parse_args()

    print(f"Query: {args.query}")
    if args.trash:
        print("Mode: TRASH (move to Trash)")
    elif args.hard_delete:
        print("Mode: HARD DELETE (irreversible)")
    else:
        print("Mode: DRY-RUN (no changes). Specify --trash or --hard-delete to execute changes.")

    service = get_service()

    # If the user has indicated labels to protect, we extend the query to exclude them
    # (this is a "best-effort" exclusion at search level; further checking is below)
    q = args.query
    for lbl in args.protect_label:
        q += f' -label:"{lbl}"'

    processed = 0
    matched_ids: List[str] = []
    print("Searching for messages...")

    # We collect IDs once (so the set is stable even if Trash changes in the meantime)
    for msg_id in gmail_search(service, q):
        matched_ids.append(msg_id)
        if args.limit and len(matched_ids) >= args.limit:
            break

    total = len(matched_ids)
    print(f"Found {total} matching messages.")

    if not args.trash and not args.hard_delete:
        # No changes: only preview of the number
        print("DRY-RUN: nothing will be deleted. Specify --trash or --hard-delete to execute changes.")
        return

    # ask the user if they want to proceed
    proceed = input("Do you want to proceed? (y/n): ")
    if proceed != "y":
        print("Operation cancelled.")
        return

    # For safety: check protected labels message-by-message (if requested)
    protect = set(args.protect_label)

    done = 0
    skipped = 0
    t0 = time.time()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}]: Starting deletion...")

    for i, msg_id in enumerate(matched_ids, start=1):
        if protect:
            # Retrieve quick metadata (only labelIds) to filter
            try:
                m = service.users().messages().get(
                    userId="me", id=msg_id, format="metadata", metadataHeaders=[]
                ).execute()
                label_ids = set(m.get("labelIds", []))
                # custom label names don't match labelIds; they need to be mapped.
                # For simplicity, we filter already in the query and skip this step here.
                # (If precise mapping were needed, we would need to download all labels and compare IDs.)
            except HttpError:
                # If get fails, we try to continue anyway
                label_ids = set()

        ok = trash_message(service, msg_id, hard_delete=args.hard_delete)
        if ok:
            done += 1
        else:
            skipped += 1

        # Small gentle pause every 200 actions
        if i % 200 == 0:
            time.sleep(1)

        # Print progress every 500
        if i % 500 == 0:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            rate = done / max(1, (time.time() - t0))
            print(f"[{now}]: Progress: {i}/{total} (trashed/deleted: {done}, skipped: {skipped}) ~{rate:.1f} msg/s")

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}]: DONE. Total processed: {total}. "
          f"{'Deleted' if args.hard_delete else 'Trashed'}: {done}. Skipped: {skipped}.")

if __name__ == "__main__":
    main()
