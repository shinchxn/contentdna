/* global chrome */

// ──────────────────────────────────────────────
// Utility helpers
// ──────────────────────────────────────────────

function setStatus(msg, type = "") {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = `status ${type}`;
}

function setLoading(msg) {
  setStatus(msg, "loading");
}

async function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(
      { apiUrl: "http://localhost:8000", ownerId: "demo-owner-id" },
      resolve
    );
  });
}

async function getCurrentTab() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      resolve(tabs[0] || null);
    });
  });
}

// ──────────────────────────────────────────────
// Init — load settings and display current page
// ──────────────────────────────────────────────

(async () => {
  const { apiUrl, ownerId } = await getSettings();
  document.getElementById("apiUrl").value = apiUrl;
  document.getElementById("ownerId").value = ownerId;

  const tab = await getCurrentTab();
  if (tab?.url) {
    const display = tab.url.length > 55 ? tab.url.substring(0, 55) + "…" : tab.url;
    document.getElementById("currentPage").textContent = display;
  }
})();

// ──────────────────────────────────────────────
// Settings
// ──────────────────────────────────────────────

document.getElementById("settingsToggle").addEventListener("click", () => {
  const panel = document.getElementById("settingsPanel");
  const isHidden = panel.style.display === "none";
  panel.style.display = isHidden ? "block" : "none";
  document.getElementById("settingsToggle").textContent =
    isHidden ? "⚙ Hide Settings" : "⚙ Settings";
});

document.getElementById("saveSettings").addEventListener("click", () => {
  const apiUrl  = document.getElementById("apiUrl").value.trim();
  const ownerId = document.getElementById("ownerId").value.trim();
  if (!apiUrl) return setStatus("API URL cannot be empty.", "error");
  chrome.storage.sync.set({ apiUrl, ownerId }, () => {
    setStatus("Settings saved ✓", "success");
  });
});

// ──────────────────────────────────────────────
// Shared POST helper
// ──────────────────────────────────────────────

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ──────────────────────────────────────────────
// Scan This Page → POST /hunt depth=2
// ──────────────────────────────────────────────

document.getElementById("scanPage").addEventListener("click", async () => {
  const tab = await getCurrentTab();
  if (!tab?.url || tab.url.startsWith("chrome://")) {
    return setStatus("Cannot scan browser internal pages.", "error");
  }
  const { apiUrl, ownerId } = await getSettings();
  setLoading("Starting page scan…");
  try {
    const data = await postJSON(`${apiUrl}/hunt`, {
      url:       tab.url,
      owner_id:  ownerId || "demo-owner-id",
      max_depth: 2,
      max_pages: 50,
    });
    setStatus(
      `Scan started ✓  Job ID: ${(data.job_id || "").substring(0, 12)}…`,
      "success"
    );
  } catch (e) {
    setStatus(`Error: ${e.message}`, "error");
  }
});

// ──────────────────────────────────────────────
// Deep Scan Domain → POST /hunt depth=3, domain root
// ──────────────────────────────────────────────

document.getElementById("deepScan").addEventListener("click", async () => {
  const tab = await getCurrentTab();
  if (!tab?.url || tab.url.startsWith("chrome://")) {
    return setStatus("Cannot scan browser internal pages.", "error");
  }
  const { apiUrl, ownerId } = await getSettings();
  let domain;
  try {
    domain = new URL(tab.url).origin;
  } catch {
    return setStatus("Invalid page URL.", "error");
  }
  setLoading(`Deep scanning ${domain}…`);
  try {
    const data = await postJSON(`${apiUrl}/hunt`, {
      url:       domain,
      owner_id:  ownerId || "demo-owner-id",
      max_depth: 3,
      max_pages: 100,
    });
    setStatus(
      `Deep scan started ✓  Job: ${(data.job_id || "").substring(0, 12)}…`,
      "success"
    );
  } catch (e) {
    setStatus(`Error: ${e.message}`, "error");
  }
});

// ──────────────────────────────────────────────
// Scan Specific URL → POST /check-url
// ──────────────────────────────────────────────

document.getElementById("scanUrl").addEventListener("click", async () => {
  const urlVal = document.getElementById("urlInput").value.trim();
  if (!urlVal) return setStatus("Please enter a URL to scan.", "error");
  const { apiUrl } = await getSettings();
  setLoading("Scanning URL…");
  try {
    const data = await postJSON(`${apiUrl}/check-url`, {
      url:      urlVal,
      platform: "web",
    });
    if (data.matched) {
      const score    = data.matches?.[0]?.score ?? 0;
      const severity = data.matches?.[0]?.severity ?? "UNKNOWN";
      const pct      = Math.round(score * 100);
      setStatus(
        `⚠️ VIOLATION FOUND  Score: ${pct}%  Severity: ${severity}  (${data.matches.length} match${data.matches.length !== 1 ? "es" : ""})`,
        "error"
      );
    } else {
      setStatus("✅ No violations found — content is clear.", "success");
    }
  } catch (e) {
    setStatus(`Error: ${e.message}`, "error");
  }
});
