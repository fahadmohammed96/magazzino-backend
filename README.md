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

Contratto OpenAPI: `http://localhost:8000/openapi.json`

## Flusso di lavoro

Consegne sempre via pull request verso `main` (branch protetto). La CI
esegue lint e test su ogni PR.
