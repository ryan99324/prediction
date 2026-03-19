from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from protocol import PredictionProtocol

HOST = "127.0.0.1"
PORT = 8000
FRONTEND_DIR = Path(__file__).parent / "frontend"


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
LOCK = threading.Lock()


def protocol_state() -> dict:
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


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }.get(file_path.suffix.lower(), "application/octet-stream")

        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/state":
            with LOCK:
                self._send_json(protocol_state())
            return

        if path == "/":
            self._send_file(FRONTEND_DIR / "index.html")
            return

        if path in {"/styles.css", "/app.js"}:
            self._send_file(FRONTEND_DIR / path.lstrip("/"))
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        global PROTO
        path = urlparse(self.path).path

        if path == "/api/trade":
            try:
                body = self._read_json_body()
                with LOCK:
                    trade = PROTO.place_trade(
                        decision_id=str(body["decision_id"]),
                        option_id=str(body["option_id"]),
                        trader_id=str(body["trader_id"]),
                        shares=float(body["shares"]),
                    )
                    state = protocol_state()
                self._send_json(
                    {
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
                )
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/resolve":
            try:
                body = self._read_json_body()
                with LOCK:
                    PROTO.resolve_decision(
                        decision_id=str(body["decision_id"]),
                        winner_option_id=str(body["winner_option_id"]),
                    )
                    state = protocol_state()
                self._send_json({"ok": True, "state": state})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/reset":
            with LOCK:
                PROTO = build_protocol()
                state = protocol_state()
            self._send_json({"ok": True, "state": state})
            return

        if path == "/api/decisions":
            try:
                body = self._read_json_body()
                with LOCK:
                    PROTO.create_decision(
                        decision_id=str(body["decision_id"]),
                        title=str(body["title"]),
                        description=str(body.get("description", "")),
                        use_case=str(body.get("use_case", "Custom")),
                        options=list(body["options"]),
                        rule=body.get("rule"),
                        liquidity_b=float(body.get("liquidity_b", 120.0)),
                        fee_bps=float(body.get("fee_bps", 25.0)),
                    )
                    state = protocol_state()
                self._send_json({"ok": True, "state": state})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/fund":
            try:
                body = self._read_json_body()
                with LOCK:
                    PROTO.fund_trader(
                        trader_id=str(body["trader_id"]),
                        tokens=float(body["tokens"]),
                    )
                    state = protocol_state()
                self._send_json({"ok": True, "state": state})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/window":
            try:
                body = self._read_json_body()
                with LOCK:
                    PROTO.set_window_remaining(
                        decision_id=str(body["decision_id"]),
                        remaining_seconds=float(body["remaining_seconds"]),
                    )
                    state = protocol_state()
                self._send_json({"ok": True, "state": state})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/simulate":
            try:
                body = self._read_json_body()
                with LOCK:
                    trader_ids = [a["trader_id"] for a in PROTO.account_snapshot()]
                    executed = PROTO.simulate_trade_burst(
                        decision_id=str(body["decision_id"]),
                        trader_ids=trader_ids,
                        rounds=int(body.get("rounds", 10)),
                        min_shares=float(body.get("min_shares", 1.0)),
                        max_shares=float(body.get("max_shares", 6.0)),
                    )
                    state = protocol_state()
                self._send_json({"ok": True, "executed": executed, "state": state})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Decision market server running at http://{HOST}:{PORT}")
    server.serve_forever()
