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
  els.boundary.textContent = state.pool_boundary_set ? "set" : "not set";
  els.inpool.textContent = state.object_in_pool ? "YES" : "no";
  els.alive.textContent = state.alive_status ?? "unknown";
  els.stream.textContent = state.streaming_enabled ? "ON" : "off";
  els.lastevent.textContent = state.last_event;
  els.lasttime.textContent = state.last_event_time;

  if (state.object_in_pool) {
    if (state.alert_level === "critical") {
      showBanner("CRITICAL: Possible drowning risk. View live feed now?", "critical");
    } else {
      showBanner("Alert: Object entered pool. View live feed?", "warning");
    }
  } else {
    if (state.streaming_enabled) {
      showBanner("Object exited pool. Disconnect live feed?", "info");
    } else {
      hideBanner();
    }
  }

  if (state.streaming_enabled) els.liveArea.classList.remove("hidden");
  else els.liveArea.classList.add("hidden");
}

async function fetchStatus() {
  const r = await fetch("/api/status");
  const j = await r.json();
  renderState(j.state);
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
    els.liveImg.src = `/video/mjpeg?key=${encodeURIComponent(streamKey)}&t=${Date.now()}`;
  } else {
    streamKey = null;
    els.liveImg.src = "";
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

els.btnOn.addEventListener("click", () => controlStream(true));
els.btnOff.addEventListener("click", () => controlStream(false));

fetchStatus();
connectWS();
