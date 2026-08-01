from pathlib import Path

import pytest

from spread_research.contract_metadata import load_contract_specs
from spread_research.costs import CostModel
from spread_research.position_sizing import size_spread

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def specs():
    return load_contract_specs(ROOT / "config" / "instruments.yaml")


def test_specs_load_and_sanity(specs):
    assert set(specs) == {"MES", "MNQ", "M2K", "MYM", "ZT", "ZF", "ZN", "ZB"}
    # spot-check verified values
    assert specs["MES"].tick_value == 1.25
    assert specs["MNQ"].multiplier == 2.0
    assert specs["ZN"].tick_value == 15.625
    assert specs["ZT"].face_value == 200000
    # internal consistency enforced for all
    for s in specs.values():
        assert abs(s.tick_size * s.multiplier - s.tick_value) < 1e-9


def test_notional_arithmetic(specs):
    # MES at 5000 -> $25,000 notional
    assert specs["MES"].notional(5000.0) == 25000.0
    # ZN at 110 points -> $110,000
    assert specs["ZN"].notional(110.0) == 110000.0


def test_cost_model_known_arithmetic(specs):
    cm = CostModel.from_config(ROOT / "config" / "cost_assumptions.yaml", specs)
    # MES base scenario: commission 0.62 + half-spread 0.625 + 1 tick slip 1.25 = 2.495/side
    assert abs(cm.fill_cost("MES", 1, "base") - 2.495) < 1e-9
    assert abs(cm.round_trip_cost("MES", 1, "base") - 4.99) < 1e-9
    # stressed adds one more tick per side
    assert cm.fill_cost("MES", 1, "stressed") > cm.fill_cost("MES", 1, "base")
    # spread round trip = both legs
    both = cm.spread_round_trip_cost({"MES": 1, "MNQ": 1}, "base")
    assert abs(both - (cm.round_trip_cost("MES", 1, "base")
                       + cm.round_trip_cost("MNQ", 1, "base"))) < 1e-9


def test_size_spread_minimizes_rounding(specs):
    # MES ~5000 ($25k/contract), MNQ ~18000 ($36k/contract):
    # beta_contracts = 25/36 ≈ 0.694 → 1:1 at ca=1 is poor; search should improve it
    sz = size_spread(specs["MES"], specs["MNQ"], 5000.0, 18000.0,
                     beta_contracts=25.0 / 36.0, max_contracts_per_leg=10)
    assert 1 <= sz.contracts_a <= 10 and 1 <= sz.contracts_b <= 10
    naive_err = abs(25000.0 - 36000.0) / (25000.0 + 36000.0)
    assert sz.rounding_error_pct < naive_err
    # reported net must equal recomputed net
    assert abs(sz.net_notional - (sz.notional_a - sz.notional_b)) < 1e-6


def test_size_spread_respects_caps(specs):
    sz = size_spread(specs["ZT"], specs["ZN"], 103.0, 112.0, beta_contracts=2.0,
                     max_contracts_per_leg=3)
    assert sz.contracts_a <= 3 and sz.contracts_b <= 3
