"use strict";

const API_BASE = "http://127.0.0.1:8000";
const MAX_UPLOAD_BYTES = 2 * 1024 * 1024;
const MAX_DIFF_TOKENS = 850;

const elements = {
  apiStatus: document.getElementById("apiStatus"),
  apiStatusText: document.getElementById("apiStatusText"),
  refreshHealth: document.getElementById("refreshHealth"),
  refreshHistory: document.getElementById("refreshHistory"),
  originalText: document.getElementById("originalText"),
  wordCount: document.getElementById("wordCount"),
  outputContent: document.getElementById("outputContent"),
  outputWordCount: document.getElementById("outputWordCount"),
  copyButton: document.getElementById("copyButton"),
  clearButton: document.getElementById("clearButton"),
  sampleButton: document.getElementById("sampleButton"),
  fileInput: document.getElementById("fileInput"),
  rewriteButton: document.getElementById("rewriteButton"),
  processState: document.getElementById("processState"),
  processMessage: document.getElementById("processMessage"),
  metricsState: document.getElementById("metricsState"),
  metricsContent: document.getElementById("metricsContent"),
  modeList: document.getElementById("modeList"),
  selectedModeLabel: document.getElementById("selectedModeLabel"),
  historyList: document.getElementById("historyList"),
  historyPrev: document.getElementById("historyPrev"),
  historyNext: document.getElementById("historyNext"),
  historyPosition: document.getElementById("historyPosition"),
  toastRegion: document.getElementById("toastRegion")
};

const modeNames = {
  improve: "Improve writing",
  professional: "Professional",
  academic: "Academic",
  concise: "Make concise",
  expand: "Expand",
  simplify: "Simplify",
  creative: "Creative",
  persuasive: "Persuasive"
};

const sampleText = "Clear communication helps people understand ideas and take action. When writing is thoughtful and well structured, it is easier for readers to stay engaged and remember what matters.";
let selectedMode = "improve";
let activeOutput = "";
let historyItems = [];
let historyIndex = -1;
let requestInProgress = false;
let toastTimer;

function wordCount(text) {
  const matches = text.trim().match(/[\p{L}\p{N}]+(?:['’][\p{L}\p{N}]+)*/gu);
  return matches ? matches.length : 0;
}

function updateWordCount() {
  const count = wordCount(elements.originalText.value);
  elements.wordCount.textContent = `${count} ${count === 1 ? "word" : "words"}`;
}

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, character => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[character]);
}

function setProcessState(state, message) {
  elements.processState.classList.remove("is-working", "is-success", "is-error");
  if (state) elements.processState.classList.add(`is-${state}`);
  elements.processMessage.textContent = message;
}

function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast${type === "error" ? " is-error" : type === "success" ? " is-success" : ""}`;
  toast.textContent = message;
  elements.toastRegion.replaceChildren(toast);
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.remove(), 4800);
}

function isCorsOrNetworkError(error) {
  return error instanceof TypeError || /failed to fetch|networkerror|load failed/i.test(error.message || "");
}

function apiFailureMessage(error, path) {
  if (isCorsOrNetworkError(error)) {
    return `Could not reach ${API_BASE}${path}. Check that your FastAPI server is running and allows this frontend origin in its CORS settings (for example, http://127.0.0.1:5500).`;
  }
  return error.message || `The API request to ${path} failed.`;
}

async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers
      }
    });
  } catch (error) {
    throw new Error(apiFailureMessage(error, path), { cause: error });
  }

  const responseText = await response.text();
  let data = null;
  if (responseText) {
    try {
      data = JSON.parse(responseText);
    } catch {
      if (response.ok) throw new Error(`The API returned an unreadable response from ${path}.`);
    }
  }
  if (!response.ok) {
    const detail = data && (data.detail || data.message || data.error);
    throw new Error(detail ? String(detail) : `The API returned HTTP ${response.status} for ${path}.`);
  }
  return data;
}

function setApiStatus(online, message) {
  elements.apiStatus.classList.toggle("is-online", online);
  elements.apiStatus.classList.toggle("is-offline", !online);
  elements.apiStatusText.textContent = message;
}

async function checkHealth() {
  elements.apiStatus.classList.remove("is-online", "is-offline");
  elements.apiStatusText.textContent = "Checking API…";
  try {
    await apiRequest("/health");
    setApiStatus(true, "API connected");
  } catch (error) {
    setApiStatus(false, "API unavailable");
    console.warn("API health check failed:", error);
    showToast(apiFailureMessage(error, "/health"), "error");
  }
}

function tokenizeForDiff(text) {
  return text.match(/\s+|[\p{L}\p{N}_]+(?:['’][\p{L}\p{N}_]+)*|[^\s]/gu) || [];
}

function renderDiff(original, rewritten) {
  const left = tokenizeForDiff(original);
  const right = tokenizeForDiff(rewritten);
  if (left.length > MAX_DIFF_TOKENS || right.length > MAX_DIFF_TOKENS) {
    return {
      html: escapeHtml(rewritten),
      highlighted: false
    };
  }

  const rows = left.length + 1;
  const columns = right.length + 1;
  const table = Array.from({ length: rows }, () => new Uint16Array(columns));
  for (let i = left.length - 1; i >= 0; i--) {
    for (let j = right.length - 1; j >= 0; j--) {
      table[i][j] = left[i] === right[j]
        ? table[i + 1][j + 1] + 1
        : Math.max(table[i + 1][j], table[i][j + 1]);
    }
  }

  const pieces = [];
  let i = 0;
  let j = 0;
  while (j < right.length) {
    if (i < left.length && left[i] === right[j]) {
      pieces.push(escapeHtml(right[j]));
      i++;
      j++;
    } else if (j < right.length && (i === left.length || table[i][j + 1] >= table[i + 1][j])) {
      pieces.push(`<span class="diff-added">${escapeHtml(right[j])}</span>`);
      j++;
    } else {
      i++;
    }
  }
  return { html: pieces.join(""), highlighted: true };
}

function displayOutput(original, rewritten) {
  activeOutput = rewritten;
  if (!rewritten) {
    elements.outputContent.innerHTML = '<div class="empty-output"><span class="empty-icon" aria-hidden="true">✧</span><p>Your refined text will appear here.</p><span>Choose a mode and let your words find their way.</span></div>';
    elements.copyButton.disabled = true;
    elements.outputWordCount.textContent = "—";
    return;
  }
  const result = renderDiff(original, rewritten);
  elements.outputContent.innerHTML = result.html;
  elements.copyButton.disabled = false;
  elements.outputWordCount.textContent = `${wordCount(rewritten)} words`;
  if (!result.highlighted) {
    showToast("Text is displayed without word highlighting because it is too long for the comparison view.");
  }
}

function unwrapResponse(value) {
  if (typeof value === "string") return value;
  if (!value || typeof value !== "object") return "";
  const keys = ["rewritten_text", "enhanced_text", "rewritten", "enhanced", "output", "result", "text"];
  for (const key of keys) {
    if (typeof value[key] === "string") return value[key];
  }
  for (const key of ["data", "response"]) {
    if (value[key] && typeof value[key] === "object") {
      const nested = unwrapResponse(value[key]);
      if (nested) return nested;
    }
  }
  return "";
}

function flattenMetrics(value, prefix = "", depth = 0) {
  if (!value || typeof value !== "object" || depth > 3) return [];
  const result = [];
  for (const [key, item] of Object.entries(value)) {
    const label = prefix ? `${prefix} ${key}` : key;
    if (typeof item === "number" && Number.isFinite(item)) {
      result.push([label, item]);
    } else if (typeof item === "string" && item.trim() && item.length < 36 && !/^(true|false)$/i.test(item)) {
      result.push([label, item]);
    } else if (item && typeof item === "object" && !Array.isArray(item)) {
      result.push(...flattenMetrics(item, label, depth + 1));
    }
  }
  return result;
}

function formatMetricLabel(label) {
  return label
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, character => character.toUpperCase());
}

function showMetrics(data) {
  const source = data && typeof data === "object" && (data.metrics || data.scores || data.evaluation || data.data)
    ? (data.metrics || data.scores || data.evaluation || data.data)
    : data;
  const metrics = flattenMetrics(source).slice(0, 8);
  elements.metricsContent.replaceChildren();
  if (!metrics.length) {
    const empty = document.createElement("p");
    empty.className = "metrics-empty";
    empty.textContent = "The evaluation API returned no displayable metrics.";
    elements.metricsContent.append(empty);
    elements.metricsState.textContent = "No metrics returned";
    return;
  }
  for (const [label, value] of metrics) {
    const card = document.createElement("div");
    card.className = "metric-card";
    const score = document.createElement("strong");
    score.textContent = typeof value === "number" ? `${Number.isInteger(value) ? value : Number(value.toFixed(2))}` : value;
    const caption = document.createElement("span");
    caption.textContent = formatMetricLabel(label);
    card.append(score, caption);
    elements.metricsContent.append(card);
  }
  elements.metricsState.textContent = `${metrics.length} metric${metrics.length === 1 ? "" : "s"} from API`;
}

function resetMetrics(message = "Waiting for a rewrite") {
  elements.metricsContent.replaceChildren();
  const empty = document.createElement("p");
  empty.className = "metrics-empty";
  empty.textContent = "Evaluation metrics from your API will show up here after a rewrite.";
  elements.metricsContent.append(empty);
  elements.metricsState.textContent = message;
}

function parseHistory(data) {
  const source = Array.isArray(data)
    ? data
    : data && (data.history || data.items || data.results || data.data);
  if (Array.isArray(source)) return source;
  return [];
}

function historyText(item, keys) {
  for (const key of keys) {
    if (typeof item[key] === "string") return item[key];
  }
  return "";
}

function renderHistory() {
  elements.historyList.replaceChildren();
  if (!historyItems.length) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.textContent = "No rewrite history returned by the API.";
    elements.historyList.append(empty);
  } else {
    historyItems.forEach((item, index) => {
      const original = historyText(item, ["original_text", "input_text", "original", "input", "prompt"]);
      const rewritten = historyText(item, ["rewritten_text", "enhanced_text", "rewritten", "enhanced", "output", "result"]);
      const button = document.createElement("button");
      button.type = "button";
      button.className = `history-item${index === historyIndex ? " is-active" : ""}`;
      const title = document.createElement("strong");
      title.textContent = original || rewritten || `History item ${index + 1}`;
      const detail = document.createElement("small");
      const mode = item.mode ? String(item.mode) : "Rewrite";
      const date = item.created_at || item.timestamp || item.date;
      detail.textContent = `${formatMetricLabel(mode)}${date ? ` · ${String(date)}` : ""}`;
      button.append(title, detail);
      button.addEventListener("click", () => loadHistoryItem(index));
      elements.historyList.append(button);
    });
  }
  const position = historyIndex >= 0 ? historyIndex + 1 : 0;
  elements.historyPosition.textContent = `${position} / ${historyItems.length}`;
  elements.historyPrev.disabled = !historyItems.length || historyIndex <= 0;
  elements.historyNext.disabled = !historyItems.length || historyIndex < 0 || historyIndex >= historyItems.length - 1;
}

function loadHistoryItem(index) {
  const item = historyItems[index];
  if (!item) return;
  const original = historyText(item, ["original_text", "input_text", "original", "input", "prompt"]);
  const rewritten = historyText(item, ["rewritten_text", "enhanced_text", "rewritten", "enhanced", "output", "result"]);
  if (!original || !rewritten) {
    showToast("This history entry does not include both the original and rewritten text.", "error");
    return;
  }
  elements.originalText.value = original;
  updateWordCount();
  displayOutput(original, rewritten);
  resetMetrics("History item loaded");
  historyIndex = index;
  if (typeof item.mode === "string") selectMode(item.mode);
  renderHistory();
  setProcessState("success", "Loaded from API history");
}

async function loadHistory() {
  elements.refreshHistory.disabled = true;
  try {
    const data = await apiRequest("/api/history");
    historyItems = parseHistory(data);
    historyIndex = -1;
    renderHistory();
  } catch (error) {
    historyItems = [];
    historyIndex = -1;
    renderHistory();
    console.warn("History request failed:", error);
    showToast(apiFailureMessage(error, "/api/history"), "error");
  } finally {
    elements.refreshHistory.disabled = false;
  }
}

function selectMode(mode) {
  const normalized = String(mode || "").toLowerCase().replace(/[\s-]+/g, "_");
  const found = Object.keys(modeNames).find(key => key === normalized || modeNames[key].toLowerCase().replace(/[\s-]+/g, "_") === normalized);
  if (!found) return;
  selectedMode = found;
  for (const button of elements.modeList.querySelectorAll(".mode-option")) {
    const selected = button.dataset.mode === selectedMode;
    button.classList.toggle("is-selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  }
  elements.selectedModeLabel.textContent = modeNames[selectedMode];
}

async function rewriteText() {
  const original = elements.originalText.value.trim();
  if (!original) {
    showToast("Add or upload some text before asking for a rewrite.", "error");
    elements.originalText.focus();
    return;
  }
  if (requestInProgress) return;

  requestInProgress = true;
  elements.rewriteButton.disabled = true;
  elements.rewriteButton.querySelector(".rewrite-button-content span").textContent = "Working…";
  elements.metricsState.textContent = "Waiting for evaluation";
  setProcessState("working", "Sending text to your rewrite API…");
  try {
    const data = await apiRequest("/api/rewrite", {
      method: "POST",
      body: JSON.stringify({ text: original, mode: selectedMode })
    });
    const rewritten = unwrapResponse(data);
    if (!rewritten.trim()) {
      throw new Error("The rewrite API responded successfully but did not include rewritten text.");
    }
    displayOutput(original, rewritten);
    setProcessState("working", "Rewrite received · evaluating quality…");
    elements.metricsState.textContent = "Evaluating with API…";

    try {
      const evaluation = await apiRequest("/api/evaluate", {
        method: "POST",
        body: JSON.stringify({ original_text: original, rewritten_text: rewritten })
      });
      showMetrics(evaluation);
      setProcessState("success", "Rewrite and evaluation complete");
    } catch (error) {
      resetMetrics("Evaluation unavailable");
      elements.metricsState.textContent = "Evaluation request failed";
      setProcessState("error", "Rewrite received · evaluation failed");
      showToast(`Your rewrite was received, but evaluation failed: ${apiFailureMessage(error, "/api/evaluate")}`, "error");
    }
    historyIndex = -1;
    renderHistory();
  } catch (error) {
    setProcessState("error", "Rewrite failed");
    elements.metricsState.textContent = "No evaluation available";
    console.error("Rewrite request failed:", error);
    showToast(apiFailureMessage(error, "/api/rewrite"), "error");
  } finally {
    requestInProgress = false;
    elements.rewriteButton.disabled = false;
    elements.rewriteButton.querySelector(".rewrite-button-content span").textContent = "Enhance my writing";
  }
}

function clearAll() {
  if (requestInProgress) return;
  elements.originalText.value = "";
  updateWordCount();
  displayOutput("", "");
  resetMetrics();
  setProcessState("", "Ready when you are");
  elements.fileInput.value = "";
  historyIndex = -1;
  renderHistory();
  elements.originalText.focus();
}

async function copyOutput() {
  if (!activeOutput) return;
  try {
    await navigator.clipboard.writeText(activeOutput);
    showToast("Enhanced text copied to clipboard.", "success");
  } catch (error) {
    console.warn("Clipboard write failed:", error);
    showToast("Could not access the clipboard. Select and copy the enhanced text instead.", "error");
  }
}

async function uploadTextFile(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".txt") && file.type !== "text/plain") {
    showToast("Please choose a plain .txt file.", "error");
    event.target.value = "";
    return;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    showToast("That file is over the 2 MB upload limit.", "error");
    event.target.value = "";
    return;
  }
  try {
    elements.originalText.value = await file.text();
    updateWordCount();
    elements.originalText.focus();
    showToast(`Loaded ${file.name}.`, "success");
  } catch (error) {
    console.error("Text file could not be read:", error);
    showToast(`Could not read ${file.name}. Please try another .txt file.`, "error");
  } finally {
    event.target.value = "";
  }
}

elements.originalText.addEventListener("input", updateWordCount);
elements.modeList.addEventListener("click", event => {
  const button = event.target.closest(".mode-option");
  if (button) selectMode(button.dataset.mode);
});
elements.rewriteButton.addEventListener("click", rewriteText);
elements.clearButton.addEventListener("click", clearAll);
elements.sampleButton.addEventListener("click", () => {
  if (requestInProgress) return;
  elements.originalText.value = sampleText;
  updateWordCount();
  elements.originalText.focus();
  setProcessState("", "Sample text added · ready to rewrite");
});
elements.copyButton.addEventListener("click", copyOutput);
elements.fileInput.addEventListener("change", uploadTextFile);
elements.refreshHealth.addEventListener("click", checkHealth);
elements.refreshHistory.addEventListener("click", loadHistory);
elements.historyPrev.addEventListener("click", () => {
  if (historyIndex > 0) loadHistoryItem(historyIndex - 1);
});
elements.historyNext.addEventListener("click", () => {
  if (historyIndex >= 0 && historyIndex < historyItems.length - 1) loadHistoryItem(historyIndex + 1);
});
document.addEventListener("keydown", event => {
  if (event.ctrlKey && event.key === "Enter") {
    event.preventDefault();
    rewriteText();
  }
});

updateWordCount();
renderHistory();
checkHealth();
loadHistory();
