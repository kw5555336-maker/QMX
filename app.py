from pathlib import Path
from io import BytesIO
import re
import logging

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageStat, UnidentifiedImageError
from pypdf import PdfReader
import pytesseract
from pdf2image import convert_from_bytes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("qmx")

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="QMX | Qamar AI", version="0.3.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {".pdf", ".png", ".jpg", ".jpeg"}
OCR_LANG = "ara+eng"

# Demo checklist only. Never treat these keywords as official requirements.
DEMO_RULES = {
    ("وزارة الخارجية", "تصديق مستند"): {
        "keywords": ["certificate", "certification", "شهادة", "تصديق", "وزارة", "ministry", "document"],
        "label": "مؤشرات نصية ذات صلة محتملة",
    }
}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    return {"status": "ok", "app": "QMX", "version": "0.3.0"}

def clean_text(value: str) -> str:
    value = re.sub(r"[ \t]+", " ", value or "")
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()

def run_ocr(image: Image.Image):
    try:
        return clean_text(pytesseract.image_to_string(image, lang=OCR_LANG))
    except Exception as exc:
        log.warning("OCR unavailable: %s", exc)
        return ""

def inspect_image(content: bytes):
    try:
        with Image.open(BytesIO(content)) as original:
            img = original.convert("RGB")
            width, height = img.size
            fmt = (original.format or "").upper()
            gray = img.convert("L")
            contrast = round(ImageStat.Stat(gray).stddev[0], 1)
            # A conservative signal only; this is not a true blur detector.
            low_contrast = contrast < 22
            return {
                "width": width, "height": height, "format": fmt,
                "contrast": contrast, "low_contrast": low_contrast,
                "image": img.copy()
            }
    except (UnidentifiedImageError, OSError):
        return None

def extract_pdf_text(content: bytes):
    try:
        reader = PdfReader(BytesIO(content), strict=False)
        page_count = len(reader.pages)
        text = clean_text("\n".join((p.extract_text() or "") for p in reader.pages[:15]))
        if text:
            return text, page_count, False, None
        # OCR only first 3 pages to limit CPU and processing time.
        pages = convert_from_bytes(content, first_page=1, last_page=min(page_count, 3), dpi=160)
        ocr_text = clean_text("\n".join(run_ocr(p) for p in pages))
        return ocr_text, page_count, bool(ocr_text), None
    except Exception as exc:
        log.info("PDF extraction/OCR failed: %s", exc)
        return "", 0, False, "تعذرت قراءة ملف PDF. قد يكون تالفاً أو محمياً أو تعذر تحليل صفحاته."

def assess_relevance(filename: str, extracted_text: str, rule):
    if not rule:
        return "needs_review", "لا توجد قائمة تحقق تجريبية لهذا النوع من المعاملات؛ يلزم تحديد المتطلبات ومراجعتها يدوياً."
    searchable = f"{filename} {extracted_text}".lower()
    hits = [word for word in rule["keywords"] if word.lower() in searchable]
    if hits:
        return "possible_match", "ظهرت مؤشرات نصية قد تتوافق مع المعاملة، لكنها لا تثبت صحة المستند أو اكتماله."
    if extracted_text:
        return "mismatch", "لم نعثر على مؤشرات نصية كافية تربط محتوى الملف بالمعاملة المختارة."
    return "needs_review", "لم نتمكن من استخراج نص قابل للمراجعة؛ يلزم فحص يدوي."

@app.post("/api/check")
async def check_document(
    department: str = Form(...),
    transaction: str = Form(...),
    documents: list[UploadFile] = File(...)
):
    if not documents:
        raise HTTPException(status_code=400, detail="يرجى إرفاق ملف واحد على الأقل.")
    if len(documents) > 10:
        raise HTTPException(status_code=400, detail="الحد الأقصى 10 ملفات في الفحص الواحد.")

    results = []
    rule = DEMO_RULES.get((department, transaction))

    for item in documents:
        name = (item.filename or "unnamed")[:180]
        suffix = Path(name).suffix.lower()
        content = await item.read()
        issues, extracted_text, metadata = [], "", {}
        status = "needs_review"

        if not content:
            issues.append("الملف فارغ.")
            status = "invalid_file"
        elif suffix not in ALLOWED_TYPES:
            issues.append("صيغة الملف غير مدعومة؛ الصيغ المقبولة PDF وJPG وPNG.")
            status = "invalid_file"
        elif len(content) > MAX_FILE_SIZE:
            issues.append("حجم الملف أكبر من 10MB.")
            status = "invalid_file"
        else:
            ocr_used = False
            if suffix == ".pdf":
                extracted_text, pages, ocr_used, pdf_error = extract_pdf_text(content)
                metadata["pages"] = pages
                if pdf_error:
                    issues.append(pdf_error)
                    status = "invalid_file"
                elif not extracted_text:
                    issues.append("لم يتم استخراج نص من الملف حتى بعد محاولة OCR؛ قد تكون الصفحات غير واضحة.")
            else:
                image_info = inspect_image(content)
                if not image_info:
                    issues.append("تعذر فتح الصورة؛ تحقق من سلامة الملف.")
                    status = "invalid_file"
                else:
                    metadata.update({
                        "width": image_info["width"], "height": image_info["height"],
                        "format": image_info["format"], "contrast": image_info["contrast"]
                    })
                    if image_info["width"] < 500 or image_info["height"] < 500:
                        issues.append("دقة الصورة منخفضة وقد يصعب قراءة التفاصيل.")
                    if image_info["low_contrast"]:
                        issues.append("التباين منخفض؛ تأكد من وضوح النص والإضاءة.")
                    extracted_text = run_ocr(image_info["image"])
                    ocr_used = True
                    if not extracted_text:
                        issues.append("لم يتمكن OCR من قراءة نص واضح؛ جرّب صورة أوضح أو راجع المستند يدوياً.")

            metadata["ocr_attempted"] = ocr_used
            metadata["text_characters"] = len(extracted_text)
            if extracted_text:
                metadata["text_preview"] = extracted_text[:260]
                status, relevance_note = assess_relevance(name, extracted_text, rule)
                issues.append(relevance_note)
            elif status != "invalid_file":
                status = "needs_review"

        status_labels = {
            "possible_match": "مؤشرات أولية — يحتاج مراجعة",
            "needs_review": "يحتاج مراجعة يدوية",
            "mismatch": "لم تظهر مطابقة كافية",
            "invalid_file": "مشكلة تقنية بالملف"
        }
        results.append({
            "name": name, "size": len(content), "status": status,
            "status_label": status_labels[status], "issues": issues, "metadata": metadata
        })

    keys = ["possible_match", "needs_review", "mismatch", "invalid_file"]
    counts = {key: sum(1 for r in results if r["status"] == key) for key in keys}
    return {
        "department": department, "transaction": transaction,
        "files": results, "counts": counts,
        "rule_mode": "demo_checklist" if rule else "no_demo_rule",
        "notice": "نتيجة تجريبية استرشادية فقط. OCR واستخراج الكلمات قد يخطئان، ولا تؤكد النتيجة صحة المستند أو اكتماله أو قبوله، ولا تمثل متطلبات رسمية لأي جهة حكومية. راجع القنوات الرسمية قبل التقديم."
    }
