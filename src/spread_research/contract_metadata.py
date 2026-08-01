"""Contract metadata: load verified specs from config/instruments.yaml and give
notebooks/backtester one place for tick arithmetic and notional calculations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ContractSpec:
    symbol: str
    name: str
    exchange: str
    asset_class: str          # "equity_index" | "treasury"
    multiplier: float         # $/point for index; point_value for treasuries
    tick_size: float          # in price/index points
    tick_value: float         # USD per tick per contract
    face_value: float | None = None

    def notional(self, price: float, contracts: int = 1) -> float:
        """Gross notional in USD at a given quoted price."""
        return abs(contracts) * price * self.multiplier

    def round_to_tick(self, price: float) -> float:
        return round(price / self.tick_size) * self.tick_size

    def ticks_to_dollars(self, ticks: float, contracts: int = 1) -> float:
        return ticks * self.tick_value * abs(contracts)

    def points_to_dollars(self, points: float, contracts: int = 1) -> float:
        return points * self.multiplier * abs(contracts)


def load_contract_specs(instruments_yaml: str | Path) -> dict[str, ContractSpec]:
    """Parse config/instruments.yaml into ContractSpec objects."""
    raw = yaml.safe_load(Path(instruments_yaml).read_text())
    specs: dict[str, ContractSpec] = {}
    for sym, d in raw.get("equity_index_futures", {}).items():
        specs[sym] = ContractSpec(
            symbol=sym, name=d["name"], exchange=d["exchange"],
            asset_class="equity_index", multiplier=float(d["multiplier"]),
            tick_size=float(d["tick_size"]), tick_value=float(d["tick_value"]),
        )
    for sym, d in raw.get("treasury_futures", {}).items():
        specs[sym] = ContractSpec(
            symbol=sym, name=d["name"], exchange=d["exchange"],
            asset_class="treasury", multiplier=float(d["point_value"]),
            tick_size=float(d["tick_size_points"]), tick_value=float(d["tick_value"]),
            face_value=float(d["face_value"]),
        )
    _sanity_check(specs)
    return specs


def _sanity_check(specs: dict[str, ContractSpec]) -> None:
    """tick_value must equal tick_size * multiplier — catches transcription errors
    in the YAML (this exact class of error appeared in one external source during
    spec verification; see logs/research_decisions.md D-003)."""
    for s in specs.values():
        implied = s.tick_size * s.multiplier
        if abs(implied - s.tick_value) > 1e-9:
            raise ValueError(
                f"{s.symbol}: tick_size*multiplier={implied} != tick_value={s.tick_value}"
            )
