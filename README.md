# QMX — Qamar AI (Phase 1)

A starter web application for an independent document-readiness assistant.

## Included in Phase 1
- Responsive Arabic landing page
- Department and transaction selection
- Multi-file upload
- Basic file checks: extension, empty file, 10MB limit
- Simple results report
- Health endpoint for hosting checks
- Render deployment blueprint

## Important limitations
This is a prototype, not a production government service. It does not authenticate documents, determine legal validity, or confirm official acceptance. Department and transaction options are illustrative demo data. Verify every requirement against the relevant official source before production.

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app:app --reload
```
Open http://127.0.0.1:8000

## Deploy on Render
1. Create a GitHub repository named `QMX`.
2. Upload the contents of this folder to the repository root.
3. In Render, choose **New + → Blueprint** (or create a Web Service).
4. Connect the GitHub repository. Render reads `render.yaml`.
5. Deploy and open the generated `onrender.com` URL.

## Roadmap
- Phase 2: real database, user accounts, saved applications, bilingual UI
- Phase 3: PDF text extraction, OCR, image-quality analysis, structured checks
- Phase 4: AI assistant and explainable review reports
- Phase 5: admin console, requirements management, analytics, security hardening
