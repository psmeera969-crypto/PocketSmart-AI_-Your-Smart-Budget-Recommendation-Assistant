/**
 * PocketSmart AI - shared frontend logic.
 * Each planner page calls PocketSmart.submitPlanner(url, body, isFormData)
 * on submit; this module posts the request, shows loading/error state,
 * and renders the returned RecommendationResponse as result cards.
 */
window.PocketSmart = (function () {
  function setStatus(message, type) {
    const el = document.getElementById("status");
    if (!el) return;
    el.textContent = message || "";
    el.className = "status" + (type ? " " + type : "");
  }

  function clearResults() {
    const el = document.getElementById("results");
    if (el) el.innerHTML = "";
  }

  function renderResults(data) {
    const el = document.getElementById("results");
    if (!el) return;

    const summary = document.createElement("div");
    summary.className = "result-summary";
    summary.innerHTML = `
      <strong>${data.planner_type.charAt(0).toUpperCase() + data.planner_type.slice(1)} plan ready.</strong>
      ${data.summary}
      <br/><span class="muted">Engine: ${data.source === "gemini" ? "Gemini AI" : "Fallback (mock mode)"}</span>
    `;
    el.appendChild(summary);

    data.items.forEach((item) => {
      const card = document.createElement("article");
      card.className = "result-card";
      card.innerHTML = `
        <h3>${item.item_name}</h3>
        <p class="muted">${item.category} &middot; ${item.platform}</p>
        <p>${item.description}</p>
        <p class="price">${item.estimated_price} ${item.currency}</p>
        <a href="${item.search_link}" target="_blank" rel="noopener">View on ${item.platform} →</a>
      `;
      el.appendChild(card);
    });
  }

  async function submitPlanner(url, body, isFormData) {
    clearResults();
    setStatus("Generating your recommendations with Gemini...", "loading");
    try {
      const options = { method: "POST", credentials: "same-origin" };
      if (isFormData) {
        options.body = body;
      } else {
        options.headers = { "Content-Type": "application/json" };
        options.body = JSON.stringify(body);
      }
      const res = await fetch(url, options);

      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const detail =
          typeof errData.detail === "string"
            ? errData.detail
            : JSON.stringify(errData.detail || "Request failed.");
        setStatus(`Error: ${detail}`, "error");
        return;
      }

      const data = await res.json();
      setStatus("");
      renderResults(data);
    } catch (err) {
      setStatus("Network error - please check your connection and try again.", "error");
      console.error(err);
    }
  }

  return { submitPlanner };
})();
