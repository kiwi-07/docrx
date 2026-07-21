const SAMPLE = `# Example with common pitfalls
FROM python:latest

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y curl

EXPOSE 8000
CMD ["python", "app.py"]
`;

const CAT_LABELS = {
  cache: "Cache",
  size: "Size",
  security: "Security",
  maintainability: "Maintainability",
  best_practices: "Best practices",
};

const el = {
  dockerfile: document.getElementById("dockerfile"),
  lineCount: document.getElementById("line-count"),
  analyze: document.getElementById("btn-analyze"),
  loading: document.getElementById("btn-loading"),
  btnLabel: document.getElementById("btn-label"),
  sample: document.getElementById("btn-sample"),
  clear: document.getElementById("btn-clear"),
  emptyAnalyze: document.getElementById("btn-empty-analyze"),
  status: document.getElementById("status"),
  dockerignore: document.getElementById("opt-dockerignore"),
  report: document.getElementById("report"),
  empty: document.getElementById("empty"),
  scoreRadial: document.getElementById("score-radial"),
  scoreNum: document.getElementById("score-num"),
  scoreLabel: document.getElementById("score-label"),
  scoreSub: document.getElementById("score-sub"),
  categories: document.getElementById("categories"),
  diag: document.getElementById("diag"),
  layers: document.getElementById("layers"),
  findings: document.getElementById("findings"),
  findingsCount: document.getElementById("findings-count"),
  btnKeys: document.getElementById("btn-keys"),
  tabs: [...document.querySelectorAll("[data-tool]")],
  panes: [...document.querySelectorAll("[data-pane]")],
  fixPreviewButton: document.getElementById("btn-fix-preview"),
  fixApplyButton: document.getElementById("btn-fix-apply"),
  fixDownloadButton: document.getElementById("btn-fix-download"),
  fixOptions: document.getElementById("fix-options"),
  fixPreview: document.getElementById("fix-preview"),
  fixStatus: document.getElementById("fix-status"),
  dockerignorePreview: document.getElementById("dockerignore-preview"),
  dockerignoreCode: document.getElementById("dockerignore-code"),
  formatButton: document.getElementById("btn-format"),
  formatDownloadButton: document.getElementById("btn-format-download"),
  formatPreview: document.getElementById("format-preview"),
  formatStatus: document.getElementById("format-status"),
  compareBefore: document.getElementById("compare-before"),
  compareAfter: document.getElementById("compare-after"),
  compareButton: document.getElementById("btn-compare"),
  compareResult: document.getElementById("compare-result"),
  compareHeadline: document.getElementById("compare-headline"),
  compareScoreBefore: document.getElementById("compare-score-before"),
  compareScoreAfter: document.getElementById("compare-score-after"),
  compareDelta: document.getElementById("compare-delta"),
  compareResolved: document.getElementById("compare-resolved"),
  compareNew: document.getElementById("compare-new"),
  compareStatus: document.getElementById("compare-status"),
  badgeButton: document.getElementById("btn-badge"),
  badgeLabel: document.getElementById("badge-label"),
  badgeStyle: document.getElementById("badge-style"),
  badgeStatus: document.getElementById("badge-status"),
  badgePreview: document.getElementById("badge-preview"),
  badgeDownloadButton: document.getElementById("btn-badge-download"),
  badgeMarkdownButton: document.getElementById("btn-badge-markdown"),
  badgeUrlButton: document.getElementById("btn-badge-url"),
};

let fixedDockerfile = "";
let formattedDockerfile = "";
let badgeData = null;

function isMac() {
  return /Mac|iPhone|iPad/.test(navigator.platform) || navigator.userAgent.includes("Mac");
}

function setStatus(message, tone = "") {
  el.status.textContent = message;
  el.status.className = "text-sm m-0";
  if (tone === "error") el.status.classList.add("text-error");
  else if (tone === "busy") el.status.classList.add("text-info");
  else if (tone === "ok") el.status.classList.add("text-success");
  else el.status.classList.add("opacity-70");
}

function updateLineCount() {
  const text = el.dockerfile.value;
  const lines = text.length ? text.split("\n").length : 1;
  el.lineCount.textContent = `${lines} line${lines === 1 ? "" : "s"}`;
}

function parseLines(text) {
  return text.replace(/\r\n/g, "\n").split("\n");
}

function instructionLines(text) {
  const lines = parseLines(text);
  const hits = [];
  for (let i = 0; i < lines.length; i += 1) {
    const trimmed = lines[i].trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    if (/^[A-Za-z]+\s+/.test(trimmed)) hits.push(i + 1);
  }
  return hits.length ? hits : lines.map((_, i) => i + 1).slice(0, 24);
}

function severityRank(sev) {
  return { HIGH: 0, MEDIUM: 1, LOW: 2, INFO: 3 }[sev] ?? 9;
}

function badgeClass(sev) {
  if (sev === "HIGH") return "badge badge-error badge-sm";
  if (sev === "MEDIUM") return "badge badge-warning badge-sm";
  if (sev === "LOW") return "badge badge-info badge-sm";
  return "badge badge-ghost badge-sm";
}

function progressClass(score, max) {
  const ratio = max ? score / max : 0;
  if (ratio >= 0.75) return "progress progress-success w-full";
  if (ratio >= 0.45) return "progress progress-warning w-full";
  return "progress progress-error w-full";
}

function radialTone(score) {
  if (score >= 90) return "text-success";
  if (score >= 75) return "text-success";
  if (score >= 60) return "text-warning";
  return "text-error";
}

function renderLayers(text, recommendations) {
  const lines = instructionLines(text);
  const byLine = new Map();
  for (const rec of recommendations || []) {
    if (rec.line == null) continue;
    const prev = byLine.get(rec.line);
    if (!prev || severityRank(rec.severity) < severityRank(prev)) {
      byLine.set(rec.line, rec.severity);
    }
  }

  el.layers.replaceChildren();
  lines.slice(0, 64).forEach((line) => {
    const sev = byLine.get(line);
    const wrap = document.createElement("div");
    wrap.className = "tooltip";
    wrap.dataset.tip = sev ? `Line ${line} · ${sev}` : `Line ${line}`;

    const bar = document.createElement("button");
    bar.type = "button";
    bar.className = "btn btn-xs h-5 min-h-5 w-2.5 p-0 border-0";
    if (sev === "HIGH") bar.classList.add("btn-error");
    else if (sev === "MEDIUM") bar.classList.add("btn-warning");
    else if (sev) bar.classList.add("btn-info");
    else bar.classList.add("btn-ghost", "bg-base-300");

    bar.addEventListener("click", () => {
      const finding = el.findings.querySelector(`[data-line="${line}"]`);
      if (finding) finding.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });

    wrap.append(bar);
    el.layers.appendChild(wrap);
  });
}

function renderCategories(categories) {
  const entries = Object.entries(categories || {});
  el.categories.replaceChildren(
    ...entries.map(([key, value]) => {
      const row = document.createElement("div");
      row.className = "grid grid-cols-[7.5rem_1fr_auto] items-center gap-2";

      const name = document.createElement("span");
      name.className = "text-xs uppercase tracking-wide opacity-60";
      name.textContent = CAT_LABELS[key] || key;

      const bar = document.createElement("progress");
      bar.className = progressClass(value.score ?? 0, value.max ?? 1);
      bar.max = value.max ?? 100;
      bar.value = value.score ?? 0;

      const score = document.createElement("span");
      score.className = "font-mono text-xs tabular-nums";
      score.textContent = `${value.score ?? 0}/${value.max ?? 0}`;

      row.append(name, bar, score);
      return row;
    }),
  );
}

async function copyText(button, text) {
  const original = button.textContent;
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = "Copied";
    setTimeout(() => {
      button.textContent = original;
    }, 1400);
  } catch {
    button.textContent = "Failed";
    setTimeout(() => {
      button.textContent = original;
    }, 1400);
  }
}

function renderReport(data, sourceText) {
  el.empty.classList.add("hidden");
  el.report.classList.remove("hidden");

  const score = Number(data.score ?? 0);
  el.scoreRadial.style.setProperty("--value", String(score));
  el.scoreRadial.setAttribute("aria-valuenow", String(score));
  el.scoreRadial.className = `radial-progress ${radialTone(score)}`;
  el.scoreRadial.style.setProperty("--size", "4.5rem");
  el.scoreRadial.style.setProperty("--thickness", "6px");
  el.scoreNum.textContent = String(score);
  el.scoreLabel.textContent = [data.health?.emoji, data.health?.label || "Health"].filter(Boolean).join(" ");

  const stages = data.stage_count ?? 0;
  const instructions = data.instruction_count ?? 0;
  el.scoreSub.textContent = `${instructions} instructions · ${stages} stage${stages === 1 ? "" : "s"}`;

  renderCategories(data.categories);

  const d = data.diagnosis || {};
  const chips = [
    `${d.total ?? 0} findings`,
    d.high ? `${d.high} high` : null,
    d.medium ? `${d.medium} medium` : null,
    d.potential_image_mb || null,
    d.potential_build_pct || null,
  ].filter(Boolean);

  el.diag.replaceChildren(
    ...chips.map((text) => {
      const span = document.createElement("span");
      span.className = "badge badge-ghost badge-sm";
      span.textContent = text;
      return span;
    }),
  );

  renderLayers(sourceText, data.recommendations);

  const recs = data.recommendations || [];
  el.findingsCount.textContent =
    recs.length === 0 ? "Clean bill of health" : `${recs.length} ranked`;

  el.findings.replaceChildren(
    ...recs.map((rec, index) => {
      const li = document.createElement("li");
      li.className = "list-row items-start";
      if (rec.line != null) li.dataset.line = String(rec.line);

      const rank = document.createElement("div");
      rank.className = "font-mono text-xs opacity-50 pt-1";
      rank.textContent = String(rec.rank ?? index + 1).padStart(2, "0");

      const body = document.createElement("div");
      body.className = "list-col-grow";

      const collapse = document.createElement("div");
      collapse.className = "collapse collapse-arrow bg-base-100";
      if (index === 0) collapse.classList.add("collapse-open");

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      if (index === 0) checkbox.checked = true;

      const title = document.createElement("div");
      title.className = "collapse-title font-medium min-h-0 py-3 px-3";

      const titleRow = document.createElement("div");
      titleRow.className = "flex flex-wrap items-center gap-2 pr-6";

      const sev = document.createElement("span");
      sev.className = badgeClass(rec.severity || "INFO");
      sev.textContent = rec.severity || "INFO";

      const heading = document.createElement("span");
      heading.textContent = rec.short_title || rec.title;

      const id = document.createElement("span");
      id.className = "badge badge-ghost badge-sm font-mono";
      id.textContent = rec.id;

      titleRow.append(sev, heading, id);

      if (rec.roi_score != null) {
        const roi = document.createElement("span");
        roi.className = "badge badge-ghost badge-sm font-mono ml-auto";
        roi.textContent = `ROI ${rec.roi_score}`;
        roi.title = "Return on investment: impact vs. effort";
        titleRow.append(roi);
      }

      title.append(titleRow);

      const content = document.createElement("div");
      content.className = "collapse-content text-sm px-3";

      const bits = [];
      if (rec.line != null) bits.push(`line ${rec.line}`);
      if (rec.stage) bits.push(`stage ${rec.stage}`);
      if (rec.impact) bits.push(rec.impact);
      if (rec.effort) bits.push(rec.effort);

      if (bits.length) {
        const meta = document.createElement("p");
        meta.className = "opacity-60 mb-2";
        meta.textContent = bits.join(" · ");
        content.append(meta);
      }

      if (rec.reason) {
        const why = document.createElement("div");
        why.className = "alert alert-soft mb-3 py-2 text-sm";
        const whyText = document.createElement("span");
        whyText.textContent = `Why it matters: ${rec.reason}`;
        why.append(whyText);
        content.append(why);
      }

      const recText = document.createElement("p");
      recText.className = "mb-3";
      recText.textContent = rec.recommendation || "";
      content.append(recText);

      if (rec.suggested_fix) {
        const pre = document.createElement("pre");
        pre.className = "bg-base-200 rounded-box p-3 font-mono text-xs whitespace-pre-wrap mb-2";
        pre.textContent = rec.suggested_fix;

        const copy = document.createElement("button");
        copy.type = "button";
        copy.className = "btn btn-xs";
        copy.textContent = "Copy fix";
        copy.addEventListener("click", (event) => {
          event.stopPropagation();
          copyText(copy, rec.suggested_fix);
        });

        content.append(pre, copy);
      }

      const saving = rec.estimated_saving || {};
      const savingBits = [
        saving.image_size ? `Image: ${saving.image_size}` : null,
        saving.build_time ? `Build: ${saving.build_time}` : null,
      ].filter(Boolean);
      if (savingBits.length) {
        const savingWrap = document.createElement("div");
        savingWrap.className = "mt-2 flex flex-wrap gap-1";
        for (const text of savingBits) {
          const b = document.createElement("span");
          b.className = "badge badge-ghost badge-sm";
          b.textContent = text;
          savingWrap.append(b);
        }
        content.append(savingWrap);
      }

      const refs = rec.references || [];
      if (refs.length) {
        const refWrap = document.createElement("div");
        refWrap.className = "mt-2 flex flex-col gap-1";
        refs.forEach((href, i) => {
          const a = document.createElement("a");
          a.className = "link link-hover text-xs opacity-70";
          a.href = href;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          a.textContent = `Reference ${refs.length > 1 ? i + 1 : ""}`.trim();
          refWrap.append(a);
        });
        content.append(refWrap);
      }

      collapse.append(checkbox, title, content);
      body.append(collapse);
      li.append(rank, body);
      return li;
    }),
  );

  if (window.matchMedia("(max-width: 1023px)").matches) {
    el.report.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

const MAX_DOCKERFILE_CHARS = 200_000;
const ANALYZE_TIMEOUT_MS = 25_000;

function extractError(payload, res) {
  const detail = payload?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msg = detail
      .map((d) => (d && typeof d.msg === "string" ? d.msg.replace(/^Value error,\s*/, "") : null))
      .filter(Boolean)
      .join("; ");
    if (msg) return msg;
  }
  return res?.statusText || "Request failed";
}

function currentPayload() {
  return {
    dockerfile: el.dockerfile.value,
    filename: "Dockerfile",
    has_dockerignore: el.dockerignore?.checked ?? false,
  };
}

async function requestJson(path, payload) {
  if (!payload?.dockerfile?.trim() && path !== "/api/compare") {
    throw new Error("Paste a Dockerfile in the Check tab first.");
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ANALYZE_TIMEOUT_MS);
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(extractError(data, res));
    return data;
  } catch (err) {
    if (err?.name === "AbortError") throw new Error("Request timed out. Try a smaller Dockerfile.");
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

function downloadText(filename, text, type = "text/plain;charset=utf-8") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function status(element, message, tone = "") {
  element.textContent = message;
  element.className = "text-sm";
  if (tone === "error") element.classList.add("text-error");
  else if (tone === "ok") element.classList.add("text-success");
  else element.classList.add("opacity-70");
}

function switchTool(name) {
  el.tabs.forEach((tab) => {
    tab.classList.toggle("tab-active", tab.dataset.tool === name);
    tab.setAttribute("aria-selected", tab.dataset.tool === name ? "true" : "false");
  });
  el.panes.forEach((pane) => pane.classList.toggle("hidden", pane.dataset.pane !== name));
  if (name === "compare") el.compareBefore.textContent = el.dockerfile.value;
}

function renderFixOptions(fixes, selectedIds) {
  el.fixOptions.replaceChildren();
  for (const fix of fixes) {
    const label = document.createElement("label");
    label.className = "label cursor-pointer justify-start gap-3 rounded-box bg-base-100 px-3 py-2";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "checkbox checkbox-sm";
    checkbox.value = fix.id;
    checkbox.checked = selectedIds.includes(fix.id);
    const copy = document.createElement("span");
    copy.className = "min-w-0";
    const title = document.createElement("span");
    title.className = "block text-sm font-medium";
    title.textContent = fix.title;
    const meta = document.createElement("span");
    meta.className = "block text-xs opacity-60 font-mono";
    meta.textContent = `${fix.id} · ${fix.severity}`;
    copy.append(title, meta);
    label.append(checkbox, copy);
    el.fixOptions.append(label);
  }
}

async function buildFixPreview(ruleIds = null) {
  status(el.fixStatus, "Building a deterministic preview…");
  el.fixPreviewButton.disabled = true;
  el.fixApplyButton.disabled = true;
  try {
    const payload = currentPayload();
    if (ruleIds !== null) payload.rule_ids = ruleIds;
    const data = await requestJson("/api/fix", payload);
    renderFixOptions(data.available_fixes || [], data.applied_rule_ids || []);
    fixedDockerfile = data.dockerfile || el.dockerfile.value;
    el.fixPreview.querySelector("code").textContent = fixedDockerfile;
    el.compareAfter.value = fixedDockerfile;
    el.fixApplyButton.classList.toggle("hidden", !(data.available_fixes || []).length);
    el.fixDownloadButton.classList.remove("hidden");
    el.dockerignorePreview.classList.toggle("hidden", !data.dockerignore_added);
    el.dockerignoreCode.textContent = data.dockerignore || "";
    const count = (data.applied_rule_ids || []).length;
    status(
      el.fixStatus,
      count ? `${count} selected fix${count === 1 ? "" : "es"} applied to the preview.` : "No supported fixes selected.",
      "ok",
    );
  } catch (err) {
    status(el.fixStatus, err.message || "Fix preview failed.", "error");
  } finally {
    el.fixPreviewButton.disabled = false;
    el.fixApplyButton.disabled = false;
  }
}

async function formatCurrent() {
  status(el.formatStatus, "Formatting…");
  el.formatButton.disabled = true;
  try {
    const data = await requestJson("/api/format", currentPayload());
    formattedDockerfile = data.dockerfile;
    el.formatPreview.querySelector("code").textContent = formattedDockerfile;
    el.compareAfter.value = formattedDockerfile;
    el.formatDownloadButton.classList.remove("hidden");
    status(el.formatStatus, data.changed ? "Formatting changes are ready to download." : "Already formatted.", "ok");
  } catch (err) {
    status(el.formatStatus, err.message || "Formatting failed.", "error");
  } finally {
    el.formatButton.disabled = false;
  }
}

function renderRuleBadges(container, ruleIds, emptyText) {
  container.replaceChildren();
  if (!ruleIds.length) {
    const text = document.createElement("span");
    text.className = "text-sm opacity-60";
    text.textContent = emptyText;
    container.append(text);
    return;
  }
  for (const id of ruleIds) {
    const badge = document.createElement("span");
    badge.className = "badge badge-ghost font-mono";
    badge.textContent = id;
    container.append(badge);
  }
}

async function compareCurrent() {
  status(el.compareStatus, "");
  el.compareButton.disabled = true;
  try {
    const data = await requestJson("/api/compare", {
      before: el.dockerfile.value,
      after: el.compareAfter.value,
      before_has_dockerignore: el.dockerignore?.checked ?? false,
      after_has_dockerignore: el.dockerignore?.checked ?? false,
    });
    const delta = data.delta.score;
    el.compareScoreBefore.textContent = data.before.score;
    el.compareScoreAfter.textContent = data.after.score;
    el.compareDelta.textContent = `${delta >= 0 ? "+" : ""}${delta}`;
    el.compareDelta.className = `stat-value ${delta >= 0 ? "text-success" : "text-error"}`;
    el.compareHeadline.textContent =
      delta > 0 ? "The updated Dockerfile is healthier." : delta < 0 ? "The updated Dockerfile regressed." : "Health is unchanged.";
    renderRuleBadges(el.compareResolved, data.delta.resolved_rule_ids || [], "No findings resolved.");
    renderRuleBadges(el.compareNew, data.delta.new_rule_ids || [], "No new findings.");
    el.compareResult.classList.remove("hidden");
  } catch (err) {
    status(el.compareStatus, err.message || "Comparison failed.", "error");
  } finally {
    el.compareButton.disabled = false;
  }
}

async function generateBadge() {
  status(el.badgeStatus, "Generating…");
  el.badgeButton.disabled = true;
  try {
    badgeData = await requestJson("/api/badge", {
      ...currentPayload(),
      label: el.badgeLabel.value.trim() || "DockRx",
      style: el.badgeStyle.value,
    });
    el.badgePreview.innerHTML = badgeData.svg;
    el.badgeDownloadButton.classList.remove("hidden");
    el.badgeMarkdownButton.classList.remove("hidden");
    el.badgeUrlButton.classList.remove("hidden");
    status(el.badgeStatus, `Badge generated from health score ${badgeData.score}.`, "ok");
  } catch (err) {
    status(el.badgeStatus, err.message || "Badge generation failed.", "error");
  } finally {
    el.badgeButton.disabled = false;
  }
}

async function analyze() {
  const dockerfile = el.dockerfile.value;
  if (!dockerfile.trim()) {
    setStatus("Paste a Dockerfile first.", "error");
    el.dockerfile.focus();
    return;
  }
  if (dockerfile.length > MAX_DOCKERFILE_CHARS) {
    setStatus(`Dockerfile is too large (max ${MAX_DOCKERFILE_CHARS.toLocaleString()} characters).`, "error");
    return;
  }

  el.analyze.disabled = true;
  el.loading.classList.remove("hidden");
  el.btnLabel.textContent = "Analyzing";
  setStatus("Analyzing…", "busy");

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ANALYZE_TIMEOUT_MS);

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dockerfile,
        filename: "Dockerfile",
        has_dockerignore: el.dockerignore?.checked ?? false,
      }),
      signal: controller.signal,
    });

    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(extractError(payload, res));
    }

    renderReport(payload, dockerfile);
    setStatus("Analysis complete.", "ok");
  } catch (err) {
    if (err?.name === "AbortError") {
      setStatus("Analysis timed out. Try a smaller Dockerfile.", "error");
    } else {
      setStatus(err.message || "Analysis failed.", "error");
    }
  } finally {
    clearTimeout(timer);
    el.analyze.disabled = false;
    el.loading.classList.add("hidden");
    el.btnLabel.textContent = "Analyze";
  }
}

function loadSample() {
  el.dockerfile.value = SAMPLE;
  updateLineCount();
  setStatus("Sample loaded.");
  el.dockerfile.focus();
}

el.analyze.addEventListener("click", analyze);
el.tabs.forEach((tab) => tab.addEventListener("click", () => switchTool(tab.dataset.tool)));
el.dockerignore?.addEventListener("change", () => {
  if (!el.report.classList.contains("hidden") && el.dockerfile.value.trim()) {
    analyze();
  }
});
el.fixPreviewButton.addEventListener("click", () => buildFixPreview());
el.fixApplyButton.addEventListener("click", () => {
  const selected = [...el.fixOptions.querySelectorAll('input[type="checkbox"]:checked')].map((input) => input.value);
  buildFixPreview(selected);
});
el.fixDownloadButton.addEventListener("click", () => downloadText("Dockerfile.fixed", fixedDockerfile));
el.formatButton.addEventListener("click", formatCurrent);
el.formatDownloadButton.addEventListener("click", () => downloadText("Dockerfile.formatted", formattedDockerfile));
el.compareButton.addEventListener("click", compareCurrent);
el.badgeButton.addEventListener("click", generateBadge);
el.badgeDownloadButton.addEventListener("click", () => {
  if (badgeData) downloadText("dockrx-badge.svg", badgeData.svg, "image/svg+xml;charset=utf-8");
});
el.badgeMarkdownButton.addEventListener("click", (event) => {
  if (badgeData) copyText(event.currentTarget, badgeData.markdown);
});
el.badgeUrlButton.addEventListener("click", (event) => {
  if (badgeData) copyText(event.currentTarget, badgeData.url);
});
el.sample.addEventListener("click", loadSample);
el.emptyAnalyze.addEventListener("click", () => {
  loadSample();
  analyze();
});
el.clear.addEventListener("click", () => {
  el.dockerfile.value = "";
  updateLineCount();
  el.report.classList.add("hidden");
  el.empty.classList.remove("hidden");
  setStatus("Cleared.");
  el.dockerfile.focus();
});

el.dockerfile.addEventListener("input", updateLineCount);
el.dockerfile.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    analyze();
  }
});

if (!isMac() && el.btnKeys) {
  el.btnKeys.innerHTML = '<kbd class="kbd kbd-xs">Ctrl</kbd><kbd class="kbd kbd-xs">Enter</kbd>';
}

if (!el.dockerfile.value.trim()) {
  el.dockerfile.value = SAMPLE;
}
switchTool("check");
updateLineCount();
