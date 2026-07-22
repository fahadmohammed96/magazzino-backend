# Progetto

Servizio backend del gestionale ordini di magazzino. Espone le API consumate
dalla dashboard interna `magazzino-frontend`. Domini: catalogo prodotti,
anagrafica clienti, ordini (ciclo In attesa → In lavorazione → Evaso/Spedito
→ Annullato, con ripristino scorte all'annullamento) e giacenze con scarico
automatico sugli stati Confermato/Evaso e alert sotto-scorta. Auth: login
interno con 2 ruoli (Admin, Operatore).
_(Decisioni raccolte nella scoperta di kickoff — issue MYL-9.)_

# Stack

- Python 3.12+, FastAPI, Pydantic v2
- Dipendenze: pip + pyproject.toml — installare con `pip install -e ".[dev]"`
- Database: PostgreSQL, ORM SQLAlchemy 2, migrazioni con Alembic.
  _(Decisione kickoff.)_ Il setup effettivo (dipendenze, connessione, prima
  migrazione) è tracciato in un'issue dedicata di Fase 2.
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
- Versionamento: prefisso `/v1`; nuove versioni solo per breaking change.
  _(Decisione kickoff.)_
- Formato errori: `{"error": {"code": "...", "message": "..."}}` — sempre.
  Mai stack trace o dettagli interni nelle risposte. _(Decisione kickoff.)_

# Dati e migrazioni

DB adottato: PostgreSQL + SQLAlchemy 2 + Alembic (vedi Stack). Comando
migrazioni: `alembic upgrade head` (attivo dopo l'issue di setup DB).
- Ogni migrazione ha downgrade funzionante; irreversibilità dichiarata ed
  eccezionale, con piano di rollback
- Modifiche distruttive (drop, rename, cambi di tipo) sempre segnalate
  nella nota di consegna
- Transazioni per operazioni multi-scrittura

# Test

- Unit per la logica di dominio; integrazione per endpoint (TestClient)
- Database nei test: PostgreSQL usa-e-getta via testcontainers per i test
  d'integrazione; la logica di dominio si testa a unità, senza DB.
  _(Decisione kickoff.)_
- Servizi esterni sempre mockati

# Log e sicurezza

- Log strutturati: scelta rimandata al primo bisogno (structlog o logging
  config della stdlib). MAI dati sensibili o secret nei log.
- Secret solo da variabili d'ambiente; mai nel codice o nella
  configurazione versionata

# Deploy

- Deploy: da definire quando servirà (non è un task della squad). Candidato:
  container su una PaaS. _(Decisione kickoff: rimandato.)_
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
