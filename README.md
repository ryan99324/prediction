# Internal Decision Market Protocol (Prototype)

This folder contains a decision-focused internal prediction market system: backend protocol + frontend control room.

## What this version demonstrates
- LMSR market-implied probabilities for linked multi-outcome decisions
- One decision = one market with multiple mutually exclusive branches
- Branch probabilities share one pool and sum to 100%
- Preloaded showcase decisions across multiple types:
  - M&A (2 scenarios)
  - Product Launch
  - Pricing
- Two-sided trading: `BUY` and `SELL (short)` per branch
- Collateralized shorting with risk controls (locked collateral + available balance)
- Leadership operations:
  - create new decisions live
  - fund/onboard new traders
- Trader incentive analytics:
  - funded capital, spend, realized payout, expected open payout, projected PnL
- Trade-level calculation transparency in UI (`Trade Math` tab):
  - `C_before`, `C_after`, `Delta C` (gross cost), fee
  - branch probability vector before and after each trade
- Simulator controls for demos:
  - set remaining window time
  - run automated trade bursts to visibly move spot/TWAP
- Governance policy gates before recommendation:
  - minimum expected value
  - minimum probability of success
  - minimum confidence
  - maximum downside limit
- Recommendation states:
  - `RECOMMEND`
  - `ESCALATE` (too close to call)
  - `DEFER` (no option passes policy)
- Portfolio-level decision summary across M&A, PMF rollout, and quarterly execution

## Files
- `protocol.py`: market engine, decision-policy logic, recommendation generation
- `server.py`: local HTTP API + state management
- `frontend/index.html`: decision dashboard UI
- `frontend/styles.css`: styling and responsive layout
- `frontend/app.js`: UI rendering + trade/resolve/reset API actions
- `demo.py`: legacy CLI scenario demo (kept for reference)

## Run Frontend
```powershell
cd "c:\Users\Ryan\OneDrive\Desktop\Y4S2\Financial innovation\Project"
python server.py
```
Open `http://127.0.0.1:8000`.

## API
- `GET /api/state`: full state (markets, decisions, accounts, trades, summary)
- `POST /api/trade`: execute trade using `decision_id`, `option_id`, `trader_id`, `shares`
- `POST /api/resolve`: resolve decision using `decision_id`, `winner_option_id`
- `POST /api/decisions`: create decision using `decision_id`, `title`, `description`, `options`, optional `rule`, `liquidity_b`, `fee_bps`
- `POST /api/fund`: fund trader using `trader_id`, `tokens`
- `POST /api/window`: set decision window remaining seconds (`decision_id`, `remaining_seconds`)
- `POST /api/simulate`: run simulated trade burst (`decision_id`, `rounds`)
- `POST /api/reset`: reset baseline scenario

## Vercel Deployment
This repo is configured for Vercel with:
- static frontend from `frontend/`
- serverless Python API at `api/index.py`

Files:
- [vercel.json](c:\Users\Ryan\OneDrive\Desktop\Y4S2\Financial innovation\Project\vercel.json)
- [requirements.txt](c:\Users\Ryan\OneDrive\Desktop\Y4S2\Financial innovation\Project\requirements.txt)

Deploy:
```powershell
cd "c:\Users\Ryan\OneDrive\Desktop\Y4S2\Financial innovation\Project"
vercel
vercel --prod
```

## Decision model notes
- Forecast layer: each decision has linked branch probabilities `P(branch_i)` with `sum_i P(branch_i) = 1`.
- Value layer: `EV = p * net_success + (1 - p) * net_failure`.
- Policy layer: option must pass governance thresholds to be eligible.
- Action layer: pick highest-EV eligible option, else escalate/defer.
- Trading layer: signed shares (`+` buy, `-` sell/short), with LMSR delta-cost pricing.
- Risk layer: short exposure requires collateral based on worst-case open decision liability.

## Suggested next extensions
- Add authentication, role-based permissions, and audit trails
- Add market templates linked to actual KPI definitions and data feeds
- Add calibration metrics per trader/team (Brier/log score)
- Add scenario presets for board presentation mode
