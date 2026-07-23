# magazzino — API

[Una riga sul servizio.] Le convenzioni operative del repository sono in
**[AGENTS.md](./AGENTS.md)**: è la fonte di verità, questo README è solo
l'ingresso.

## Avvio rapido

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload    # http://localhost:8000
```

## Comandi

| Comando                          | Cosa fa                    |
| -------------------------------- | -------------------------- |
| `uvicorn app.main:app --reload`  | Server di sviluppo         |
| `pytest`                         | Suite di test              |
| `ruff check .`                   | Lint                       |
| `ruff format .`                  | Format                     |
| `alembic upgrade head`           | Applica le migrazioni      |
| `alembic downgrade base`         | Annulla le migrazioni      |

Contratto OpenAPI: `http://localhost:8000/openapi.json`

## Database e migrazioni

PostgreSQL + SQLAlchemy 2 + Alembic. La connessione è letta da `DATABASE_URL`
(vedi `.env.example`); engine e sessioni sono in `app/db/`. Le migrazioni
vivono in `migrations/` e usano la stessa `DATABASE_URL`.

I test d'integrazione (`tests/integration/`) usano un PostgreSQL usa-e-getta
via **testcontainers**: richiedono un daemon Docker attivo. In assenza di
Docker vengono saltati automaticamente; i test unitari girano comunque.

## Autenticazione

Login interno con token Bearer (JWT HS256) e due ruoli, `admin` e `operator`.

| Endpoint             | Descrizione                                            |
| -------------------- | ------------------------------------------------------ |
| `POST /v1/auth/login`| Credenziali → `access_token` Bearer + dati utente      |
| `GET /v1/auth/me`    | Token Bearer → dati dell'utente autenticato            |

Variabili d'ambiente (vedi `.env.example`): `AUTH_SECRET_KEY` (obbligatoria,
firma i token), `ACCESS_TOKEN_EXPIRE_MINUTES` (opzionale, default 60).

Le dependency di protezione riusabili sono in `app/api/deps.py`:
`get_current_user` (richiede un token valido) e `require_role(Role.admin)`
(richiede anche un ruolo minimo), da applicare agli endpoint di dominio.

### Utente admin iniziale (seed)

Per il primo accesso, crea l'admin una tantum dopo aver applicato le
migrazioni:

```bash
alembic upgrade head
# SEED_ADMIN_USERNAME e SEED_ADMIN_PASSWORD valorizzate nel tuo .env
python -m app.db.seed
```

Il comando è idempotente: se l'utente esiste già non fa nulla.

## Flusso di lavoro

Consegne sempre via pull request verso `main` (branch protetto). La CI
esegue lint e test su ogni PR.
