const input = document.getElementById("documents");
const fileNames = document.getElementById("fileNames");
const form = document.getElementById("reviewForm");
const results = document.getElementById("results");
const btn = document.getElementById("submitBtn");

input.addEventListener("change", () => {
  fileNames.textContent = input.files.length
    ? [...input.files].map(f => f.name).join(" • ")
    : "لم يتم اختيار ملفات بعد";
});

document.getElementById("langBtn").addEventListener("click", () => {
  alert("سيتم تفعيل واجهة اللغة الإنجليزية في مرحلة التطوير التالية.");
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!input.files.length) return;
  btn.disabled = true;
  btn.textContent = "جارٍ فحص الملفات...";
  results.hidden = true;

  const data = new FormData();
  data.append("department", document.getElementById("department").value);
  data.append("transaction", document.getElementById("transaction").value);
  [...input.files].forEach(file => data.append("documents", file));

  try {
    const response = await fetch("/api/check", { method: "POST", body: data });
    const report = await response.json();
    results.innerHTML = `<h3>نتيجة الفحص الأولي</h3>
      <p>نسبة الملفات التي اجتازت الفحوصات الأساسية: <b>${report.score}%</b></p>
      <p>الجهة: ${escapeHtml(report.department)} — المعاملة: ${escapeHtml(report.transaction)}</p>
      ${report.files.map(f => `<div class="result-row"><b>${escapeHtml(f.name)}</b><br>${f.ok ? "✓ اجتاز الفحوصات الأساسية" : "⚠ " + f.issues.map(escapeHtml).join("، ")}</div>`).join("")}
      <div class="notice">${escapeHtml(report.notice)}</div>`;
    results.hidden = false;
    results.scrollIntoView({behavior:"smooth", block:"center"});
  } catch {
    results.innerHTML = "<p>تعذر إكمال الفحص. حاول مرة أخرى.</p>";
    results.hidden = false;
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'ابدأ الفحص التجريبي <span>←</span>';
  }
});

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
