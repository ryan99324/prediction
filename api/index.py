from __future__ import annotations

from typing import Any, Dict, List
from threading import Lock

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from protocol import PredictionProtocol


app = FastAPI(title="Decision Market API", version="1.0.0")
LOCK = Lock()


def build_protocol() -> PredictionProtocol:
    proto = PredictionProtocol()

    proto.create_decision(
        decision_id="MNA_APEX_ROBOTICS_2026",
        title="Apex Robotics ($1.20B) IRR Simulator",
        description="Employees trade PASS/FAIL contracts for whether acquiring Apex Robotics at $1.20B beats 12% IRR in 3 years.",
        use_case="M&A",
        options=[
            {
                "option_id": "PASS",
                "label": "PASS (>12% IRR in 3Y)",
                "success_value": 250_000_000,
                "failure_value": -80_000_000,
                "implementation_cost": 30_000_000,
                "risk_penalty": 12_000_000,
            },
            {
                "option_id": "FAIL",
                "label": "FAIL (<=12% IRR in 3Y)",
                "success_value": 40_000_000,
                "failure_value": -140_000_000,
                "implementation_cost": 18_000_000,
                "risk_penalty": 10_000_000,
            },
        ],
        rule={
            "min_expected_value": 0,
            "min_probability": 0.55,
            "min_confidence": 0.08,
            "max_downside_abs": 180_000_000,
            "tie_margin": 8_000_000,
        },
        liquidity_b=140,
        fee_bps=30,
        window_seconds=3600.0,
    )

    proto.create_decision(
        decision_id="MNA_BLUEWAVE_LOGISTICS_2026",
        title="BlueWave Logistics ($850M) IRR Simulator",
        description="Employees trade PASS/FAIL contracts for whether acquiring BlueWave Logistics at $850M beats 10% IRR in 3 years.",
        use_case="M&A",
        options=[
            {
                "option_id": "PASS",
                "label": "PASS (>10% IRR in 3Y)",
                "success_value": 170_000_000,
                "failure_value": -55_000_000,
                "implementation_cost": 22_000_000,
                "risk_penalty": 9_000_000,
            },
            {
                "option_id": "FAIL",
                "label": "FAIL (<=10% IRR in 3Y)",
                "success_value": 25_000_000,
                "failure_value": -105_000_000,
                "implementation_cost": 16_000_000,
                "risk_penalty": 8_000_000,
            },
        ],
        rule={
            "min_expected_value": 0,
            "min_probability": 0.53,
            "min_confidence": 0.07,
            "max_downside_abs": 150_000_000,
            "tie_margin": 6_000_000,
        },
        liquidity_b=120,
        fee_bps=28,
        window_seconds=5400.0,
    )

    proto.create_decision(
        decision_id="PRODUCT_ORBITAI_LAUNCH_2026",
        title="OrbitAI Launch Readiness Simulator",
        description="PASS if OrbitAI reaches 150K MAU with >=35% D30 retention by Q4 2026; FAIL otherwise.",
        use_case="Product Launch",
        options=[
            {
                "option_id": "PASS",
                "label": "PASS (MAU+Retention target met)",
                "success_value": 140_000_000,
                "failure_value": -45_000_000,
                "implementation_cost": 28_000_000,
                "risk_penalty": 7_000_000,
            },
            {
                "option_id": "FAIL",
                "label": "FAIL (target missed)",
                "success_value": 20_000_000,
                "failure_value": -92_000_000,
                "implementation_cost": 16_000_000,
                "risk_penalty": 8_000_000,
            },
        ],
        rule={
            "min_expected_value": 5_000_000,
            "min_probability": 0.56,
            "min_confidence": 0.08,
            "max_downside_abs": 130_000_000,
            "tie_margin": 5_000_000,
        },
        liquidity_b=115,
        fee_bps=24,
        window_seconds=4200.0,
    )

    proto.create_decision(
        decision_id="PRICING_PRO_PLAN_2026",
        title="Pro Plan Price Change Simulator",
        description="PASS if raising Pro price from $49 to $59 lifts gross margin dollars without churn >3.5% in 2 quarters.",
        use_case="Pricing",
        options=[
            {
                "option_id": "PASS",
                "label": "PASS (margin up, churn controlled)",
                "success_value": 95_000_000,
                "failure_value": -30_000_000,
                "implementation_cost": 9_000_000,
                "risk_penalty": 4_000_000,
            },
            {
                "option_id": "FAIL",
                "label": "FAIL (churn shock / margin miss)",
                "success_value": 15_000_000,
                "failure_value": -75_000_000,
                "implementation_cost": 7_000_000,
                "risk_penalty": 5_000_000,
            },
        ],
        rule={
            "min_expected_value": 0,
            "min_probability": 0.54,
            "min_confidence": 0.07,
            "max_downside_abs": 95_000_000,
            "tie_margin": 4_000_000,
        },
        liquidity_b=105,
        fee_bps=22,
        window_seconds=3600.0,
    )

    for trader in [
        "finance_lead",
        "product_mgr",
        "sales_director",
        "corp_dev",
        "strategy_office",
        "ops_lead",
    ]:
        proto.fund_trader(trader, 700.0)

    return proto


PROTO = build_protocol()


def protocol_state() -> Dict[str, Any]:
    PROTO.auto_close_expired_decisions()
    decisions = PROTO.all_decision_snapshots()
    linked_markets = PROTO.linked_market_snapshot()
    return {
        "decisions": decisions,
        "markets": linked_markets,
        "accounts": PROTO.account_snapshot(),
        "trader_metrics": PROTO.trader_incentive_snapshot(),
        "summary": PROTO.enterprise_decision_summary(),
        "trades": [
            {
                "decision_id": t.decision_id,
                "option_id": t.option_id,
                "trader_id": t.trader_id,
                "side": t.side,
                "shares": round(t.shares, 4),
                "gross_cost": round(t.gross_cost, 4),
                "fee_paid": round(t.fee_paid, 4),
                "old_cost": round(t.old_cost, 6),
                "new_cost": round(t.new_cost, 6),
                "before_probabilities": {k: round(v, 6) for k, v in t.before_probabilities.items()},
                "after_probabilities": {k: round(v, 6) for k, v in t.after_probabilities.items()},
                "ts": round(t.ts, 3),
            }
            for t in PROTO.trades[-50:]
        ],
    }


class TradePayload(BaseModel):
    decision_id: str
    option_id: str
    trader_id: str
    shares: float


class ResolvePayload(BaseModel):
    decision_id: str
    winner_option_id: str


class FundPayload(BaseModel):
    trader_id: str
    tokens: float


class WindowPayload(BaseModel):
    decision_id: str
    remaining_seconds: float


class SimulatePayload(BaseModel):
    decision_id: str
    rounds: int = 10
    min_shares: float = 1.0
    max_shares: float = 6.0


class CreateDecisionPayload(BaseModel):
    decision_id: str
    title: str
    description: str = ""
    use_case: str = "Custom"
    options: List[Dict[str, Any]]
    rule: Dict[str, Any] | None = None
    liquidity_b: float = 120.0
    fee_bps: float = 25.0
    window_seconds: float = 1800.0


@app.get("/api/state")
def get_state() -> Dict[str, Any]:
    with LOCK:
        return protocol_state()


@app.post("/api/trade")
def post_trade(payload: TradePayload) -> Dict[str, Any]:
    try:
        with LOCK:
            trade = PROTO.place_trade(
                decision_id=payload.decision_id,
                option_id=payload.option_id,
                trader_id=payload.trader_id,
                shares=payload.shares,
            )
            state = protocol_state()
        return {
            "ok": True,
            "trade": {
                "decision_id": trade.decision_id,
                "option_id": trade.option_id,
                "trader_id": trade.trader_id,
                "side": trade.side,
                "shares": round(trade.shares, 4),
                "gross_cost": round(trade.gross_cost, 4),
                "fee_paid": round(trade.fee_paid, 4),
                "old_cost": round(trade.old_cost, 6),
                "new_cost": round(trade.new_cost, 6),
                "before_probabilities": {k: round(v, 6) for k, v in trade.before_probabilities.items()},
                "after_probabilities": {k: round(v, 6) for k, v in trade.after_probabilities.items()},
                "ts": round(trade.ts, 3),
            },
            "state": state,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/resolve")
def post_resolve(payload: ResolvePayload) -> Dict[str, Any]:
    try:
        with LOCK:
            PROTO.resolve_decision(
                decision_id=payload.decision_id,
                winner_option_id=payload.winner_option_id,
            )
            state = protocol_state()
        return {"ok": True, "state": state}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/fund")
def post_fund(payload: FundPayload) -> Dict[str, Any]:
    try:
        with LOCK:
            PROTO.fund_trader(trader_id=payload.trader_id, tokens=payload.tokens)
            state = protocol_state()
        return {"ok": True, "state": state}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/window")
def post_window(payload: WindowPayload) -> Dict[str, Any]:
    try:
        with LOCK:
            PROTO.set_window_remaining(
                decision_id=payload.decision_id,
                remaining_seconds=payload.remaining_seconds,
            )
            state = protocol_state()
        return {"ok": True, "state": state}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/simulate")
def post_simulate(payload: SimulatePayload) -> Dict[str, Any]:
    try:
        with LOCK:
            trader_ids = [a["trader_id"] for a in PROTO.account_snapshot()]
            executed = PROTO.simulate_trade_burst(
                decision_id=payload.decision_id,
                trader_ids=trader_ids,
                rounds=payload.rounds,
                min_shares=payload.min_shares,
                max_shares=payload.max_shares,
            )
            state = protocol_state()
        return {"ok": True, "executed": executed, "state": state}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/decisions")
def post_decisions(payload: CreateDecisionPayload) -> Dict[str, Any]:
    try:
        with LOCK:
            PROTO.create_decision(
                decision_id=payload.decision_id,
                title=payload.title,
                description=payload.description,
                use_case=payload.use_case,
                options=payload.options,
                rule=payload.rule,
                liquidity_b=payload.liquidity_b,
                fee_bps=payload.fee_bps,
                window_seconds=payload.window_seconds,
            )
            state = protocol_state()
        return {"ok": True, "state": state}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/reset")
def post_reset() -> Dict[str, Any]:
    global PROTO
    with LOCK:
        PROTO = build_protocol()
        state = protocol_state()
    return {"ok": True, "state": state}
