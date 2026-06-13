import uuid
from typing import List, Dict, Set, Tuple
from datetime import datetime

from karsa.allocation.domain.model.allocation import RiskAllocation
from karsa.portfolio.domain.model.portfolio import (
    Portfolio, TargetPosition, PortfolioTargetSnapshot, PortfolioDecision,
    TradeIntent, ExposureMetrics, CashTarget, RegimeState,
    AllocationPortfolioMapping, DriftMetrics, RebalanceResult
)

class RebalancingEngine:
    def __init__(self):
        pass

    def evaluate_allocations(
        self, 
        portfolio_id: str, 
        allocations: List[RiskAllocation], 
        mappings: List[AllocationPortfolioMapping]
    ) -> List[RiskAllocation]:
        # Filter allocations that apply to this portfolio via the N:M mapping
        active_allocation_ids = {m.allocation_id for m in mappings if m.portfolio_id == portfolio_id and m.active}
        return [a for a in allocations if a.allocation_id in active_allocation_ids]

    def calculate_exposure(self, portfolio: Portfolio) -> ExposureMetrics:
        # Purity check: calculate based on inputs without mutating
        total_market_value = sum(p.market_value for p in portfolio.positions)
        if total_market_value == 0:
            return ExposureMetrics(0.0, 0.0, 0.0, 1.0, 0.0)

        # Simplified placeholder math for architecture test
        # In reality, this evaluates longs vs shorts, etc.
        gross_exposure = 1.0
        net_exposure = 1.0
        concentration = max((p.market_value / total_market_value for p in portfolio.positions), default=0.0)
        cash_ratio = 0.0
        leverage_ratio = 1.0
        
        return ExposureMetrics(
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            concentration_exposure=concentration,
            cash_ratio=cash_ratio,
            leverage_ratio=leverage_ratio
        )

    def evaluate_constraints(
        self, 
        exposure: ExposureMetrics, 
        cash_target: CashTarget, 
        buying_power: float
    ) -> Tuple[bool, List[str]]:
        violations = []
        if exposure.cash_ratio < cash_target.target_cash_percentage:
            violations.append(f"Cash ratio {exposure.cash_ratio} below target {cash_target.target_cash_percentage}")
            
        if exposure.leverage_ratio > 2.0: # Arbitrary portfolio limit
            violations.append(f"Leverage {exposure.leverage_ratio} exceeds max limit")
            
        return len(violations) == 0, violations

    def calculate_drift(
        self, 
        portfolio: Portfolio, 
        target_positions: frozenset[TargetPosition]
    ) -> List[DriftMetrics]:
        total_market_value = sum(p.market_value for p in portfolio.positions)
        
        actual_weights = {}
        if total_market_value > 0:
            for p in portfolio.positions:
                actual_weights[p.symbol] = p.market_value / total_market_value

        drifts = []
        target_map = {t.symbol: t.target_weight for t in target_positions}
        
        all_symbols = sorted(list(set(actual_weights.keys()).union(set(target_map.keys()))))
        for sym in all_symbols:
            t_w = target_map.get(sym, 0.0)
            a_w = actual_weights.get(sym, 0.0)
            drifts.append(DriftMetrics(
                symbol=sym,
                target_weight=t_w,
                actual_weight=a_w
            ))
            
        return drifts

    def generate_trade_intents(
        self, 
        portfolio_id: str, 
        snapshot_id: str, 
        drifts: List[DriftMetrics]
    ) -> List[TradeIntent]:
        intents = []
        for d in drifts:
            if d.drift_percentage > 0.0:
                action = "BUY" if d.target_weight > d.actual_weight else "SELL"
                intents.append(TradeIntent(
                    intent_id=str(uuid.uuid4()),
                    portfolio_id=portfolio_id,
                    snapshot_id=snapshot_id,
                    symbol=d.symbol,
                    action=action,
                    target_weight=d.target_weight,
                    reason=f"Drift adjustment of {d.drift_percentage}"
                ))
        # Ensure deterministic sort for tests
        return sorted(intents, key=lambda x: x.symbol)

    def rebalance(
        self, 
        portfolio: Portfolio, 
        allocations: List[RiskAllocation], 
        mappings: List[AllocationPortfolioMapping], 
        cash_target: CashTarget, 
        buying_power: float, 
        regime: RegimeState
    ) -> RebalanceResult:
        
        # 1. Evaluate relevant allocations
        relevant_allocations = self.evaluate_allocations(portfolio.portfolio_id, allocations, mappings)
        
        # 2. Exposure evaluation
        exposure = self.calculate_exposure(portfolio)
        
        # 3. Constraint evaluation
        is_valid, violations = self.evaluate_constraints(exposure, cash_target, buying_power)
        
        # 4. Generate Target Snapshot (Deterministic)
        # Using a deterministic algorithm based on inputs (simplified for arch proof)
        target_symbols = {}
        if relevant_allocations:
            # Distribute 1.0 - cash_target equally among all allocations' theses
            # This is a stub for complex optimizer math
            weight_per_thesis = (1.0 - cash_target.target_cash_percentage) / len(relevant_allocations)
            for a in relevant_allocations:
                # Assuming thesis ID maps 1:1 to a symbol representation for test simplicity
                sym = f"SYM_{a.thesis_id}"
                target_symbols[sym] = weight_per_thesis
                
        targets = frozenset([TargetPosition(sym, w) for sym, w in target_symbols.items()])
        
        import hashlib
        import json

        # Ensure ID generation is deterministic based on hash of targets and portfolio
        target_list = sorted([{"symbol": sym, "weight": w} for sym, w in target_symbols.items()], key=lambda x: x["symbol"])
        target_json = json.dumps(target_list, separators=(",", ":"))
        
        hasher = hashlib.sha256()
        hasher.update(target_json.encode('utf-8'))
        deterministic_hash = hasher.hexdigest()[:16]
        
        snapshot_id = f"SNAP_{portfolio.portfolio_id}_{deterministic_hash}"
        
        snapshot = PortfolioTargetSnapshot(
            snapshot_id=snapshot_id,
            portfolio_id=portfolio.portfolio_id,
            version=1,
            target_positions=targets
        )
        
        # 5. Calculate Drift
        drifts = self.calculate_drift(portfolio, targets)
        
        # 6. Generate Trade Intents
        intents = self.generate_trade_intents(portfolio.portfolio_id, snapshot_id, drifts)
        
        # 7. Generate Decision
        decision_id = f"DEC_{portfolio.portfolio_id}_{deterministic_hash}"
        decision = PortfolioDecision(
            decision_id=decision_id,
            portfolio_id=portfolio.portfolio_id,
            target_snapshot_id=snapshot_id,
            timestamp=datetime.utcnow(),
            assumptions={"regime_trend": regime.trend, "regime_volatility": regime.volatility},
            constraints={"buying_power": str(buying_power), "violations": str(violations)},
            expected_outcome={"target_symbols": str(sorted(list(target_symbols.keys())))},
            alternatives_considered=[{"option": "do nothing"}],
            decision_reasoning="Periodic rebalance optimization"
        )
        
        return RebalanceResult(
            portfolio_id=portfolio.portfolio_id,
            decision=decision,
            target_snapshot=snapshot,
            trade_intents=intents,
            drift_metrics=drifts,
            exposure_metrics=exposure
        )
