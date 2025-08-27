# Gmail Cleanup Script

Questo progetto contiene uno script Python (`gmail_cleanup.py`) che utilizza la **Gmail API** per individuare e cancellare automaticamente (spostando nel Cestino o eliminando definitivamente) le email più vecchie di 2 anni, o qualsiasi criterio impostato con una query di Gmail.

## 🚀 Setup

### 1. Abilitare la Gmail API
1. Vai su [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un nuovo progetto (o usane uno esistente).
3. Vai su **API e servizi → Libreria**.
4. Cerca **Gmail API** → clicca **Abilita**.

### 2. Creare credenziali OAuth
1. Vai su **API e servizi → Credenziali**.
2. Clicca **Crea credenziali → ID client OAuth**.
3. Tipo di applicazione: **Desktop App**.
4. Scarica il file `credentials.json`.
5. Metti `credentials.json` nella stessa cartella dello script.

### 3. Installare le dipendenze Python
Assicurati di avere Python 3.13+ installato, poi esegui:

```bash
uv venv
uv sync
````

### 4. Primo avvio (autenticazione)

Alla prima esecuzione lo script aprirà il browser e ti chiederà di autorizzare l’accesso al tuo Gmail.
Verrà creato un file `token.json` che contiene il token di accesso e verrà riutilizzato nelle esecuzioni successive.

---

## ⚙️ Utilizzo

### Comando base (sposta nel Cestino le email più vecchie di 2 anni)

```bash
uv run gmail_cleanup.py
```

### Modalità DRY-RUN (simulazione, nessuna modifica)

```bash
uv run gmail_cleanup.py --dry-run
```

Mostra solo quante email corrispondono alla query senza spostarle nel Cestino.

### Eliminazione immediata e irreversibile

```bash
uv run gmail_cleanup.py --hard-delete
```

⚠️ Attenzione: i messaggi non passano dal Cestino, vengono eliminati subito.

### Limitare il numero di messaggi processati

```bash
uv run gmail_cleanup.py --limit 200
```

### Modificare la query Gmail

La query usa la stessa sintassi della barra di ricerca di Gmail.
Esempi:

```bash
# Solo email in Posta in arrivo più vecchie di 2 anni
uv run gmail_cleanup.py --query "older_than:2y in:inbox -in:spam -in:trash"

# Email più vecchie del 1° gennaio 2023
uv run gmail_cleanup.py --query "before:2023/01/01 -in:spam -in:trash"

# Escludere le email di un mittente
uv run gmail_cleanup.py --query "older_than:2y -from:capo@azienda.com -in:spam -in:trash"
```

### Proteggere email con certe etichette

```bash
uv run gmail_cleanup.py --protect-label Fatture --protect-label Keep
```

Le email che hanno una di queste etichette **non verranno cancellate**.

---

## 🛠 File generati

* `credentials.json` → le tue credenziali OAuth scaricate da Google Cloud (non condividerle).
* `token.json` → token salvato dopo il primo login (rigenerabile cancellandolo).
* `gmail_cleanup.py` → lo script Python.

---

## 📅 Automazione

Puoi schedulare lo script per eseguirlo periodicamente:

* **Linux/macOS** → aggiungi una riga al tuo `crontab` (esempio: esecuzione ogni primo del mese alle 03:00):

  ```bash
  0 3 1 * * /usr/bin/python3 /percorso/gmail_cleanup.py
  ```
* **Windows** → usa l’**Utilità di pianificazione** per eseguirlo con cadenza mensile.

---

## ⚠️ Note importanti

* Usa **prima la modalità `--dry-run`** per verificare i risultati.
* Se usi `--hard-delete`, i messaggi vengono eliminati definitivamente e **non possono essere recuperati**.
* Lo script lavora a livello di **singolo messaggio** (non thread intero), in base a ciò che la query restituisce.
* Rispetta i limiti di quota API di Gmail (lo script include retry e backoff automatici per 429/500).

---

## ✅ Esempio rapido

```bash
# Simulazione: quanti messaggi più vecchi di 2 anni verrebbero eliminati
uv run gmail_cleanup.py --dry-run

# Elimina davvero spostando nel Cestino
uv run gmail_cleanup.py
```

---

```

---

Vuoi che ti aggiunga anche una **sezione troubleshooting** nel README (tipo errori comuni `invalid_grant`, `quota exceeded`, ecc.) o lo teniamo semplice così?
```
