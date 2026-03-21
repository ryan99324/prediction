const state = {
  markets: [],
  accounts: [],
  trades: [],
  decisions: [],
  trader_metrics: [],
  summary: null,
  aliases: {},
};

const palette = ["#0e7a62", "#155f90", "#d06b2f", "#8d4ab4", "#b03e6d"];

const els = {
  decisionCount: document.getElementById("decisionCount"),
  recommendedCount: document.getElementById("recommendedCount"),
  portfolioEv: document.getElementById("portfolioEv"),
  decisions: document.getElementById("decisions"),
  markets: document.getElementById("markets"),
  accounts: document.getElementById("accounts"),
  tradesBody: document.getElementById("tradesBody"),
  incentivesBody: document.getElementById("incentivesBody"),
  mathBody: document.getElementById("mathBody"),
  simControlForm: document.getElementById("simControlForm"),
  simDecision: document.getElementById("simDecision"),
  simRemainingSeconds: document.getElementById("simRemainingSeconds"),
  setWindowBtn: document.getElementById("setWindowBtn"),
  simRounds: document.getElementById("simRounds"),
  simulateBtn: document.getElementById("simulateBtn"),
  tradeForm: document.getElementById("tradeForm"),
  tradeDecision: document.getElementById("tradeDecision"),
  tradeOption: document.getElementById("tradeOption"),
  tradeTrader: document.getElementById("tradeTrader"),
  tradeSide: document.getElementById("tradeSide"),
  tradeShares: document.getElementById("tradeShares"),
  resolveForm: document.getElementById("resolveForm"),
  resolveDecision: document.getElementById("resolveDecision"),
  resolveOption: document.getElementById("resolveOption"),
  createDecisionForm: document.getElementById("createDecisionForm"),
  newDecisionId: document.getElementById("newDecisionId"),
  newDecisionTitle: document.getElementById("newDecisionTitle"),
  newDecisionDescription: document.getElementById("newDecisionDescription"),
  newDecisionUseCase: document.getElementById("newDecisionUseCase"),
  newDecisionLiquidity: document.getElementById("newDecisionLiquidity"),
  newDecisionFeeBps: document.getElementById("newDecisionFeeBps"),
  newDecisionOptions: document.getElementById("newDecisionOptions"),
  fundTraderForm: document.getElementById("fundTraderForm"),
  fundTraderId: document.getElementById("fundTraderId"),
  fundTraderTokens: document.getElementById("fundTraderTokens"),
  resetBtn: document.getElementById("resetBtn"),
  status: document.getElementById("status"),
  menuSelect: document.getElementById("menuSelect"),
};
const tabButtons = Array.from(document.querySelectorAll(".tab-btn[data-tab]"));
const tabPanels = Array.from(document.querySelectorAll(".tab-panel"));

function setStatus(message, isError = false) {
  els.status.textContent = message;
  els.status.style.color = isError ? "#fb7185" : "#c6d3ef";
}

function fmtPct(v) {
  return `${(v * 100).toFixed(1)}%`;
}

function fmtMoney(v) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);
}

function fmtCost(v) {
  return Number(v).toFixed(6);
}

function fmtProbabilities(before, after) {
  const keys = Object.keys(before || {});
  return keys.map((k) => `${k}: ${fmtPct(before[k])} -> ${fmtPct(after[k])}`).join(" | ");
}

function fmtSecs(secs) {
  const s = Math.max(0, Math.floor(secs || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  return `${h}:${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

function aliasOf(traderId) {
  if (!traderId) return "anon";
  if (!state.aliases[traderId]) {
    const next = Object.keys(state.aliases).length + 1;
    state.aliases[traderId] = `anon_${String(next).padStart(2, "0")}`;
  }
  return state.aliases[traderId];
}

function setTab(tabName) {
  tabPanels.forEach((p) => p.classList.toggle("active", p.id === `tab-${tabName}`));
  tabButtons.forEach((b) => b.classList.toggle("active", b.dataset.tab === tabName));
  if (els.menuSelect) {
    els.menuSelect.value = tabName;
  }
}

function getDecisionById(decisionId) {
  return state.decisions.find((d) => d.decision_id === decisionId);
}

function fillDecisionSelectors() {
  const open = state.decisions.filter((d) => d.state === "OPEN");
  const decisionOptions = open.map((d) => `<option value="${d.decision_id}">${d.decision_id} - ${d.title}</option>`).join("");

  els.tradeDecision.innerHTML = decisionOptions;
  els.resolveDecision.innerHTML = decisionOptions;
  els.simDecision.innerHTML = decisionOptions;

  els.tradeTrader.innerHTML = state.accounts.map((a) => `<option value="${a.trader_id}">${aliasOf(a.trader_id)}</option>`).join("");

  syncTradeOptionSelector();
  syncResolveOptionSelector();
}

function syncTradeOptionSelector() {
  const d = getDecisionById(els.tradeDecision.value);
  const opts = d ? d.options : [];
  els.tradeOption.innerHTML = opts.map((o) => `<option value="${o.option_id}">${o.option_id} - ${o.label}</option>`).join("");
}

function syncResolveOptionSelector() {
  const d = getDecisionById(els.resolveDecision.value);
  const opts = d ? d.options : [];
  els.resolveOption.innerHTML = opts.map((o) => `<option value="${o.option_id}">${o.option_id} - ${o.label}</option>`).join("");
}

function renderSummary() {
  if (!state.summary) {
    els.decisionCount.textContent = "-";
    els.recommendedCount.textContent = "-";
    els.portfolioEv.textContent = "-";
    return;
  }
  els.decisionCount.textContent = String(state.summary.decision_count);
  els.recommendedCount.textContent = `${state.summary.recommended_count} (Escalate ${state.summary.escalated_count})`;
  els.portfolioEv.textContent = fmtMoney(state.summary.portfolio_expected_value);
}

function renderDecisions() {
  els.decisions.innerHTML = state.decisions
    .map((d) => {
      const recommendation = d.recommended_option_id || "NONE";
      const rationale = (d.rationale || []).join("; ");
      const optionsRows = d.options
        .map((o) => {
          const reason = o.fail_reasons.length ? o.fail_reasons.join(", ") : "-";
          return `
            <tr>
              <td>${o.option_id}</td>
              <td>${fmtPct(o.p_success)}</td>
              <td>${fmtPct(o.p_twap)}</td>
              <td>${fmtMoney(o.expected_value)}</td>
              <td>${fmtPct(o.confidence)}</td>
              <td>${fmtMoney(o.downside)}</td>
              <td class="${o.passes_rule ? "pass" : "fail"}">${o.passes_rule ? "PASS" : "FAIL"}</td>
              <td>${reason}</td>
            </tr>
          `;
        })
        .join("");

      return `
        <article class="decision-card">
          <div class="row-top">
            <div>
              <strong>${d.title}</strong>
              <div class="sub">${d.description}</div>
            </div>
            <span class="badge ${d.status}">${d.status}</span>
          </div>
          <div class="reco">Decision ${d.decision_id} | Recommendation: <strong>${recommendation}</strong> | ${rationale}</div>
          <div class="rule">Use Case: ${d.use_case}</div>
          <div class="rule">Linked branch market check: probability sum = ${d.probability_sum.toFixed(4)} (target 1.0000)</div>
          <div class="rule">Window status: ${d.state} | Time remaining: ${fmtSecs(d.seconds_remaining)}</div>
          <div class="rule">Close rule: highest TWAP branch wins (spot only breaks ties). Non-winning branch trades are reverted.</div>
          <div class="rule">
            Policy: EV >= ${fmtMoney(d.rule.min_expected_value)}, P >= ${fmtPct(d.rule.min_probability)},
            confidence >= ${fmtPct(d.rule.min_confidence)}, downside <= ${d.rule.max_downside_abs === null ? "N/A" : `${fmtMoney(d.rule.max_downside_abs)} loss`}
          </div>
          <div class="table-wrap">
            <table class="options">
              <thead>
                <tr>
                  <th>Branch</th>
                  <th>Spot P</th>
                  <th>TWAP P</th>
                  <th>Expected Value</th>
                  <th>Confidence</th>
                  <th>Downside</th>
                  <th>Gate</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>${optionsRows}</tbody>
            </table>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderMarkets() {
  els.markets.innerHTML = state.markets
    .map((m) => {
      const segments = m.probabilities
        .map((p, i) => `<div class="segment" style="width:${Math.max(1.2, p.probability * 100)}%; background:${palette[i % palette.length]}"></div>`)
        .join("");
      const legend = m.probabilities
        .map((p, i) => `<span class="legend-item"><i style="background:${palette[i % palette.length]}"></i>${p.option_id}: spot ${fmtPct(p.probability)} | twap ${fmtPct(p.twap_probability)}</span>`)
        .join("");

      return `
        <article class="market-card">
          <div class="row-top">
            <div>
              <div class="market-id">${m.decision_id}</div>
              <div class="market-id">Use Case: ${m.use_case}</div>
              <strong>${m.title}</strong>
            </div>
            <span class="badge">${m.state}</span>
          </div>
          <div class="stack-bar">${segments}</div>
          <div class="meta">
            <span>Linked branches share one probability pool</span>
            <span>Depth: ${m.depth.toFixed(1)} | closes in ${fmtSecs(m.seconds_remaining)}</span>
          </div>
          <div class="legend">${legend}</div>
        </article>
      `;
    })
    .join("");
}

function renderAccounts() {
  els.accounts.innerHTML = state.accounts
    .map(
      (a) =>
        `<span class="chip">${aliasOf(a.trader_id)}: ${a.token_balance.toFixed(2)} tok | locked ${a.locked_collateral.toFixed(
          2
        )} | avail ${a.available_balance.toFixed(2)}</span>`
    )
    .join("");
}

function renderTrades() {
  const rows = [...state.trades].reverse();
  els.tradesBody.innerHTML = rows
    .map(
      (t) => `
      <tr>
        <td>${aliasOf(t.trader_id)}</td>
        <td>${t.decision_id}</td>
        <td>${t.option_id}</td>
        <td>${t.side}</td>
        <td>${Math.abs(t.shares).toFixed(2)}</td>
        <td>${fmtMoney(t.gross_cost + t.fee_paid)}</td>
      </tr>
      `
    )
    .join("");
}

function renderIncentives() {
  const rows = [...(state.trader_metrics || [])];
  els.incentivesBody.innerHTML = rows
    .map(
      (r) => `
      <tr>
        <td>${aliasOf(r.trader_id)}</td>
        <td>${fmtMoney(r.initial_funding)}</td>
        <td>${fmtMoney(r.total_spent)}</td>
        <td>${fmtMoney(r.realized_payout)}</td>
        <td>${fmtMoney(r.expected_open_payout)}</td>
        <td>${fmtMoney(r.projected_balance)}</td>
        <td class="${r.projected_pnl >= 0 ? "pass" : "fail"}">${fmtMoney(r.projected_pnl)}</td>
      </tr>
      `
    )
    .join("");
}

function renderTradeMath() {
  const rows = [...state.trades].reverse();
  els.mathBody.innerHTML = rows
    .map(
      (t) => `
      <tr>
        <td>${aliasOf(t.trader_id)}</td>
        <td>${t.decision_id}</td>
        <td>${t.option_id}</td>
        <td>${t.side}</td>
        <td>${Math.abs(t.shares).toFixed(2)}</td>
        <td>${fmtCost(t.old_cost)}</td>
        <td>${fmtCost(t.new_cost)}</td>
        <td>${fmtCost(t.gross_cost)}</td>
        <td>${fmtCost(t.fee_paid)}</td>
        <td>${fmtProbabilities(t.before_probabilities, t.after_probabilities)}</td>
      </tr>
      `
    )
    .join("");
}

function hydrateState(data) {
  state.markets = data.markets || [];
  state.accounts = data.accounts || [];
  state.trades = data.trades || [];
  state.decisions = data.decisions || [];
  state.summary = data.summary || null;
  state.trader_metrics = data.trader_metrics || [];
}

function renderAll() {
  fillDecisionSelectors();
  renderSummary();
  renderDecisions();
  renderMarkets();
  renderAccounts();
  renderTrades();
  renderIncentives();
  renderTradeMath();
}

async function fetchState() {
  const res = await fetch("/api/state");
  const data = await res.json();
  hydrateState(data);
  renderAll();
}

async function apiPost(path, payload) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!data.ok) {
    throw new Error(data.error || "Operation failed");
  }
  hydrateState(data.state);
  renderAll();
  return data;
}

els.tradeDecision.addEventListener("change", syncTradeOptionSelector);
els.resolveDecision.addEventListener("change", syncResolveOptionSelector);

els.tradeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = {
      decision_id: els.tradeDecision.value,
      option_id: els.tradeOption.value,
      trader_id: els.tradeTrader.value,
      shares: Number(els.tradeShares.value) * (els.tradeSide.value === "SELL" ? -1 : 1),
    };
    const out = await apiPost("/api/trade", payload);
    setStatus(`Trade executed: ${out.trade.trader_id} ${out.trade.side} ${Math.abs(out.trade.shares).toFixed(2)} ${out.trade.option_id} on ${out.trade.decision_id}.`);
  } catch (err) {
    setStatus(err.message, true);
  }
});

els.resolveForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = {
      decision_id: els.resolveDecision.value,
      winner_option_id: els.resolveOption.value,
    };
    await apiPost("/api/resolve", payload);
    setStatus(`Resolved ${payload.decision_id} with winner ${payload.winner_option_id}.`);
  } catch (err) {
    setStatus(err.message, true);
  }
});

els.setWindowBtn.addEventListener("click", async () => {
  try {
    const payload = {
      decision_id: els.simDecision.value,
      remaining_seconds: Number(els.simRemainingSeconds.value),
    };
    await apiPost("/api/window", payload);
    setStatus(`Window updated: ${payload.decision_id} now closes in ${payload.remaining_seconds}s.`);
  } catch (err) {
    setStatus(err.message, true);
  }
});

els.simulateBtn.addEventListener("click", async () => {
  try {
    const payload = {
      decision_id: els.simDecision.value,
      rounds: Number(els.simRounds.value),
    };
    const out = await apiPost("/api/simulate", payload);
    setStatus(`Simulated ${out.executed} trades on ${payload.decision_id}.`);
  } catch (err) {
    setStatus(err.message, true);
  }
});

els.createDecisionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    let parsedOptions;
    try {
      parsedOptions = JSON.parse(els.newDecisionOptions.value);
    } catch {
      throw new Error("Options JSON is invalid.");
    }

    const payload = {
      decision_id: els.newDecisionId.value.trim(),
      title: els.newDecisionTitle.value.trim(),
      description: els.newDecisionDescription.value.trim(),
      use_case: els.newDecisionUseCase.value.trim() || "Custom",
      options: parsedOptions,
      liquidity_b: Number(els.newDecisionLiquidity.value),
      fee_bps: Number(els.newDecisionFeeBps.value),
    };

    await apiPost("/api/decisions", payload);
    els.createDecisionForm.reset();
    els.newDecisionLiquidity.value = "120";
    els.newDecisionFeeBps.value = "25";
    setStatus(`Decision ${payload.decision_id} created.`);
  } catch (err) {
    setStatus(err.message, true);
  }
});

els.fundTraderForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = {
      trader_id: els.fundTraderId.value.trim(),
      tokens: Number(els.fundTraderTokens.value),
    };
    await apiPost("/api/fund", payload);
    setStatus(`Funded ${payload.trader_id} with ${payload.tokens} tokens.`);
  } catch (err) {
    setStatus(err.message, true);
  }
});

els.resetBtn.addEventListener("click", async () => {
  try {
    await apiPost("/api/reset", {});
    setStatus("System reset to baseline state.");
  } catch (err) {
    setStatus(err.message, true);
  }
});

tabButtons.forEach((btn) => {
  btn.addEventListener("click", () => setTab(btn.dataset.tab));
});
if (els.menuSelect) {
  els.menuSelect.addEventListener("change", () => setTab(els.menuSelect.value));
}

fetchState().then(() => setStatus("Linked decision markets loaded.")).catch((err) => setStatus(err.message, true));
setInterval(() => {
  fetchState().catch(() => {});
}, 3000);
