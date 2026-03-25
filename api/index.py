from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from threading import Lock
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from protocol import PredictionProtocol

try:
    from redis import Redis
except Exception:  # pragma: no cover
    Redis = None


app = FastAPI(title="Decision Market API", version="1.1.0")
LOCAL_LOCK = Lock()
LOCAL_PROTO: PredictionProtocol | None = None
LOCAL_SESSIONS: Dict[str, Dict[str, Any]] = {}

REDIS_URL = os.getenv("REDIS_URL") or os.getenv("KV_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
USE_REDIS = bool(REDIS_URL and Redis is not None and str(REDIS_URL).startswith("redis"))
REDIS = Redis.from_url(REDIS_URL, decode_responses=True) if USE_REDIS else None
STATE_KEY = "pm:state:v2"
LOCK_KEY = "pm:lock:v2"
SESSION_KEY_PREFIX = "pm:session:v1:"
SESSION_COOKIE = "pm_session"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "43200"))  # 12h


def _load_users() -> Dict[str, Dict[str, str]]:
    default_users: Dict[str, Dict[str, str]] = {
        "admin": {"role": "admin", "trader_id": "admin"},
        "team1": {"role": "team", "trader_id": "team_1"},
        "team2": {"role": "team", "trader_id": "team_2"},
        "team3": {"role": "team", "trader_id": "team_3"},
        "team4": {"role": "team", "trader_id": "team_4"},
        "team5": {"role": "team", "trader_id": "team_5"},
        "team6": {"role": "team", "trader_id": "team_6"},
        "team7": {"role": "team", "trader_id": "team_7"},
        "team8": {"role": "team", "trader_id": "team_8"},
        "team9": {"role": "team", "trader_id": "team_9"},
        "team10": {"role": "team", "trader_id": "team_10"},
        "team11": {"role": "team", "trader_id": "team_11"},
    }

    raw = os.getenv("APP_USERS_JSON", "").strip()
    if raw:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("APP_USERS_JSON must be a JSON object")
        normalized = {str(k).strip().lower(): v for k, v in parsed.items()}
        merged = dict(default_users)
        merged.update(normalized)
        return merged

    return default_users


USERS = _load_users()


def _ensure_user_accounts(proto: PredictionProtocol) -> None:
    for username, user in USERS.items():
        if user.get("role") != "team":
            continue
        trader_id = user.get("trader_id")
        if not trader_id:
            continue
        if trader_id not in proto.accounts:
            proto.fund_trader(trader_id, 700.0)


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
        "team_1",
        "team_2",
        "team_3",
        "team_4",
        "team_5",
        "team_6",
        "team_7",
        "team_8",
        "team_9",
        "team_10",
        "team_11",
    ]:
        proto.fund_trader(trader, 700.0)

    return proto


def _load_proto() -> PredictionProtocol:
    global LOCAL_PROTO
    if REDIS is None:
        if LOCAL_PROTO is None:
            LOCAL_PROTO = build_protocol()
            _ensure_user_accounts(LOCAL_PROTO)
        return LOCAL_PROTO

    raw = REDIS.get(STATE_KEY)
    if raw:
        proto = PredictionProtocol.from_dict(json.loads(raw))
        _ensure_user_accounts(proto)
        REDIS.set(STATE_KEY, json.dumps(proto.to_dict()))
        return proto

    proto = build_protocol()
    _ensure_user_accounts(proto)
    REDIS.set(STATE_KEY, json.dumps(proto.to_dict()))
    return proto


def _save_proto(proto: PredictionProtocol) -> None:
    global LOCAL_PROTO
    if REDIS is None:
        LOCAL_PROTO = proto
        return
    REDIS.set(STATE_KEY, json.dumps(proto.to_dict()))


@contextmanager
def _mutation_lock(timeout_s: float = 10.0):
    if REDIS is None:
        with LOCAL_LOCK:
            yield
        return

    token = str(uuid.uuid4())
    deadline = time.time() + timeout_s
    acquired = False
    while time.time() < deadline:
        if REDIS.set(LOCK_KEY, token, nx=True, ex=15):
            acquired = True
            break
        time.sleep(0.05)

    if not acquired:
        raise RuntimeError("Failed to acquire state lock")

    try:
        yield
    finally:
        release_script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        else
            return 0
        end
        """
        REDIS.eval(release_script, 1, LOCK_KEY, token)


def _state_response(proto: PredictionProtocol) -> Dict[str, Any]:
    proto.auto_close_expired_decisions()
    return {
        "decisions": proto.all_decision_snapshots(),
        "markets": proto.linked_market_snapshot(),
        "accounts": proto.account_snapshot(),
        "trader_metrics": proto.trader_incentive_snapshot(),
        "summary": proto.enterprise_decision_summary(),
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
            for t in proto.trades[-50:]
        ],
    }


def _ok(state: Dict[str, Any], extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = {"ok": True, "state": state}
    if extra:
        payload.update(extra)
    return payload


def _bad(msg: str, status: int = 400):
    return JSONResponse(status_code=status, content={"ok": False, "error": msg})


def _session_key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


def _save_session(session_id: str, session: Dict[str, str]) -> None:
    if REDIS is None:
        global LOCAL_SESSIONS
        LOCAL_SESSIONS[session_id] = {"session": session, "expires_at": time.time() + SESSION_TTL_SECONDS}
        return
    REDIS.setex(_session_key(session_id), SESSION_TTL_SECONDS, json.dumps(session))


def _delete_session(session_id: str) -> None:
    if not session_id:
        return
    if REDIS is None:
        LOCAL_SESSIONS.pop(session_id, None)
        return
    REDIS.delete(_session_key(session_id))


def _get_session(request: Request) -> Optional[Dict[str, str]]:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return None

    if REDIS is None:
        rec = LOCAL_SESSIONS.get(session_id)
        if rec is None:
            return None
        if float(rec.get("expires_at", 0)) < time.time():
            LOCAL_SESSIONS.pop(session_id, None)
            return None
        return rec.get("session")

    raw = REDIS.get(_session_key(session_id))
    if not raw:
        return None
    REDIS.expire(_session_key(session_id), SESSION_TTL_SECONDS)
    return json.loads(raw)


def _require_auth(request: Request) -> Dict[str, str]:
    session = _get_session(request)
    if not session:
        raise PermissionError("Please login first")
    return session


def _require_admin(request: Request) -> Dict[str, str]:
    session = _require_auth(request)
    if session.get("role") != "admin":
        raise PermissionError("Admin role required")
    return session


class TradePayload(BaseModel):
    decision_id: str
    option_id: str
    trader_id: Optional[str] = None
    shares: float


class LoginPayload(BaseModel):
    username: str


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
def get_state(request: Request) -> Dict[str, Any]:
    try:
        _require_auth(request)
        proto = _load_proto()
        state = _state_response(proto)
        _save_proto(proto)
        return state
    except Exception as exc:
        if isinstance(exc, PermissionError):
            return _bad(str(exc), status=401)
        return _bad(str(exc))


@app.post("/api/login")
def post_login(payload: LoginPayload, response: Response):
    username = payload.username.strip().lower()
    user = USERS.get(username)
    if not user:
        return _bad("Invalid username", status=401)

    session = {
        "username": username,
        "role": user.get("role", "team"),
        "trader_id": user.get("trader_id", username),
    }
    session_id = str(uuid.uuid4())
    _save_session(session_id, session)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
    )
    return {"ok": True, "session": session}


@app.post("/api/logout")
def post_logout(request: Request, response: Response):
    session_id = request.cookies.get(SESSION_COOKIE, "")
    _delete_session(session_id)
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.get("/api/me")
def get_me(request: Request):
    session = _get_session(request)
    if not session:
        return _bad("Not logged in", status=401)
    return {"ok": True, "session": session}


@app.post("/api/trade")
def post_trade(payload: TradePayload, request: Request):
    try:
        session = _require_auth(request)
        trader_id = session.get("trader_id", "")
        if session.get("role") == "admin":
            trader_id = payload.trader_id or trader_id
        if not trader_id:
            return _bad("No trader assigned to this session", status=403)

        with _mutation_lock():
            proto = _load_proto()
            trade = proto.place_trade(
                decision_id=payload.decision_id,
                option_id=payload.option_id,
                trader_id=trader_id,
                shares=payload.shares,
            )
            state = _state_response(proto)
            _save_proto(proto)
            return _ok(
                state,
                {
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
                    }
                },
            )
    except Exception as exc:
        if isinstance(exc, PermissionError):
            return _bad(str(exc), status=403)
        return _bad(str(exc))


@app.post("/api/resolve")
def post_resolve(payload: ResolvePayload, request: Request):
    try:
        _require_admin(request)
        with _mutation_lock():
            proto = _load_proto()
            proto.resolve_decision(
                decision_id=payload.decision_id,
                winner_option_id=payload.winner_option_id,
            )
            state = _state_response(proto)
            _save_proto(proto)
            return _ok(state)
    except Exception as exc:
        if isinstance(exc, PermissionError):
            return _bad(str(exc), status=403)
        return _bad(str(exc))


@app.post("/api/fund")
def post_fund(payload: FundPayload, request: Request):
    try:
        _require_admin(request)
        with _mutation_lock():
            proto = _load_proto()
            proto.fund_trader(trader_id=payload.trader_id, tokens=payload.tokens)
            state = _state_response(proto)
            _save_proto(proto)
            return _ok(state)
    except Exception as exc:
        if isinstance(exc, PermissionError):
            return _bad(str(exc), status=403)
        return _bad(str(exc))


@app.post("/api/window")
def post_window(payload: WindowPayload, request: Request):
    try:
        _require_admin(request)
        with _mutation_lock():
            proto = _load_proto()
            proto.set_window_remaining(
                decision_id=payload.decision_id,
                remaining_seconds=payload.remaining_seconds,
            )
            state = _state_response(proto)
            _save_proto(proto)
            return _ok(state)
    except Exception as exc:
        if isinstance(exc, PermissionError):
            return _bad(str(exc), status=403)
        return _bad(str(exc))


@app.post("/api/simulate")
def post_simulate(payload: SimulatePayload, request: Request):
    try:
        _require_admin(request)
        with _mutation_lock():
            proto = _load_proto()
            trader_ids = [a["trader_id"] for a in proto.account_snapshot()]
            executed = proto.simulate_trade_burst(
                decision_id=payload.decision_id,
                trader_ids=trader_ids,
                rounds=payload.rounds,
                min_shares=payload.min_shares,
                max_shares=payload.max_shares,
            )
            state = _state_response(proto)
            _save_proto(proto)
            return _ok(state, {"executed": executed})
    except Exception as exc:
        if isinstance(exc, PermissionError):
            return _bad(str(exc), status=403)
        return _bad(str(exc))


@app.post("/api/decisions")
def post_decisions(payload: CreateDecisionPayload, request: Request):
    try:
        _require_admin(request)
        with _mutation_lock():
            proto = _load_proto()
            proto.create_decision(
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
            state = _state_response(proto)
            _save_proto(proto)
            return _ok(state)
    except Exception as exc:
        if isinstance(exc, PermissionError):
            return _bad(str(exc), status=403)
        return _bad(str(exc))


@app.post("/api/reset")
def post_reset(request: Request):
    try:
        _require_admin(request)
        with _mutation_lock():
            if REDIS is not None:
                REDIS.delete(STATE_KEY)
            proto = build_protocol()
            state = _state_response(proto)
            _save_proto(proto)
            return _ok(state)
    except Exception as exc:
        if isinstance(exc, PermissionError):
            return _bad(str(exc), status=403)
        return _bad(str(exc))


@app.get("/api/health")
def get_health() -> Dict[str, Any]:
    return {
        "ok": True,
        "storage": "redis" if REDIS is not None else "memory",
    }
