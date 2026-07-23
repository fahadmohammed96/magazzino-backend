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

## Flusso di lavoro

Consegne sempre via pull request verso `main` (branch protetto). La CI
esegue lint e test su ogni PR.
