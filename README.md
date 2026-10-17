# ClausePilot — Contract Obligation and Renewal Assistant

A small full-stack assessment prototype that stores contract text, suggests potentially relevant obligations with transparent rule-based matching, and requires a human reviewer to correct, approve, or reject each item.

## Features
- Responsive frontend for adding and reviewing contracts.
- Flask JSON API and SQLite persistence.
- Rule-based suggestion categories: renewal, payment, notice, delivery/service, and compliance.
- Optional due-date extraction for a limited set of unambiguous date formats.
- Human review workflow: Needs review / Approved / Rejected, editable descriptions, dates, and reviewer notes.
- Validation, loading states, empty states, success/error messages, health endpoint, and focused tests.
- No external LLM API is required for the demo.

## Important limitation
This is an assessment prototype, not legal advice and not a reliable legal document parser. Matching is keyword-based and can miss or misinterpret clauses. The confidence value is a heuristic indicator, not a calibrated probability. A qualified person must verify all items against the original agreement. The app does not send notices, make legal decisions, or perform automated contract actions.

## Local setup
Requires Python 3.10+.

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

## Run tests
```bash
pytest -q
```

## API overview
- `GET /api/health` — health status.
- `GET /api/contracts` — list contracts.
- `POST /api/contracts` — create contract and generate suggested review items.
- `GET /api/obligations` — list obligations.
- `PATCH /api/obligations/<id>` — save reviewer status, corrected text, due date, and note.

## Deployment
Deploy as a Python web service with build command `pip install -r requirements.txt` and start command `gunicorn app:app` (add `gunicorn` to requirements before using that start command). Set `PORT` if required by the host. Configure a persistent writable disk and set `DATABASE_PATH` to its mounted path; otherwise SQLite data may be lost on redeploy/restart depending on the hosting provider. Verify `/api/health` and test the full workflow on the deployed URL before submitting.

## Repository checklist
- Commit source code, tests, README, `AGENT_USAGE.md`, and `.env.example`.
- Never commit real credentials, API keys, private contracts, or production data.
- Keep the repository and deployed URL public for reviewer access if required by the assessment.
- Include a short PDF/PPT/PPTX presentation only if the assessment form requests one.
