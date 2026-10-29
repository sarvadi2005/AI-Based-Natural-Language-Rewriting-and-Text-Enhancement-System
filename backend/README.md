# Natural Language Rewriting API

A small FastAPI service for the Rewrite Studio frontend. The default engine is a
deterministic, local, rule-based rewriter. It does not download a model, require
an API key, or claim to use a pretrained AI model.

## Requirements

- Python 3.10 or newer
- The packages listed in `requirements.txt`

From PowerShell in this directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Then start the API with `start_backend.bat`, or run:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`; interactive docs are at
`http://127.0.0.1:8000/docs`. Keep the backend console open while using the
frontend. The frontend's `.\start_frontend.bat` serves on port 5500. CORS allows
both `http://127.0.0.1:5500` and `http://localhost:5500`.

## Endpoints

- `GET /` — service and engine information
- `GET /health` — API and SQLite status
- `POST /api/rewrite` — rewrite text and save the successful result
- `POST /api/evaluate` — evaluate original and rewritten text
- `GET /api/history?limit=100` — newest saved rewrites first (limit 1–500)
- `GET /api/history/{record_id}` — retrieve one saved rewrite
- `DELETE /api/history` — delete all saved rewrites

Rewrite requests use the frontend's `{ "text": "...", "mode": "improve" }`
shape. Responses include both `enhanced_text` and `rewritten_text`, plus the
requested `mode`, its `canonical_mode`, word counts, quality/readability
metrics, a list of changes, processing time, status, and engine name.

Canonical mode IDs are `paraphrase`, `academic`, `professional`, `simple`,
`friendly`, `concise`, `expand`, and `grammar`. Existing frontend IDs remain
supported: `improve` maps to `paraphrase`, `simplify` to `simple`, `creative`
to `expand`, and `persuasive` to `professional`. The response and stored
history retain the originally requested mode so the existing UI can read it.
Rule-based edits use fixed phrase and grammar rules; framing phrases are used
only as deterministic fallbacks and do not add domain facts.

## Evaluation and limitations

Word and sentence counts, average sentence length, an estimated English Flesch
Reading Ease score when applicable, and a 0–100 heuristic quality score are
returned. The quality score is based on sentence length, long-word frequency,
lexical repetition, and terminal punctuation. It is not proof of semantic or
factual accuracy, writing quality in general, or plagiarism freedom. Readability
is a lightweight estimate, not a full linguistic analysis.

## SQLite storage

History is saved in `backend/data/rewrite_history.sqlite3` by default. Override
this location with `TEXT_REWRITER_DB_PATH`; parent directories are created
automatically. `.env.example` documents the optional variable. The app does not
load `.env` files implicitly.

## Tests

```powershell
python -m pytest
```
