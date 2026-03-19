from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class DecisionState(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class RecommendationStatus(str, Enum):
    RECOMMEND = "RECOMMEND"
    DEFER = "DEFER"
    ESCALATE = "ESCALATE"


@dataclass
class DecisionRule:
    min_expected_value: float = 0.0
    min_probability: float = 0.0
    min_confidence: float = 0.0
    max_downside_abs: Optional[float] = None
    tie_margin: float = 0.0


@dataclass
class DecisionBranch:
    option_id: str
    label: str
    success_value: float
    failure_value: float
    implementation_cost: float = 0.0
    risk_penalty: float = 0.0


@dataclass
class DecisionMarket:
    decision_id: str
    title: str
    description: str
    use_case: str
    branches: Dict[str, DecisionBranch]
    rule: DecisionRule
    liquidity_b: float
    fee_bps: float = 25.0
    window_seconds: float = 1800.0
    state: DecisionState = DecisionState.OPEN
    resolved_option_id: Optional[str] = None
    q: Dict[str, float] = field(default_factory=dict)
    window_open_ts: float = field(default_factory=time.time)
    window_close_ts: float = 0.0
    last_twap_update_ts: float = 0.0
    twap_integral: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.liquidity_b <= 0:
            raise ValueError("liquidity_b must be positive")
        if not self.branches:
            raise ValueError("decision must include at least one branch")
        for option_id in self.branches:
            self.q.setdefault(option_id, 0.0)
            self.twap_integral.setdefault(option_id, 0.0)
        if self.window_seconds <= 0:
            self.window_seconds = 1800.0
        self.window_close_ts = self.window_open_ts + self.window_seconds
        self.last_twap_update_ts = self.window_open_ts

    def _cost(self, q: Dict[str, float]) -> float:
        b = self.liquidity_b
        return b * math.log(sum(math.exp(v / b) for v in q.values()))

    def probability_map(self) -> Dict[str, float]:
        b = self.liquidity_b
        weights = {k: math.exp(v / b) for k, v in self.q.items()}
        total = sum(weights.values())
        return {k: w / total for k, w in weights.items()}

    def _update_twap(self, now_ts: Optional[float] = None) -> None:
        now_ts = time.time() if now_ts is None else now_ts
        effective_now = min(now_ts, self.window_close_ts)
        if effective_now <= self.last_twap_update_ts:
            return
        probs = self.probability_map()
        dt = effective_now - self.last_twap_update_ts
        for option_id, p in probs.items():
            self.twap_integral[option_id] = self.twap_integral.get(option_id, 0.0) + p * dt
        self.last_twap_update_ts = effective_now

    def twap_map(self, now_ts: Optional[float] = None) -> Dict[str, float]:
        self._update_twap(now_ts)
        elapsed = max(1e-9, min((time.time() if now_ts is None else now_ts), self.window_close_ts) - self.window_open_ts)
        return {k: self.twap_integral.get(k, 0.0) / elapsed for k in self.branches}

    def seconds_remaining(self, now_ts: Optional[float] = None) -> float:
        now_ts = time.time() if now_ts is None else now_ts
        return max(0.0, self.window_close_ts - now_ts)

    def close_by_price_if_expired(self, now_ts: Optional[float] = None) -> Optional[str]:
        now_ts = time.time() if now_ts is None else now_ts
        if self.state != DecisionState.OPEN:
            return None
        if now_ts < self.window_close_ts:
            return None
        self._update_twap(now_ts)
        spot = self.probability_map()
        twap = self.twap_map(now_ts)
        sorted_by_rule = sorted(
            self.branches.keys(),
            key=lambda k: (spot.get(k, 0.0), twap.get(k, 0.0), k),
            reverse=True,
        )
        return sorted_by_rule[0]

    def price(self, option_id: str) -> float:
        if option_id not in self.branches:
            raise ValueError("unknown option_id")
        return self.probability_map()[option_id]

    def trade_cost(self, option_id: str, shares: float) -> float:
        if self.state != DecisionState.OPEN:
            raise ValueError("decision market is not open")
        if option_id not in self.branches:
            raise ValueError("unknown option_id")
        if shares == 0:
            raise ValueError("shares cannot be zero")

        old_cost = self._cost(self.q)
        new_q = dict(self.q)
        new_q[option_id] += shares
        new_cost = self._cost(new_q)
        return new_cost - old_cost

    def execute_trade(
        self, option_id: str, shares: float
    ) -> tuple[float, float, float, Dict[str, float], Dict[str, float]]:
        self._update_twap()
        before_probabilities = self.probability_map()
        old_cost = self._cost(self.q)
        gross = self.trade_cost(option_id, shares)
        self.q[option_id] += shares
        new_cost = self._cost(self.q)
        after_probabilities = self.probability_map()
        return gross, old_cost, new_cost, before_probabilities, after_probabilities

    def depth(self) -> float:
        return sum(self.q.values())


@dataclass
class TraderAccount:
    trader_id: str
    token_balance: float = 0.0
    initial_funding: float = 0.0
    gross_spent: float = 0.0
    fee_spent: float = 0.0
    realized_payout: float = 0.0
    positions: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class Trade:
    decision_id: str
    option_id: str
    trader_id: str
    shares: float
    gross_cost: float
    fee_paid: float
    old_cost: float
    new_cost: float
    before_probabilities: Dict[str, float]
    after_probabilities: Dict[str, float]
    side: str
    ts: float


class PredictionProtocol:
    def __init__(self) -> None:
        self.decisions: Dict[str, DecisionMarket] = {}
        self.accounts: Dict[str, TraderAccount] = {}
        self.trades: List[Trade] = []

    def ensure_trader(self, trader_id: str) -> TraderAccount:
        if trader_id not in self.accounts:
            self.accounts[trader_id] = TraderAccount(trader_id=trader_id)
        return self.accounts[trader_id]

    def fund_trader(self, trader_id: str, tokens: float) -> None:
        if tokens <= 0:
            raise ValueError("tokens must be positive")
        account = self.ensure_trader(trader_id)
        account.token_balance += tokens
        account.initial_funding += tokens

    def create_decision(
        self,
        decision_id: str,
        title: str,
        description: str,
        use_case: str,
        options: List[dict],
        rule: Optional[dict] = None,
        liquidity_b: float = 120.0,
        fee_bps: float = 25.0,
        window_seconds: float = 1800.0,
    ) -> None:
        if decision_id in self.decisions:
            raise ValueError(f"decision_id already exists: {decision_id}")
        if not options:
            raise ValueError("options cannot be empty")

        branches: Dict[str, DecisionBranch] = {}
        for opt in options:
            option_id = str(opt["option_id"])
            if option_id in branches:
                raise ValueError(f"duplicate option_id: {option_id}")
            branches[option_id] = DecisionBranch(
                option_id=option_id,
                label=str(opt["label"]),
                success_value=float(opt["success_value"]),
                failure_value=float(opt["failure_value"]),
                implementation_cost=float(opt.get("implementation_cost", 0.0)),
                risk_penalty=float(opt.get("risk_penalty", 0.0)),
            )

        parsed_rule = DecisionRule() if rule is None else DecisionRule(
            min_expected_value=float(rule.get("min_expected_value", 0.0)),
            min_probability=float(rule.get("min_probability", 0.0)),
            min_confidence=float(rule.get("min_confidence", 0.0)),
            max_downside_abs=(None if rule.get("max_downside_abs") is None else float(rule.get("max_downside_abs"))),
            tie_margin=float(rule.get("tie_margin", 0.0)),
        )

        self.decisions[decision_id] = DecisionMarket(
            decision_id=decision_id,
            title=title,
            description=description,
            use_case=use_case,
            branches=branches,
            rule=parsed_rule,
            liquidity_b=liquidity_b,
            fee_bps=fee_bps,
            window_seconds=window_seconds,
        )

    def auto_close_expired_decisions(self) -> None:
        for decision_id, decision in self.decisions.items():
            winner = decision.close_by_price_if_expired()
            if winner is not None:
                self.resolve_decision(decision_id=decision_id, winner_option_id=winner)

    def set_window_remaining(self, decision_id: str, remaining_seconds: float) -> None:
        if remaining_seconds < 0:
            raise ValueError("remaining_seconds must be non-negative")
        decision = self.decisions[decision_id]
        if decision.state != DecisionState.OPEN:
            raise ValueError("decision market is not open")
        now = time.time()
        decision._update_twap(now)
        decision.window_close_ts = now + remaining_seconds
        if decision.window_close_ts < decision.window_open_ts:
            decision.window_open_ts = now
            decision.last_twap_update_ts = now
            for option_id in decision.twap_integral:
                decision.twap_integral[option_id] = 0.0

    def simulate_trade_burst(
        self,
        decision_id: str,
        trader_ids: List[str],
        rounds: int = 10,
        min_shares: float = 1.0,
        max_shares: float = 6.0,
    ) -> int:
        if rounds <= 0:
            return 0
        if not trader_ids:
            return 0
        decision = self.decisions[decision_id]
        if decision.state != DecisionState.OPEN:
            return 0
        option_ids = list(decision.branches.keys())
        executed = 0
        for _ in range(rounds):
            self.auto_close_expired_decisions()
            if decision.state != DecisionState.OPEN:
                break
            trader_id = random.choice(trader_ids)
            option_id = random.choice(option_ids)
            side = random.choice([1.0, 1.0, 1.0, -1.0])  # biased toward buys for visible movement
            shares = round(random.uniform(min_shares, max_shares), 2) * side
            try:
                self.place_trade(
                    decision_id=decision_id,
                    option_id=option_id,
                    trader_id=trader_id,
                    shares=shares,
                )
                executed += 1
            except Exception:
                continue
        return executed

    def place_trade(self, decision_id: str, option_id: str, trader_id: str, shares: float) -> Trade:
        decision = self.decisions[decision_id]
        account = self.ensure_trader(trader_id)
        winner = decision.close_by_price_if_expired()
        if winner is not None:
            self.resolve_decision(decision_id=decision_id, winner_option_id=winner)
            raise ValueError("decision window has closed")
        if decision.state != DecisionState.OPEN:
            raise ValueError("decision market is not open")

        if shares == 0:
            raise ValueError("shares cannot be zero")

        prev_balance = account.token_balance
        prev_gross_spent = account.gross_spent
        prev_fee_spent = account.fee_spent
        prev_position = account.positions.get(decision_id, {}).get(option_id, 0.0)

        gross_cost, old_cost, new_cost, before_probs, after_probs = decision.execute_trade(
            option_id=option_id, shares=shares
        )
        fee = abs(gross_cost) * (decision.fee_bps / 10_000.0)
        total_cost = gross_cost + fee

        account.token_balance -= total_cost
        account.gross_spent += max(0.0, gross_cost)
        account.fee_spent += fee
        account.positions.setdefault(decision_id, {})
        account.positions[decision_id][option_id] = account.positions[decision_id].get(option_id, 0.0) + shares

        if account.token_balance < 0 or account.token_balance < self._required_collateral(account):
            # Rollback state if liquidity/collateral checks fail.
            decision.q[option_id] -= shares
            account.token_balance = prev_balance
            account.gross_spent = prev_gross_spent
            account.fee_spent = prev_fee_spent
            if decision_id in account.positions:
                account.positions[decision_id][option_id] = prev_position
            raise ValueError("insufficient collateral for trade")

        trade = Trade(
            decision_id=decision_id,
            option_id=option_id,
            trader_id=trader_id,
            shares=shares,
            gross_cost=gross_cost,
            fee_paid=fee,
            old_cost=old_cost,
            new_cost=new_cost,
            before_probabilities=before_probs,
            after_probabilities=after_probs,
            side="BUY" if shares > 0 else "SELL",
            ts=time.time(),
        )
        self.trades.append(trade)
        return trade

    def resolve_decision(self, decision_id: str, winner_option_id: str) -> None:
        decision = self.decisions[decision_id]
        if decision.state == DecisionState.RESOLVED:
            raise ValueError("decision already resolved")
        if winner_option_id not in decision.branches:
            raise ValueError("unknown winner option_id")

        decision.state = DecisionState.RESOLVED
        decision.resolved_option_id = winner_option_id

        for account in self.accounts.values():
            shares = account.positions.get(decision_id, {}).get(winner_option_id, 0.0)
            account.token_balance += shares
            account.realized_payout += shares

    def linked_market_snapshot(self) -> List[dict]:
        rows = []
        for decision in self.decisions.values():
            decision.close_by_price_if_expired()
            probabilities = decision.probability_map()
            twap = decision.twap_map()
            rows.append(
                {
                    "decision_id": decision.decision_id,
                    "title": decision.title,
                    "use_case": decision.use_case,
                    "state": decision.state.value,
                    "depth": round(decision.depth(), 2),
                    "seconds_remaining": round(decision.seconds_remaining(), 2),
                    "probabilities": [
                        {
                            "option_id": branch.option_id,
                            "label": branch.label,
                            "probability": round(probabilities[branch.option_id], 4),
                            "twap_probability": round(twap[branch.option_id], 4),
                            "q": round(decision.q[branch.option_id], 2),
                        }
                        for branch in decision.branches.values()
                    ],
                }
            )
        return rows

    def _required_collateral(self, account: TraderAccount) -> float:
        # Worst-case liability from short positions across all open decisions.
        required = 0.0
        for decision_id, branch_positions in account.positions.items():
            decision = self.decisions.get(decision_id)
            if decision is None or decision.state != DecisionState.OPEN:
                continue
            worst_case_decision_loss = 0.0
            for option_id in decision.branches:
                position = branch_positions.get(option_id, 0.0)
                if position < 0:
                    worst_case_decision_loss = max(worst_case_decision_loss, -position)
            required += worst_case_decision_loss
        return required

    def account_snapshot(self) -> List[dict]:
        rows = []
        for a in self.accounts.values():
            collateral = self._required_collateral(a)
            rows.append(
                {
                    "trader_id": a.trader_id,
                    "token_balance": round(a.token_balance, 4),
                    "locked_collateral": round(collateral, 4),
                    "available_balance": round(a.token_balance - collateral, 4),
                }
            )
        return rows

    def trader_incentive_snapshot(self) -> List[dict]:
        rows: List[dict] = []
        for account in self.accounts.values():
            expected_open_payout = 0.0
            for decision_id, branch_positions in account.positions.items():
                decision = self.decisions.get(decision_id)
                if decision is None:
                    continue
                if decision.state == DecisionState.RESOLVED:
                    continue
                probs = decision.probability_map()
                for option_id, shares in branch_positions.items():
                    expected_open_payout += shares * probs.get(option_id, 0.0)

            projected_balance = account.token_balance + expected_open_payout
            projected_pnl = projected_balance - account.initial_funding
            total_spent = account.gross_spent + account.fee_spent

            rows.append(
                {
                    "trader_id": account.trader_id,
                    "initial_funding": round(account.initial_funding, 4),
                    "token_balance": round(account.token_balance, 4),
                    "gross_spent": round(account.gross_spent, 4),
                    "fee_spent": round(account.fee_spent, 4),
                    "total_spent": round(total_spent, 4),
                    "realized_payout": round(account.realized_payout, 4),
                    "expected_open_payout": round(expected_open_payout, 4),
                    "projected_balance": round(projected_balance, 4),
                    "projected_pnl": round(projected_pnl, 4),
                }
            )

        rows.sort(key=lambda x: x["projected_pnl"], reverse=True)
        return rows

    def decision_snapshot(self, decision_id: str) -> dict:
        d = self.decisions[decision_id]
        winner = d.close_by_price_if_expired()
        if winner is not None:
            self.resolve_decision(decision_id=decision_id, winner_option_id=winner)
        probs = d.probability_map()
        twap = d.twap_map()
        n = len(d.branches)
        base = 1.0 / n

        options = []
        for branch in d.branches.values():
            p = probs[branch.option_id]
            net_success = branch.success_value - branch.implementation_cost - branch.risk_penalty
            net_failure = branch.failure_value - branch.implementation_cost - branch.risk_penalty
            ev = p * net_success + (1.0 - p) * net_failure
            downside = min(0.0, net_failure)
            confidence = max(0.0, (p - base) / (1.0 - base)) if n > 1 else 1.0

            passes = True
            fail_reasons: List[str] = []
            if ev < d.rule.min_expected_value:
                passes = False
                fail_reasons.append("EV below threshold")
            if p < d.rule.min_probability:
                passes = False
                fail_reasons.append("Probability below threshold")
            if confidence < d.rule.min_confidence:
                passes = False
                fail_reasons.append("Confidence below threshold")
            if d.rule.max_downside_abs is not None and abs(downside) > d.rule.max_downside_abs:
                passes = False
                fail_reasons.append("Downside exceeds limit")

            options.append(
                {
                    "option_id": branch.option_id,
                    "label": branch.label,
                    "p_success": round(p, 4),
                    "p_twap": round(twap[branch.option_id], 4),
                    "confidence": round(confidence, 4),
                    "expected_value": round(ev, 2),
                    "net_success": round(net_success, 2),
                    "net_failure": round(net_failure, 2),
                    "downside": round(downside, 2),
                    "shares": round(d.q[branch.option_id], 2),
                    "passes_rule": passes,
                    "fail_reasons": fail_reasons,
                }
            )

        ranked = sorted(options, key=lambda x: x["expected_value"], reverse=True)
        eligible = [o for o in ranked if o["passes_rule"]]

        status = RecommendationStatus.DEFER
        recommended_option_id: Optional[str] = None
        rationale: List[str] = []

        if eligible:
            pick = eligible[0]
            runner_up = eligible[1] if len(eligible) > 1 else None
            recommended_option_id = pick["option_id"]
            status = RecommendationStatus.RECOMMEND
            rationale.append("Top EV among policy-compliant branches")
            if runner_up and (pick["expected_value"] - runner_up["expected_value"]) <= d.rule.tie_margin:
                status = RecommendationStatus.ESCALATE
                rationale.append("EV lead within tie margin")
        else:
            rationale.append("No branch passes decision policy")

        return {
            "decision_id": d.decision_id,
            "title": d.title,
            "description": d.description,
            "use_case": d.use_case,
            "state": d.state.value,
            "resolved_option_id": d.resolved_option_id,
            "probability_sum": round(sum(probs.values()), 6),
            "seconds_remaining": round(d.seconds_remaining(), 2),
            "rule": {
                "min_expected_value": d.rule.min_expected_value,
                "min_probability": d.rule.min_probability,
                "min_confidence": d.rule.min_confidence,
                "max_downside_abs": d.rule.max_downside_abs,
                "tie_margin": d.rule.tie_margin,
            },
            "status": status.value,
            "recommended_option_id": recommended_option_id,
            "rationale": rationale,
            "options": ranked,
        }

    def all_decision_snapshots(self) -> List[dict]:
        return [self.decision_snapshot(decision_id) for decision_id in self.decisions]

    def enterprise_decision_summary(self) -> dict:
        decisions = self.all_decision_snapshots()
        recommended = [d for d in decisions if d["status"] == RecommendationStatus.RECOMMEND.value]
        escalated = [d for d in decisions if d["status"] == RecommendationStatus.ESCALATE.value]

        total_ev = 0.0
        for d in recommended:
            chosen = next((o for o in d["options"] if o["option_id"] == d["recommended_option_id"]), None)
            if chosen:
                total_ev += chosen["expected_value"]

        return {
            "decision_count": len(decisions),
            "recommended_count": len(recommended),
            "escalated_count": len(escalated),
            "portfolio_expected_value": round(total_ev, 2),
        }
