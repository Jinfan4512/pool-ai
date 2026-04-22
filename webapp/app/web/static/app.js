const els = {
  banner: document.getElementById("banner"),
  boundary: document.getElementById("boundary"),
  inpool: document.getElementById("inpool"),
  alive: document.getElementById("alive"),
  stream: document.getElementById("stream"),
  lastevent: document.getElementById("lastevent"),
  lasttime: document.getElementById("lasttime"),
  token: document.getElementById("token"),
  btnOn: document.getElementById("btnOn"),
  btnOff: document.getElementById("btnOff"),
  liveArea: document.getElementById("liveArea"),
  liveImg: document.getElementById("liveImg"),
  btnDetectPool: document.getElementById("btnDetectPool"),
  btnSetBoundary: document.getElementById("btnSetBoundary"),
  btnClearBoundary: document.getElementById("btnClearBoundary"),
  boundaryStatus: document.getElementById("boundaryStatus"),
  warningBox: document.getElementById("warningBox"),
};

function showBanner(msg, level) {
  els.banner.classList.remove("hidden");
  els.banner.textContent = msg;

  if (level === "critical") els.banner.style.background = "#fee2e2";
  else if (level === "warning") els.banner.style.background = "#fef3c7";
  else els.banner.style.background = "#e0f2fe";
}

function hideBanner() {
  els.banner.classList.add("hidden");
}

function renderState(state) {
  if (!state) return;

  els.boundary.textContent = state.boundary_set ? "set" : "not set";
  els.inpool.textContent = state.in_pool ? "yes" : "no";
  els.alive.textContent = state.alive || "unknown";
  els.stream.textContent = state.stream_on ? "ON" : "OFF";

  els.lastevent.textContent = state.last_event || "-";
  els.lasttime.textContent = state.last_event_time || "-";

  if (state.in_pool) {
    els.warningBox.classList.remove("green");
    els.warningBox.classList.add("red");
  } else {
    els.warningBox.classList.remove("red");
    els.warningBox.classList.add("green");
  }

  if (state.alert_level === "warning") {
    showBanner(state.last_event || "Warning", "warning");
  } else if (state.alert_level === "critical") {
    showBanner(state.last_event || "Critical alert", "critical");
  } else {
    hideBanner();
  }
}

async function fetchStatus() {
  const r = await fetch("/api/status");
  const j = await r.json();

  // Support both shapes:
  // 1) direct object
  // 2) { state: {...} }
  renderState(j.state || j);
}

function connectWS() {
  const ws = new WebSocket(`ws://${location.host}/ws`);

  ws.onopen = () => {
    setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send("ping");
    }, 15000);
  };

  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.state) renderState(msg.state);
  };

  ws.onclose = () => {
    setTimeout(connectWS, 1000);
  };
}

let streamKey = null;

async function controlStream(on) {
  const token = (els.token.value || "").trim();
  if (!token) {
    alert("Please enter the control token first.");
    return;
  }

  if (!on) {
    streamKey = null;
    els.liveImg.src = "";
    els.liveImg.removeAttribute("src");
    els.liveArea.classList.add("hidden");
  }

  const url = on ? "/api/stream/on" : "/api/stream/off";

  const r = await fetch(url, {
    method: "POST",
    headers: { "X-Control-Token": token },
  });

  const j = await r.json().catch(() => ({}));

  if (!r.ok) {
    alert(`Control failed: ${r.status} ${j.detail || ""}`.trim());
    return;
  }

  if (on) {
    streamKey = j.stream_key;

    els.liveImg.src = "";
    els.liveImg.removeAttribute("src");
    els.liveArea.classList.remove("hidden");

    setTimeout(() => {
      els.liveImg.src = `/video/mjpeg?key=${encodeURIComponent(streamKey)}&t=${Date.now()}`;
    }, 100);
  }
}

async function sim(action) {
  if (action === "boundary") return fetch("/api/sim/boundary", { method: "POST" });
  if (action === "enter") return fetch("/api/sim/enter?kind=person", { method: "POST" });
  if (action === "alive") return fetch("/api/sim/alive?status=alive", { method: "POST" });
  if (action === "distress") return fetch("/api/sim/alive?status=distress", { method: "POST" });
  if (action === "exit") return fetch("/api/sim/exit", { method: "POST" });
}

document.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-sim]");
  if (!btn) return;
  sim(btn.dataset.sim).then(fetchStatus);
});

async function detectPoolBoundary() {
  const r = await fetch("/api/pool/detect", { method: "POST" });
  const j = await r.json().catch(() => ({}));

  if (!r.ok) {
    alert(`Pool detect failed: ${r.status} ${j.detail || ""}`.trim());
    return;
  }

  els.boundaryStatus.textContent = "detected (not confirmed)";
  await fetchStatus();
  await refreshPoolStatus();
}

async function confirmPoolBoundary() {
  const r = await fetch("/api/pool/confirm", { method: "POST" });
  const j = await r.json().catch(() => ({}));

  if (!r.ok) {
    alert(`Set Boundaries failed: ${r.status} ${j.detail || ""}`.trim());
    return;
  }

  els.boundaryStatus.textContent = "confirmed";
  await fetchStatus();
  await refreshPoolStatus();
}

async function clearPoolBoundary() {
  const r = await fetch("/api/pool/clear", { method: "POST" });
  const j = await r.json().catch(() => ({}));

  if (!r.ok) {
    alert(`Clear boundary failed: ${r.status} ${j.detail || ""}`.trim());
    return;
  }

  els.boundaryStatus.textContent = "not set";
  await fetchStatus();
  await refreshPoolStatus();
}

async function refreshPoolStatus() {
  const r = await fetch("/api/pool/status");
  const j = await r.json();

  if (j.boundary_set) {
    els.boundaryStatus.textContent = "confirmed";
  } else if (j.detected_polygon) {
    els.boundaryStatus.textContent = "detected (not confirmed)";
  } else {
    els.boundaryStatus.textContent = "not set";
  }
}

els.btnOn.addEventListener("click", () => controlStream(true));
els.btnOff.addEventListener("click", () => controlStream(false));
els.btnDetectPool.addEventListener("click", detectPoolBoundary);
els.btnSetBoundary.addEventListener("click", confirmPoolBoundary);
els.btnClearBoundary.addEventListener("click", clearPoolBoundary);

fetchStatus();
refreshPoolStatus();
connectWS();

setInterval(fetchStatus, 1000);
setInterval(refreshPoolStatus, 1000);