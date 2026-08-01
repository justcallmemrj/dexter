"""Transaction-cost model (mandate §4.3 / notebook 07).

Deliberately conservative: cost of a fill = commission + half-spread + slippage,
all per side per contract, expressed in USD via verified tick values. The
acceptance rule (config/cost_assumptions.yaml) requires survival under the
'stressed' scenario.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .contract_metadata import ContractSpec


@dataclass(frozen=True)
class LegCost:
    symbol: str
    commission_per_side: float      # USD, all-in
    spread_ticks: float             # full quoted spread in ticks
    tick_value: float               # USD per tick


class CostModel:
    """Per-fill and per-round-trip cost calculator."""

    def __init__(self, legs: dict[str, LegCost],
                 slippage_scenarios: dict[str, float]):
        self.legs = legs
        self.slippage_scenarios = slippage_scenarios

    @classmethod
    def from_config(cls, cost_yaml: str | Path,
                    specs: dict[str, ContractSpec]) -> "CostModel":
        raw = yaml.safe_load(Path(cost_yaml).read_text())
        legs = {}
        for sym, comm in raw["commissions"].items():
            if sym not in specs:
                continue
            legs[sym] = LegCost(
                symbol=sym,
                commission_per_side=float(comm),
                spread_ticks=float(raw["spread_assumptions_ticks"][sym]),
                tick_value=specs[sym].tick_value,
            )
        return cls(legs, {k: float(v) for k, v in
                          raw["slippage_scenarios_ticks_per_leg"].items()})

    def fill_cost(self, symbol: str, contracts: int, scenario: str = "base",
                  aggressive: bool = True) -> float:
        """USD cost of one fill: commission + (half-spread if aggressive) + slippage."""
        leg = self.legs[symbol]
        slip_ticks = self.slippage_scenarios[scenario]
        spread_cost = (leg.spread_ticks / 2.0) * leg.tick_value if aggressive else 0.0
        return abs(contracts) * (leg.commission_per_side
                                 + spread_cost
                                 + slip_ticks * leg.tick_value)

    def round_trip_cost(self, symbol: str, contracts: int,
                        scenario: str = "base") -> float:
        return 2.0 * self.fill_cost(symbol, contracts, scenario)

    def spread_round_trip_cost(self, contracts_by_symbol: dict[str, int],
                               scenario: str = "base") -> float:
        """Total USD cost of entering AND exiting a multi-leg spread."""
        return sum(self.round_trip_cost(sym, n, scenario)
                   for sym, n in contracts_by_symbol.items())
