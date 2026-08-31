const labels = {
  booked: "Записан", not_booked: "Не записан", rescheduled: "Перенесена",
  cancelled: "Отменена", not_applicable: "Не применимо", unknown: "Неизвестно",
  pending: "Ожидает", processing: "Анализируется", completed: "Готов", failed: "Ошибка"
};
const demoOrganizationId = "00000000-0000-0000-0000-000000000001";
const form = document.querySelector("#tenant-form");
const input = document.querySelector("#organization-id");
const message = document.querySelector("#message");
const content = document.querySelector("#content");
const uploadForm = document.querySelector("#upload-form");
const audioFile = document.querySelector("#audio-file");
const fileName = document.querySelector("#file-name");
const uploadStatus = document.querySelector("#upload-status");
const uploadButton = document.querySelector("#upload-button");

function escapeHtml(value) {
  const replacements = {"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"};
  return String(value).replace(/[&<>'"]/g, character => replacements[character]);
}
function renderBars(target, values) {
  const entries = Object.entries(values);
  const max = Math.max(...entries.map(([, value]) => value), 1);
  target.innerHTML = entries.length ? entries.map(([key, value]) => `<div class="bar-row"><span>${escapeHtml(labels[key] ?? key)}</span><div class="bar-track"><div class="bar" style="width:${value / max * 100}%"></div></div><strong>${value}</strong></div>`).join("") : "<p class='message'>Пока нет данных</p>";
}
function formatDuration(seconds) {
  if (seconds == null) return "—";
  return `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, "0")}`;
}
function setUploadStatus(text, type = "") {
  uploadStatus.textContent = text;
  uploadStatus.className = `upload-status ${type}`;
}
async function request(path, options = {}) {
  const organizationId = input.value.trim();
  const headers = new Headers(options.headers ?? {});
  headers.set("X-Organization-ID", organizationId);
  const response = await fetch(path, {...options, headers});
  if (!response.ok) throw new Error("Не удалось получить данные. Проверьте статус сервисов и ID организации.");
  return response.json();
}
async function loadDashboard() {
  message.textContent = "Загружаем данные…";
  content.hidden = true;
  const [statistics, calls] = await Promise.all([request("/api/v1/statistics"), request("/api/v1/dashboard/calls?limit=5")]);
  document.querySelector("#total").textContent = statistics.total_calls;
  document.querySelector("#conversion").textContent = statistics.booking_conversion_rate == null ? "—" : `${Math.round(statistics.booking_conversion_rate * 100)}%`;
  document.querySelector("#quality").textContent = statistics.average_quality_score == null ? "—" : `${Math.round(statistics.average_quality_score)}/100`;
  document.querySelector("#duration").textContent = formatDuration(statistics.average_duration_seconds);
  renderBars(document.querySelector("#appointments"), statistics.appointments);
  renderBars(document.querySelector("#statuses"), statistics.statuses);
  document.querySelector("#calls").innerHTML = calls.length ? calls.map(call => `<tr><td>${escapeHtml(call.original_filename)}</td><td>${escapeHtml(call.topic ?? "—")}</td><td><span class="badge ${call.appointment_status === "booked" ? "booked" : ""}">${escapeHtml(labels[call.appointment_status] ?? "—")}</span></td><td>${call.quality_score == null ? "—" : `${call.quality_score}/100`}</td><td class="${call.status === "completed" ? "ready" : call.status === "failed" ? "failed" : ""}">${escapeHtml(labels[call.status])}</td></tr>`).join("") : "<tr><td class='empty-cell' colspan='5'>Загрузите первый MP3, чтобы увидеть аналитику.</td></tr>";
  message.textContent = "";
  content.hidden = false;
  localStorage.setItem("organizationId", input.value.trim());
}
async function pollCall(callId) {
  const call = await request(`/api/v1/calls/${callId}`);
  if (call.status === "completed") {
    setUploadStatus("Анализ завершён. Dashboard обновлён.", "success");
    await loadDashboard();
    return;
  }
  if (call.status === "failed") {
    setUploadStatus(`Ошибка обработки: ${call.error_message ?? "неизвестная ошибка"}`, "error");
    await loadDashboard();
    return;
  }
  setUploadStatus(`Звонок ${labels[call.status].toLowerCase()}. Обновим результат через несколько секунд.`);
  window.setTimeout(() => pollCall(callId).catch(() => setUploadStatus("Не удалось получить статус. Нажмите «Обновить».", "error")), 5000);
}

audioFile.addEventListener("change", () => { fileName.textContent = audioFile.files[0]?.name ?? "Выбрать MP3"; });
uploadForm.addEventListener("submit", async event => {
  event.preventDefault();
  const file = audioFile.files[0];
  if (!file) return;
  uploadButton.disabled = true;
  setUploadStatus("Загружаем файл и ставим его в очередь…");
  try {
    const payload = new FormData(); payload.append("file", file);
    const call = await request("/api/v1/calls", {method:"POST", body:payload});
    setUploadStatus("Файл принят. Начинаем анализ…", "success");
    audioFile.value = ""; fileName.textContent = "Выбрать MP3";
    await loadDashboard();
    pollCall(call.id).catch(() => setUploadStatus("Не удалось получить статус. Нажмите «Обновить».", "error"));
  } catch (error) { setUploadStatus(error.message, "error"); }
  finally { uploadButton.disabled = false; }
});
form.addEventListener("submit", async event => { event.preventDefault(); try { await loadDashboard(); } catch (error) { message.textContent = error.message; } });
document.querySelector("#refresh").addEventListener("click", () => loadDashboard().catch(error => { message.textContent = error.message; }));
input.value = localStorage.getItem("organizationId") ?? demoOrganizationId;
loadDashboard().catch(error => { message.textContent = error.message; });
