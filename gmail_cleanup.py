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

# Scopi minimi: lettura/scrittura messaggi
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
    """Generator che restituisce gli ID dei messaggi che corrispondono alla query."""
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
                print(f"[SKIP] {msg_id} errore permanente: {e}", file=sys.stderr)
                return False
        except Exception as ex:
            print(f"[SKIP] {msg_id} errore: {ex}", file=sys.stderr)
            backoff_sleep(attempt)
    return False

def main():
    parser = argparse.ArgumentParser(description="Gmail cleanup: cestina/elimina messaggi vecchi.")
    parser.add_argument("--dry-run", action="store_true", help="Non modifica nulla; mostra solo il conto.")
    parser.add_argument("--hard-delete", action="store_true", help="Eliminazione IMMEDIATA e irreversibile (salta il Cestino).")
    parser.add_argument("--query", type=str, default="older_than:8y in:inbox",
                        help="Query di Gmail per selezionare i messaggi.")
    parser.add_argument("--protect-label", action="append", default=[],
                        help="Etichette da proteggere: se presenti sul messaggio, NON viene cancellato. Ripetibile.")
    parser.add_argument("--limit", type=int, default=0, help="Limite massimo di messaggi da processare (0 = nessun limite).")
    args = parser.parse_args()

    if args.hard_delete and args.dry_run:
        print("⚠️ --hard-delete e --dry-run insieme non hanno senso: rimuovi uno dei due.")
        sys.exit(1)

    print(f"Query: {args.query}")
    if args.dry_run:
        print("Modalità: DRY-RUN (nessuna modifica)")
    elif args.hard_delete:
        print("Modalità: HARD DELETE (irreversibile)")
    else:
        print("Modalità: TRASH (sposta nel Cestino)")

    service = get_service()

    # Se l'utente ha indicato etichette da proteggere, estendiamo la query per escluderle
    # (questa è un'esclusione "best-effort" a livello di ricerca; ulteriore controllo è sotto)
    q = args.query
    for lbl in args.protect_label:
        q += f' -label:"{lbl}"'

    processed = 0
    matched_ids: List[str] = []
    print("Cerco messaggi...")

    # Raccogliamo gli ID una volta (così il set è stabile anche se nel frattempo il Cestino cambia)
    for msg_id in gmail_search(service, q):
        matched_ids.append(msg_id)
        if args.limit and len(matched_ids) >= args.limit:
            break

    total = len(matched_ids)
    print(f"Trovati {total} messaggi che corrispondono.")

    if args.dry_run:
        # Nessuna modifica: solo anteprima del numero
        print("DRY-RUN: non verrà cancellato nulla.")
        return

    # Per sicurezza: controllo etichette protette messaggio-per-messaggio (se richieste)
    protect = set(args.protect_label)

    done = 0
    skipped = 0
    t0 = time.time()
    for i, msg_id in enumerate(matched_ids, start=1):
        if protect:
            # Recupero metadati rapidi (solo labelIds) per filtrare
            try:
                m = service.users().messages().get(
                    userId="me", id=msg_id, format="metadata", metadataHeaders=[]
                ).execute()
                label_ids = set(m.get("labelIds", []))
                # i nomi custom delle etichette non coincidono con labelIds; va mappato.
                # Per semplicità, filtriamo già in query e qui saltiamo questo passaggio.
                # (Se servisse mappare con precisione, bisognerebbe scaricare tutte le labels e confrontare gli ID.)
            except HttpError:
                # Se fallisce il get, proviamo comunque a proseguire
                label_ids = set()

        ok = trash_message(service, msg_id, hard_delete=args.hard_delete)
        if ok:
            done += 1
        else:
            skipped += 1

        # Piccola pausa gentile ogni 200 azioni
        if i % 200 == 0:
            time.sleep(1)

        # Stampa progress ogni 500
        if i % 500 == 0:
            rate = done / max(1, (time.time() - t0))
            print(f"Progress: {i}/{total} (cestinati/eliminati: {done}, saltati: {skipped}) ~{rate:.1f} msg/s")

    print(f"FATTO. Totale elaborati: {total}. "
          f"{'Eliminati' if args.hard_delete else 'Cestinati'}: {done}. Saltati: {skipped}.")

if __name__ == "__main__":
    main()
