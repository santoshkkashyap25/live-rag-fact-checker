// popup.js - FactGuard Chrome Extension Controller

document.addEventListener("DOMContentLoaded", async () => {
  const claimInput = document.getElementById("claimInput");
  const serverSelect = document.getElementById("serverSelect");
  const serverLabel = document.getElementById("serverLabel");
  const verifyBtn = document.getElementById("verifyBtn");
  const btnText = document.getElementById("btnText");
  const loadingState = document.getElementById("loadingState");
  const errorState = document.getElementById("errorState");
  const errorMsg = document.getElementById("errorMsg");
  const resultCard = document.getElementById("resultCard");
  const verdictBadge = document.getElementById("verdictBadge");
  const confValue = document.getElementById("confValue");
  const reasoningText = document.getElementById("reasoningText");
  const evidenceCount = document.getElementById("evidenceCount");
  const evidenceList = document.getElementById("evidenceList");

  // Load saved server preference or pending selection
  chrome.storage.local.get(["pendingClaim", "savedServer"], (data) => {
    if (data.pendingClaim) {
      claimInput.value = data.pendingClaim;
      chrome.storage.local.remove("pendingClaim");
      // Auto-trigger verification if launched with selected text
      triggerVerify();
    }
    if (data.savedServer) {
      serverSelect.value = data.savedServer;
      updateServerLabel(data.savedServer);
    }
  });

  serverSelect.addEventListener("change", (e) => {
    const val = e.target.value;
    chrome.storage.local.set({ savedServer: val });
    updateServerLabel(val);
  });

  function updateServerLabel(url) {
    serverLabel.textContent = url.includes("localhost") ? "Local" : "Cloud";
  }

  verifyBtn.addEventListener("click", () => {
    triggerVerify();
  });

  async function triggerVerify() {
    const text = claimInput.value.trim();
    if (!text) {
      showError("Please enter or highlight a statement to verify.");
      return;
    }

    const apiUrl = serverSelect.value.replace(/\/$/, "");

    // Reset UI
    errorState.classList.add("hidden");
    resultCard.classList.add("hidden");
    loadingState.classList.remove("hidden");
    verifyBtn.disabled = true;
    btnText.textContent = "Verifying...";

    try {
      const res = await fetch(`${apiUrl}/api/verify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          text: text,
          user_id: "chrome_extension_user"
        })
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      displayResult(data);
    } catch (err) {
      showError(err.message || "Failed to reach FactGuard server.");
    } finally {
      loadingState.classList.add("hidden");
      verifyBtn.disabled = false;
      btnText.textContent = "Verify Claim";
    }
  }

  function displayResult(data) {
    const verdict = data.verdict || "Unverifiable";
    verdictBadge.textContent = verdict.toUpperCase();
    verdictBadge.className = `verdict-badge verdict-${verdict.toLowerCase()}`;

    const confNum = parseFloat(data.confidence) || 0.9;
    confValue.textContent = `${Math.round(confNum <= 1.0 ? confNum * 100 : confNum)}%`;

    reasoningText.textContent = data.reasoning || "Evidence evaluated against claim.";

    const items = data.evidence || [];
    const urls = data.evidence_urls || [];
    const sources = data.evidence_sources || [];
    evidenceCount.textContent = items.length;
    evidenceList.innerHTML = "";

    items.forEach((text, i) => {
      const src = sources[i] || "Source";
      const url = urls[i] || "";
      const div = document.createElement("div");
      div.className = "evidence-item";
      div.innerHTML = `<strong>[${escapeHtml(src)}]</strong> ${escapeHtml(text.slice(0, 110))}... ${
        url ? `<a href="${encodeURI(url)}" target="_blank">&#x2197;</a>` : ""
      }`;
      evidenceList.appendChild(div);
    });

    resultCard.classList.remove("hidden");
  }

  function showError(msg) {
    errorMsg.textContent = msg;
    errorState.classList.remove("hidden");
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }
});
