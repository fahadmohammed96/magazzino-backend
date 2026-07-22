# Progetto

[DECISIONE] Cosa fa questo servizio e chi lo consuma — definire in Fase 1
del kickoff.

# Stack

- Python 3.12+, FastAPI, Pydantic v2
- Dipendenze: pip + pyproject.toml — installare con `pip install -e ".[dev]"`
- Database: [DECISIONE] nessuno nel template. Quando serve: scegliere DB e
  strumento migrazioni (es. PostgreSQL + SQLAlchemy/Alembic) e aggiornare
  QUI stack, comandi e sezione "Dati e migrazioni".
- Test: pytest (+ httpx TestClient per gli endpoint)
- Lint/format: ruff

# Comandi (verificati sul repo pulito)

- Installazione: `pip install -e ".[dev]"`
- Avvio locale: `uvicorn app.main:app --reload` → http://localhost:8000
- Test: `pytest` — la suite deve passare prima di ogni PR
- Lint: `ruff check .` e `ruff format --check .` — il codice consegnato li passa
- Contratto OpenAPI generato: http://localhost:8000/openapi.json

# Struttura

- `app/main.py` — punto di ingresso, registrazione dei router
- `app/api/` — endpoint e router, un modulo per area
- `app/services/` — logica di dominio (creare al primo bisogno)
- `app/models/` — modelli e schema (creare al primo bisogno)
- `tests/` — specchia la struttura del codice

# Convenzioni di codice

- Type hint ovunque; snake_case per moduli e funzioni, PascalCase per classi
- Docstring sulle API pubbliche dei moduli
- Input validati al confine con schemi Pydantic

# API

- Contratto: OpenAPI generato da FastAPI (`/openapi.json`) — è la fonte che
  il frontend consuma
- Versionamento: [DECISIONE] es. prefisso `/v1`, nuove versioni solo per
  breaking change — definire in Fase 1
- Formato errori: [DECISIONE] es. `{"error": {"code": "...", "message": "..."}}`
  — definire in Fase 1. Mai stack trace o dettagli interni nelle risposte.

# Dati e migrazioni

(Si attiva quando il progetto adotta un database — vedi Stack.)
- Ogni migrazione ha downgrade funzionante; irreversibilità dichiarata ed
  eccezionale, con piano di rollback
- Modifiche distruttive (drop, rename, cambi di tipo) sempre segnalate
  nella nota di consegna
- Transazioni per operazioni multi-scrittura

# Test

- Unit per la logica di dominio; integrazione per endpoint (TestClient)
- Database nei test: [DECISIONE] quando ci sarà un DB — testcontainers /
  SQLite in memoria / fixture: scegliere e documentare qui
- Servizi esterni sempre mockati

# Log e sicurezza

- Log strutturati: [DECISIONE] logging config / structlog — definire al
  primo bisogno. MAI dati sensibili o secret nei log.
- Secret solo da variabili d'ambiente; mai nel codice o nella
  configurazione versionata

# Deploy

- [DECISIONE] Dove e come va online (es. container su una PaaS, deploy
  automatico da `main`) — definire in Fase 1.
- Il deploy NON è mai un task della squad: è un automatismo di
  piattaforma o un gesto umano.
- Variabili d'ambiente richieste: dichiarate in `.env.example` (nomi e
  descrizione, MAI valori).

# Flusso di lavoro

- I task arrivano come issue su Multica; consegne SEMPRE via PR verso
  `main` (protetto), mai push diretto
- Ogni PR include la nota di consegna nel formato definito dalle
  istruzioni dell'agente
- La CI (lint + test) deve essere verde perché la PR sia approvabile
- Fuori scope per questo repo: interfacce utente e layer server del
  framework frontend → segnalare sull'issue, non implementare
