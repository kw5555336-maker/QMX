# QMX | Qamar AI — Phase 2 prototype

Arabic-first prototype for preliminary document-readiness checks.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000

## Phase 2 changes
- Validates file format, size, empty files and image readability/dimensions.
- Extracts selectable text from PDF files where possible.
- Uses a small illustrative keyword checklist for one demo scenario (Ministry of Foreign Affairs / document attestation).
- Reports possible text indicators, insufficient evidence, mismatches, and technical file problems separately.
- Removes the misleading overall pass percentage.

## Important limitations
This is a hackathon/demo prototype, not an official UAE government service. The demo keywords are invented for software demonstration and are not official requirements. It does not authenticate documents, verify signatures/stamps, establish legal validity, or predict government acceptance. Image OCR is not enabled in this version; images without readable extracted text are flagged for manual review. Do not upload sensitive personal documents to a public demo deployment.

Before real-world use, requirements must be verified with official sources, and the system needs OCR, robust document classification, privacy/security controls, retention policies, access control, monitoring, and human review.
