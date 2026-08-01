"""Position sizing: convert a hedge ratio into integer contract counts and
quantify the directional exposure created by rounding (mandate §4.3)."""

from __future__ import annotations

from dataclasses import dataclass

from .contract_metadata import ContractSpec


@dataclass(frozen=True)
class SpreadSize:
    contracts_a: int
    contracts_b: int
    notional_a: float
    notional_b: float
    gross_notional: float
    net_notional: float           # signed residual directional exposure, USD
    rounding_error_pct: float     # |net| / gross — the cost of integer contracts


def size_spread(spec_a: ContractSpec, spec_b: ContractSpec,
                price_a: float, price_b: float, beta_contracts: float,
                base_contracts_a: int = 1,
                max_contracts_per_leg: int = 10) -> SpreadSize:
    """Given a CONTRACT-space hedge ratio (contracts of B per contract of A),
    choose integer contract counts minimizing |net notional|, subject to leg caps.

    Searches contracts_a in [1, max] and rounds contracts_b both ways, keeping the
    combination with the smallest relative rounding error. Small accounts trading
    1-lot micros can see material rounding error — that is a finding to report,
    not to hide.
    """
    best: SpreadSize | None = None
    for ca in range(base_contracts_a, max_contracts_per_leg + 1):
        target_b = beta_contracts * ca
        for cb in {int(target_b), int(target_b) + 1}:
            if cb < 1 or cb > max_contracts_per_leg:
                continue
            na = spec_a.notional(price_a, ca)
            nb = spec_b.notional(price_b, cb)
            gross = na + nb
            net = na - nb
            err = abs(net) / gross if gross > 0 else float("inf")
            cand = SpreadSize(ca, cb, na, nb, gross, net, err)
            if best is None or cand.rounding_error_pct < best.rounding_error_pct:
                best = cand
    if best is None:
        raise ValueError("no feasible sizing within contract caps")
    return best
