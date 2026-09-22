/* 开源依赖许可审查 —— 前端逻辑 */

const STATUS_LABEL = {
  conflict: "冲突",
  warning: "告警",
  ok: "兼容",
  exempted: "已豁免",
};

let currentReview = null;
let policies = [];

/* ---------- 初始化 ---------- */

async function init() {
  await Promise.all([loadPolicies(), loadHistory()]);
  bindEvents();
}

async function loadPolicies() {
  policies = await fetch("/api/policies").then((r) => r.json());
  const select = document.getElementById("policy-select");
  select.innerHTML = "";
  for (const p of policies) {
    const opt = document.createElement("option");
    opt.value = p.key;
    opt.textContent = p.label;
    select.appendChild(opt);
  }
  updatePolicyDesc();
}

function updatePolicyDesc() {
  const key = document.getElementById("policy-select").value;
  const p = policies.find((x) => x.key === key);
  document.getElementById("policy-desc").textContent = p ? p.description : "";
}

async function loadHistory() {
  const items = await fetch("/api/reviews").then((r) => r.json());
  const ul = document.getElementById("history-list");
  ul.innerHTML = "";
  if (!items.length) {
    ul.innerHTML = "<li>暂无记录</li>";
    return;
  }
  ul.classList.remove("muted");
  for (const it of items) {
    const li = document.createElement("li");
    const s = it.summary || {};
    li.innerHTML =
      `<a href="#" data-id="${it.id}">#${it.id} ${escapeHtml(it.project_name)}</a>` +
      ` <span class="muted">${escapeHtml(it.policy_label)} · ${it.created_at}</span>` +
      ` <span class="badge st-conflict">${s.conflict || 0} 冲突</span>` +
      ` <span class="badge st-warning">${s.warning || 0} 告警</span>`;
    li.querySelector("a").addEventListener("click", (e) => {
      e.preventDefault();
      openReview(it.id);
    });
    ul.appendChild(li);
  }
}

function bindEvents() {
  document.getElementById("policy-select").addEventListener("change", updatePolicyDesc);
  document.getElementById("file-input").addEventListener("change", onFileChosen);
  document.getElementById("btn-sample").addEventListener("click", loadSample);
  document.getElementById("btn-run").addEventListener("click", runReview);
  document.getElementById("btn-recalc").addEventListener("click", recalculate);
  document.getElementById("btn-export").addEventListener("click", exportJson);
}

/* ---------- 上传 ---------- */

function onFileChosen(e) {
  const file = e.target.files[0];
  if (!file) return;
  document.getElementById("file-name").textContent = file.name;
  const reader = new FileReader();
  reader.onload = () => {
    document.getElementById("manifest-input").value = reader.result;
  };
  reader.readAsText(file);
}

async function loadSample() {
  const data = await fetch("/api/sample-manifest").then((r) => r.json());
  document.getElementById("manifest-input").value = JSON.stringify(data, null, 2);
  document.getElementById("file-name").textContent = "示例清单";
}

async function runReview() {
  const errEl = document.getElementById("upload-error");
  errEl.textContent = "";
  let manifest;
  try {
    manifest = JSON.parse(document.getElementById("manifest-input").value);
  } catch (e) {
    errEl.textContent = "JSON 解析失败：" + e.message;
    return;
  }
  const resp = await fetch("/api/reviews", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      policy: document.getElementById("policy-select").value,
      manifest,
    }),
  });
  const data = await resp.json();
  if (!resp.ok) {
    errEl.textContent = data.detail || "审查失败";
    return;
  }
  renderReview(data);
  loadHistory();
}

/* ---------- 结果渲染 ---------- */

function renderReview(review) {
  currentReview = review;
  const r = review.result;
  document.getElementById("result-section").classList.remove("hidden");
  document.getElementById("result-meta").textContent =
    `#${review.id} · ${r.project.name} ${r.project.version} · 策略：${r.policy_label}`;

  const s = r.summary;
  const cards = [
    ["依赖总数", s.total, ""],
    ["冲突", s.conflict, "st-conflict"],
    ["告警", s.warning, "st-warning"],
    ["已豁免", s.exempted, "st-exempted"],
    ["兼容", s.ok, "st-ok"],
    ["游离依赖", s.unreachable, ""],
  ];
  document.getElementById("summary-cards").innerHTML = cards
    .map(
      ([label, val, cls]) =>
        `<div class="card-mini ${cls}"><div class="num">${val}</div><div>${label}</div></div>`
    )
    .join("");

  renderExceptions(review.exceptions);
  renderFindings(r.findings, review.exceptions);
  document.getElementById("result-section").scrollIntoView({ behavior: "smooth" });
}

function renderExceptions(exceptions) {
  const box = document.getElementById("exceptions-list");
  if (!exceptions.length) {
    box.className = "exceptions muted";
    box.textContent = "暂无例外包";
    return;
  }
  box.className = "exceptions";
  box.innerHTML = "";
  for (const ex of exceptions) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.innerHTML =
      `<strong>${escapeHtml(ex.package)}</strong>` +
      (ex.note ? ` <span class="muted">${escapeHtml(ex.note)}</span>` : "") +
      ` <button title="移除例外" data-pkg="${escapeHtml(ex.package)}">✕</button>`;
    chip.querySelector("button").addEventListener("click", () => removeException(ex.package));
    box.appendChild(chip);
  }
}

function renderFindings(findings, exceptions) {
  const tbody = document.querySelector("#findings-table tbody");
  tbody.innerHTML = "";
  for (const f of findings) {
    const tr = document.createElement("tr");
    tr.className = "row-" + f.status;

    const pathHtml = f.reachable
      ? f.path.map((p) => `<span class="node">${escapeHtml(p)}</span>`).join('<span class="arrow">→</span>')
      : `<span class="node">${escapeHtml(f.package)}</span> <span class="muted">（游离依赖，不在依赖图中）</span>`;

    const canExempt = f.original_status !== "ok" && !f.exempted;
    const actionHtml = f.exempted
      ? '<span class="muted">已豁免</span>'
      : canExempt
        ? `<button class="btn tiny" data-pkg="${escapeHtml(f.package)}">标记例外</button>`
        : "";

    tr.innerHTML =
      `<td><span class="badge st-${f.status}">${STATUS_LABEL[f.status]}</span></td>` +
      `<td><strong>${escapeHtml(f.package)}</strong> <span class="muted">${escapeHtml(f.version)}</span></td>` +
      `<td>${escapeHtml(f.license)}${f.license !== f.license_raw ? ` <span class="muted">(${escapeHtml(String(f.license_raw))})</span>` : ""}</td>` +
      `<td class="rule">${escapeHtml(f.rule)}</td>` +
      `<td class="path">${pathHtml}</td>` +
      `<td>${actionHtml}</td>`;

    const btn = tr.querySelector("button");
    if (btn) btn.addEventListener("click", () => addException(f.package));
    tbody.appendChild(tr);
  }
}

/* ---------- 例外 / 重算 / 导出 ---------- */

async function addException(pkg) {
  const note = prompt(`为「${pkg}」添加例外说明（可选）：`) || "";
  const resp = await fetch(`/api/reviews/${currentReview.id}/exceptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ package: pkg, note }),
  });
  const data = await resp.json();
  if (!resp.ok) {
    alert(data.detail || "操作失败");
    return;
  }
  renderReview(data);
}

async function removeException(pkg) {
  const resp = await fetch(
    `/api/reviews/${currentReview.id}/exceptions/${encodeURIComponent(pkg)}`,
    { method: "DELETE" }
  );
  const data = await resp.json();
  if (!resp.ok) {
    alert(data.detail || "操作失败");
    return;
  }
  renderReview(data);
}

async function recalculate() {
  if (!currentReview) return;
  const resp = await fetch(`/api/reviews/${currentReview.id}/recalculate`, { method: "POST" });
  const data = await resp.json();
  if (!resp.ok) {
    alert(data.detail || "重新计算失败");
    return;
  }
  renderReview(data);
  loadHistory();
}

function exportJson() {
  if (!currentReview) return;
  window.location.href = `/api/reviews/${currentReview.id}/export`;
}

async function openReview(id) {
  const resp = await fetch(`/api/reviews/${id}`);
  const data = await resp.json();
  if (!resp.ok) {
    alert(data.detail || "加载失败");
    return;
  }
  renderReview(data);
}

/* ---------- 工具 ---------- */

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

init();
