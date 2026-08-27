const labels = {
  booked: "Записан", not_booked: "Не записан", rescheduled: "Перенесена",
  cancelled: "Отменена", not_applicable: "Не применимо", unknown: "Неизвестно",
  pending: "Ожидает", processing: "Обработка", completed: "Готов", failed: "Ошибка"
};

const form = document.querySelector("#tenant-form");
const input = document.querySelector("#organization-id");
const message = document.querySelector("#message");
const content = document.querySelector("#content");

function renderBars(target, values) {
  const entries = Object.entries(values);
  const max = Math.max(...entries.map(([, value]) => value), 1);
  target.innerHTML = entries.length ? entries.map(([key, value]) => `
    <div class="bar-row"><span>${labels[key] ?? key}</span>
      <div class="bar-track"><div class="bar" style="width:${value / max * 100}%"></div></div>
      <strong>${value}</strong></div>`).join("") : "<p class='message'>Нет данных</p>";
}

function formatDuration(seconds) {
  if (seconds == null) return "—";
  return `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, "0")}`;
}

async function loadDashboard(organizationId) {
  message.textContent = "Загружаем статистику…";
  content.hidden = true;
  const options = {headers: {"X-Organization-ID": organizationId}};
  const [statisticsResponse, callsResponse] = await Promise.all([
    fetch("/api/v1/statistics", options), fetch("/api/v1/dashboard/calls", options)
  ]);
  if (!statisticsResponse.ok || !callsResponse.ok) throw new Error("Не удалось получить данные. Проверь Organization ID.");
  const statistics = await statisticsResponse.json();
  const calls = await callsResponse.json();
  document.querySelector("#total").textContent = statistics.total_calls;
  document.querySelector("#conversion").textContent = statistics.booking_conversion_rate == null ? "—" : `${Math.round(statistics.booking_conversion_rate * 100)}%`;
  document.querySelector("#quality").textContent = statistics.average_quality_score == null ? "—" : `${Math.round(statistics.average_quality_score)}/100`;
  document.querySelector("#duration").textContent = formatDuration(statistics.average_duration_seconds);
  renderBars(document.querySelector("#appointments"), statistics.appointments);
  renderBars(document.querySelector("#statuses"), statistics.statuses);
  document.querySelector("#calls").innerHTML = calls.map(call => `<tr>
    <td>${call.original_filename}</td><td>${call.topic ?? "—"}</td>
    <td><span class="badge ${call.appointment_status === "booked" ? "booked" : ""}">${labels[call.appointment_status] ?? "—"}</span></td>
    <td>${call.quality_score == null ? "—" : `${call.quality_score}/100`}</td>
    <td>${new Date(call.created_at).toLocaleString("ru-RU")}</td></tr>`).join("") || "<tr><td colspan='5'>Звонков пока нет</td></tr>";
  message.textContent = "";
  content.hidden = false;
  localStorage.setItem("organizationId", organizationId);
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  try { await loadDashboard(input.value.trim()); } catch (error) { message.textContent = error.message; }
});

const savedId = localStorage.getItem("organizationId") ?? "00000000-0000-0000-0000-000000000001";
input.value = savedId;
loadDashboard(savedId).catch(error => { message.textContent = error.message; });
