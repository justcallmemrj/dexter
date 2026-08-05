"""QC research drivers hardcode contract constants, because they run on
QuantConnect where config/ is not available. That makes them silently
driftable: nothing in the normal test run touches them, and a stale tick size
does not raise — it just scales every derived number.

`qc_quote_data_smoke.py` divides the measured bid-ask spread by a hardcoded
tick size to express it in ticks, and the whole point of that run is to test
A-008's "1 tick" against reality. A wrong constant there would produce a
confident, wrong answer to the program's binding cost question.

These drivers cannot be imported locally (they `from AlgorithmImports import *`),
so the constants are read out of the source with `ast` and compared against the
CME-verified specs in config/instruments.yaml (A-003).
"""

import ast
from pathlib import Path

import pytest

from spread_research.contract_metadata import load_contract_specs

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / "lean" / "research" / "qc_quote_data_smoke.py"


@pytest.fixture(scope="module")
def specs():
    return load_contract_specs(ROOT / "config" / "instruments.yaml")


@pytest.fixture(scope="module")
def legs():
    """Pull the LEGS table out of the driver source without executing it."""
    tree = ast.parse(DRIVER.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "LEGS" for t in node.targets):
            out = {}
            for elt in node.value.elts:
                leg = elt.elts[0].value
                out[leg] = ast.literal_eval(elt.elts[2])
            return out
    raise AssertionError("LEGS table not found in qc_quote_data_smoke.py")


def test_driver_exists_and_parses():
    assert DRIVER.exists()
    ast.parse(DRIVER.read_text(encoding="utf-8"))


def test_quote_smoke_tick_sizes_match_verified_config(legs, specs):
    assert legs, "LEGS table is empty"
    for leg, tick in legs.items():
        assert leg in specs, f"{leg} is not in the locked universe"
        assert tick == pytest.approx(specs[leg].tick_size, rel=0, abs=1e-12), (
            f"{leg}: driver hardcodes tick_size={tick} but config/instruments.yaml "
            f"(A-003 CME-verified) says {specs[leg].tick_size}. Every "
            f"spread-in-ticks figure from this driver would be wrong by "
            f"{specs[leg].tick_size / tick:.4f}x.")


def test_quote_smoke_legs_are_in_locked_universe(legs):
    # CLAUDE.md hard gate 5. A smoke test is still bound by the locked universe.
    assert set(legs) <= {"MES", "MNQ", "M2K", "MYM", "ZT", "ZF", "ZN", "ZB"}


def test_quote_smoke_emission_stays_under_the_l019_cap(legs):
    """L-019 (BINDING): emissions above ~57 keys silently lose blocks. This
    driver emits 3 keys per leg plus a small fixed set; assert the design
    cannot creep past the cap as legs are added."""
    per_leg = 3                      # _REG, _EXT, _EARLY
    fixed = 6                        # API, VERDICT, KEYS + failure headroom
    assert len(legs) * per_leg + fixed <= 57
