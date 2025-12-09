const ws = new WebSocket(`ws://${location.host}/ws`);

function setWsStatus(connected) {
  const pill = document.getElementById("ws_status");
  const text = document.getElementById("ws_status_text");
  const dot = pill.querySelector(".dot");

  if (connected) {
    text.textContent = "Connected";
    dot.classList.remove("dot-offline");
    dot.classList.add("dot-online");
  } else {
    text.textContent = "Disconnected";
    dot.classList.remove("dot-online");
    dot.classList.add("dot-offline");
  }
}

ws.onopen = () => {
  console.log("WS connected");
  setWsStatus(true);
};

ws.onclose = () => {
  console.log("WS closed");
  setWsStatus(false);
};

ws.onerror = (e) => {
  console.error("WS error", e);
  setWsStatus(false);
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data || "{}");
  document.getElementById("raw_json").innerText = JSON.stringify(data, null, 2);

  // Basic fields
  document.getElementById("symbol").innerText = data.symbol ?? "-";
  document.getElementById("price").innerText =
    data.price?.toFixed?.(2) ?? "-";
  document.getElementById("price_big").innerText =
    data.price?.toFixed?.(2) ?? "-";

  // AI
  const up = data.ai_prob_up;
  const down = data.ai_prob_down;
  const conf = data.ai_confidence;

  document.getElementById("ai_up_big").innerText = up
    ? (up * 100).toFixed(1) + "%"
    : "0%";
  document.getElementById("ai_down").innerText = down
    ? (down * 100).toFixed(2) + "%"
    : "-";
  document.getElementById("ai_conf").innerText = conf
    ? conf.toFixed(2)
    : "-";

  document.getElementById("ai_dir").innerText = data.ai_direction ?? "-";
  document.getElementById("ai_dir_small").innerText =
    data.ai_direction ?? "-";

  // Market indicators
  document.getElementById("rsi").innerText = data.rsi
    ? data.rsi.toFixed(2)
    : "-";
  document.getElementById("rsi_zone").innerText = data.rsi_zone ?? "-";
  document.getElementById("rsi_zone_small").innerText =
    data.rsi_zone ?? "-";

  document.getElementById("macd_hist").innerText = data.macd_hist
    ? data.macd_hist.toFixed(4)
    : "-";
  document.getElementById("atr").innerText = data.atr
    ? data.atr.toFixed(3)
    : "-";
  document.getElementById("adx").innerText = data.adx
    ? data.adx.toFixed(2)
    : "-";

  // Regime / Engine
  document.getElementById("regime").innerText = data.regime ?? "-";
  document.getElementById("regime_small").innerText = data.regime ?? "-";
  document.getElementById("use_lstm").innerText = data.use_lstm
    ? "LSTM + Rule-based"
    : "Rule-based";

  // Signals
  const preEl = document.getElementById("pre_signal");
  const confEl = document.getElementById("confirm_signal");

  const pre = !!data.pre_signal;
  const confirm = !!data.confirm_signal;

  preEl.textContent = pre ? "ACTIVE" : "IDLE";
  confEl.textContent = confirm ? "ACTIVE" : "IDLE";

  preEl.classList.toggle("signal-on", pre);
  preEl.classList.toggle("signal-off", !pre);
  confEl.classList.toggle("signal-on", confirm);
  confEl.classList.toggle("signal-off", !confirm);

  document.getElementById("pre_ts").innerText =
    data.pre_timestamp ? new Date(data.pre_timestamp).toLocaleString() : "-";
  document.getElementById("confirm_ts").innerText =
    data.confirm_timestamp ? new Date(data.confirm_timestamp).toLocaleString() : "-";

  // Loop time
  document.getElementById("loop_started").innerText =
    data.loop_started ? new Date(data.loop_started).toLocaleString() : "-";
};


// -------- ปุ่ม BUY / SELL / AUTO / TRAIN --------

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    console.error("Invalid JSON from", url, e);
  }
  if (!res.ok) {
    const msg = (data && data.error) || res.statusText;
    throw new Error(msg);
  }
  return data;
}

const tradeStatusEl = document.getElementById("trade_status");
const trainStatusEl = document.getElementById("train_status");

async function sendOrder(side) {
  try {
    tradeStatusEl.textContent = `Sending ${side}...`;
    const data = await postJSON("/api/order", { side });
    tradeStatusEl.textContent = `OK: ${data.side} ${data.volume} (${data.result?.retcode ?? "-"})`;
  } catch (e) {
    console.error(e);
    tradeStatusEl.textContent = `Error: ${e.message}`;
  }
}

async function triggerTrainAI() {
  try {
    trainStatusEl.textContent = "Training...";
    const data = await postJSON("/api/train_ai", {});
    trainStatusEl.textContent = data.message || "Training started";
  } catch (e) {
    console.error(e);
    trainStatusEl.textContent = `Error: ${e.message}`;
  }
}

document.getElementById("btn_buy").addEventListener("click", () => {
  sendOrder("BUY");
});

document.getElementById("btn_sell").addEventListener("click", () => {
  sendOrder("SELL");
});

document.getElementById("btn_auto_order").addEventListener("click", () => {
  sendOrder("AUTO");
});

document.getElementById("btn_train_ai").addEventListener("click", () => {
  triggerTrainAI();
});
