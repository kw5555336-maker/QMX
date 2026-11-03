from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import os

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="QMX | Qamar AI", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {".pdf", ".png", ".jpg", ".jpeg"}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    return {"status": "ok", "app": "QMX"}

@app.post("/api/check")
async def check_document(
    department: str = Form(...),
    transaction: str = Form(...),
    documents: list[UploadFile] = File(...)
):
    """Phase 1 demo validation only. Not an official or legal document verification."""
    results = []
    for item in documents:
        suffix = Path(item.filename or "").suffix.lower()
        content = await item.read()
        issues = []
        if not content:
            issues.append("الملف فارغ / File is empty")
        if suffix not in ALLOWED_TYPES:
            issues.append("صيغة الملف غير مدعومة / Unsupported file format")
        if len(content) > MAX_FILE_SIZE:
            issues.append("حجم الملف أكبر من 10MB / File exceeds 10MB")
        results.append({
            "name": item.filename or "unnamed",
            "size": len(content),
            "ok": not issues,
            "issues": issues
        })

    passed = sum(1 for r in results if r["ok"])
    score = round((passed / len(results)) * 100) if results else 0
    return {
        "department": department,
        "transaction": transaction,
        "score": score,
        "files": results,
        "notice": "فحص تجريبي أولي فقط؛ لا يؤكد صحة المستند أو قبوله لدى أي جهة حكومية."
    }
