from pathlib import Path
from io import BytesIO
import re

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="QMX | Qamar AI", version="0.2.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {".pdf", ".png", ".jpg", ".jpeg"}
# Illustrative demo checklist only. These are NOT official UAE requirements.
DEMO_RULES = {
    ("وزارة الخارجية", "تصديق مستند"): {
        "keywords": ["certificate", "certification", "شهادة", "تصديق", "وزارة", "ministry", "document"],
        "label": "مستند ذو صلة محتملة بالتصديق",
        "hint": "تحقق يدوياً من نوع المستند ومتطلبات التصديق لدى الجهة المختصة.",
    }
}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    return {"status": "ok", "app": "QMX", "version": "0.2.0"}


def extract_pdf_text(content: bytes):
    try:
        reader = PdfReader(BytesIO(content))
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:15])
        return text, len(reader.pages), None
    except Exception:
        return "", 0, "تعذر قراءة محتوى PDF؛ قد يكون الملف تالفاً أو محمياً." 


def inspect_image(content: bytes):
    try:
        with Image.open(BytesIO(content)) as img:
            width, height = img.size
            fmt = (img.format or "").upper()
            if width < 300 or height < 300:
                return {"width": width, "height": height, "format": fmt, "issue": "دقة الصورة منخفضة وقد يصعب قراءة التفاصيل."}
            return {"width": width, "height": height, "format": fmt, "issue": None}
    except (UnidentifiedImageError, OSError):
        return None


def assess_relevance(filename: str, extracted_text: str, rule):
    if not rule:
        return "needs_review", "لا توجد قائمة تحقق تجريبية لهذا النوع من المعاملات؛ يلزم تحديد المتطلبات ومراجعتها يدوياً."
    searchable = f"{filename} {extracted_text}".lower()
    hits = [word for word in rule["keywords"] if word.lower() in searchable]
    if hits:
        return "possible_match", "ظهرت مؤشرات نصية قد تتوافق مع نوع المعاملة، لكنها لا تثبت نوع المستند أو صحته."
    if extracted_text.strip():
        return "mismatch", "لم نعثر على مؤشرات نصية كافية تربط محتوى الملف بالمعاملة المختارة."
    return "needs_review", "لم يتوفر نص قابل للبحث؛ لا يمكن تأكيد ارتباط الملف بالمعاملة. يلزم فحص بصري أو OCR."


@app.post("/api/check")
async def check_document(
    department: str = Form(...),
    transaction: str = Form(...),
    documents: list[UploadFile] = File(...),
):
    results = []
    rule = DEMO_RULES.get((department, transaction))

    for item in documents:
        name = item.filename or "unnamed"
        suffix = Path(name).suffix.lower()
        content = await item.read()
        issues, extracted_text, metadata = [], "", {}
        status = "needs_review"

        if not content:
            issues.append("الملف فارغ.")
        elif suffix not in ALLOWED_TYPES:
            issues.append("صيغة الملف غير مدعومة؛ الصيغ المقبولة PDF وJPG وPNG.")
        elif len(content) > MAX_FILE_SIZE:
            issues.append("حجم الملف أكبر من 10MB.")
        else:
            if suffix == ".pdf":
                extracted_text, pages, pdf_error = extract_pdf_text(content)
                metadata["pages"] = pages
                if pdf_error:
                    issues.append(pdf_error)
                if not extracted_text.strip() and not pdf_error:
                    issues.append("ملف PDF لا يحتوي على نص قابل للاستخراج؛ قد يكون ممسوحاً ضوئياً.")
            else:
                image_info = inspect_image(content)
                if not image_info:
                    issues.append("تعذر فتح الصورة؛ تحقق من سلامة الملف.")
                else:
                    metadata.update({"width": image_info["width"], "height": image_info["height"], "format": image_info["format"]})
                    if image_info["issue"]:
                        issues.append(image_info["issue"])

            if not issues or all("نص قابل للاستخراج" in x for x in issues):
                status, relevance_note = assess_relevance(name, extracted_text, rule)
                if status == "mismatch":
                    issues.append(relevance_note)
                elif status == "needs_review":
                    issues.append(relevance_note)
                else:
                    issues.append(relevance_note)

        if not content or suffix not in ALLOWED_TYPES or len(content) > MAX_FILE_SIZE or any("تعذر" in x or "فارغ" in x for x in issues):
            status = "invalid_file"
        results.append({
            "name": name,
            "size": len(content),
            "status": status,
            "status_label": {"possible_match": "مؤشرات أولية — يحتاج مراجعة", "needs_review": "يحتاج مراجعة يدوية", "mismatch": "لم تظهر مطابقة كافية", "invalid_file": "مشكلة تقنية بالملف"}[status],
            "issues": issues,
            "metadata": metadata,
        })

    counts = {key: sum(1 for r in results if r["status"] == key) for key in ["possible_match", "needs_review", "mismatch", "invalid_file"]}
    return {
        "department": department,
        "transaction": transaction,
        "files": results,
        "counts": counts,
        "rule_mode": "demo_checklist" if rule else "no_demo_rule",
        "notice": "نتيجة تجريبية استرشادية فقط. لا تؤكد صحة المستند أو اكتماله أو قبوله، ولا تمثل متطلبات رسمية لأي جهة حكومية. راجع القنوات الرسمية قبل التقديم.",
    }
