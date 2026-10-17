# AI / Agent Usage and Verification

## Tools used
This prototype was prepared with AI-assisted coding support. The shipped application does not call an external LLM at runtime; it uses simple, inspectable keyword rules to create review suggestions.

## Representative prompts used during development
- "Create a small contract obligation tracking app with a frontend, Flask backend, and SQLite persistence."
- "Add human review controls so every suggested obligation can be corrected, approved, or rejected."
- "Add input validation, visible loading/empty/error states, tests, and documentation."
- "Review the code for unsafe assumptions and clearly document limitations."

## Delegated work
AI assistance was used to draft application structure, frontend presentation, API routes, tests, and documentation. A human should inspect all code and run the tests before submission.

## Verification performed / required
- Automated tests cover health status, input validation, contract creation, and review updates.
- Before submission, run `pytest -q`, start the app locally, create a sample contract, verify suggestions, edit a due date, approve/reject an item, refresh the page, and confirm the decision persists.
- After deployment, repeat the workflow on the public URL and confirm `/api/health` returns `{"status":"ok","app":"Contract Obligation and Renewal Assistant"}`.
- Confirm repository and deployed application links work in a private/incognito browser window.

## Known failure modes
- Keyword rules can miss obligations, return irrelevant text, and fail to understand legal context.
- Only a narrow set of date formats is recognized; no date should be trusted without review.
- The displayed confidence is heuristic, not statistically calibrated.
- No authentication, multi-user authorization, encryption-at-rest configuration, file upload, email reminders, or production-grade audit log is implemented.
- SQLite persistence depends on the hosting provider's disk behavior; configure persistent storage before deployment.
- Do not paste confidential contracts into a public demo.

## Human oversight
No suggested item should be treated as legally correct until a human verifies the original clause. The user must review, correct, and explicitly approve/reject each item. The app does not automatically notify counterparties or execute contract actions.
