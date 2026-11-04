const input = document.getElementById("documents");
const fileNames = document.getElementById("fileNames");
const form = document.getElementById("reviewForm");
const results = document.getElementById("results");
const btn = document.getElementById("submitBtn");

input.addEventListener("change", () => {
  fileNames.textContent = input.files.length
    ? [...input.files].map(f => `${f.name} (${(f.size/1024/1024).toFixed(2)} MB)`).join(" • ")
    : "لم يتم اختيار ملفات بعد";
});

document.getElementById("langBtn").addEventListener("click", () => {
  alert("واجهة QMX الحالية باللغة العربية. سيتم إضافة الإنجليزية في مرحلة لاحقة.");
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!input.files.length) return;
  btn.disabled = true;
  btn.textContent = "جارٍ تحليل الملفات وقراءة النص...";
  results.hidden = true;

  const data = new FormData();
  data.append("department", document.getElementById("department").value);
  data.append("transaction", document.getElementById("transaction").value);
  [...input.files].forEach(file => data.append("documents", file));

  try {
    const response = await fetch("/api/check", { method: "POST", body: data });
    const report = await response.json();
    if (!response.ok) throw new Error(report.detail || "تعذر إكمال الفحص");

    const c = report.counts;
    results.innerHTML = `
      <h3>تقرير المراجعة الأولية</h3>
      <p>الجهة: <b>${escapeHtml(report.department)}</b> — المعاملة: <b>${escapeHtml(report.transaction)}</b></p>
      <div class="summary-grid">
        <div><b>${c.possible_match}</b><small>مؤشرات أولية</small></div>
        <div><b>${c.needs_review}</b><small>تحتاج مراجعة</small></div>
        <div><b>${c.mismatch}</b><small>مطابقة غير كافية</small></div>
        <div><b>${c.invalid_file}</b><small>مشكلة تقنية</small></div>
      </div>
      ${report.files.map(f => `
        <article class="result-row ${f.status}">
          <div class="result-head"><b>${escapeHtml(f.name)}</b><span class="status-pill">${escapeHtml(f.status_label)}</span></div>
          ${f.metadata.width ? `<small>أبعاد الصورة: ${f.metadata.width} × ${f.metadata.height}</small>` : ""}
          ${f.metadata.pages ? `<small>عدد الصفحات: ${f.metadata.pages}</small>` : ""}
          ${f.metadata.text_characters ? `<small>النص المستخرج: ${f.metadata.text_characters} حرفاً — OCR: ${f.metadata.ocr_attempted ? "تمت المحاولة" : "غير مستخدم"}</small>` : ""}
          ${f.metadata.text_preview ? `<details><summary>معاينة النص المستخرج</summary><p class="text-preview">${escapeHtml(f.metadata.text_preview)}</p></details>` : ""}
          <ul>${f.issues.map(i => `<li>${escapeHtml(i)}</li>`).join("")}</ul>
        </article>`).join("")}
      <div class="notice">${escapeHtml(report.notice)}</div>`;
    results.hidden = false;
    results.scrollIntoView({behavior:"smooth", block:"center"});
  } catch (err) {
    results.innerHTML = `<p>${escapeHtml(err.message || "تعذر إكمال الفحص. حاول مرة أخرى.")}</p>`;
    results.hidden = false;
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'ابدأ الفحص التجريبي <span>←</span>';
  }
});

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
