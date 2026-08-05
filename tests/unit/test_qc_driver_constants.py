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
RESEARCH = ROOT / "lean" / "research"

# driver -> (keys emitted per leg, fixed keys) for the L-019 headroom check
DRIVERS = {
    "qc_quote_data_smoke.py": (3, 6),     # _REG, _EXT, _EARLY
    "qc_quote_depth_probe.py": (3, 6),    # one per PROBES row, 3 rows per micro
}
UNIVERSE = {"MES", "MNQ", "M2K", "MYM", "ZT", "ZF", "ZN", "ZB"}


@pytest.fixture(scope="module")
def specs():
    return load_contract_specs(ROOT / "config" / "instruments.yaml")


def _legs(driver: str) -> dict[str, float]:
    """Pull the LEGS table out of a driver's source without executing it.

    The two drivers spell LEGS differently — a list of tuples in one, a dict of
    tuples in the other — so both shapes are handled rather than forcing them
    to converge, which would mean editing a file that is banked evidence.
    """
    tree = ast.parse((RESEARCH / driver).read_text(encoding="utf-8"))
    for node in tree.body:
        if not (isinstance(node, ast.Assign)
                and any(getattr(t, "id", None) == "LEGS" for t in node.targets)):
            continue
        v = node.value
        if isinstance(v, ast.Dict):      # {leg: (market, tick)}
            return {k.value: ast.literal_eval(val.elts[1])
                    for k, val in zip(v.keys, v.values)}
        return {e.elts[0].value: ast.literal_eval(e.elts[2])
                for e in v.elts}         # [(leg, market, tick, ...)]
    raise AssertionError(f"LEGS table not found in {driver}")


@pytest.mark.parametrize("driver", sorted(DRIVERS))
def test_driver_exists_and_parses(driver):
    path = RESEARCH / driver
    assert path.exists()
    ast.parse(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("driver", sorted(DRIVERS))
def test_driver_tick_sizes_match_verified_config(driver, specs):
    legs = _legs(driver)
    assert legs, f"{driver}: LEGS table is empty"
    for leg, tick in legs.items():
        assert leg in specs, f"{leg} is not in the locked universe"
        assert tick == pytest.approx(specs[leg].tick_size, rel=0, abs=1e-12), (
            f"{driver} hardcodes {leg} tick_size={tick} but "
            f"config/instruments.yaml (A-003 CME-verified) says "
            f"{specs[leg].tick_size}. Every spread-in-ticks figure from this "
            f"driver would be wrong by {specs[leg].tick_size / tick:.4f}x.")


@pytest.mark.parametrize("driver", sorted(DRIVERS))
def test_driver_legs_are_in_locked_universe(driver):
    # CLAUDE.md hard gate 5. A smoke test is still bound by the locked universe.
    assert set(_legs(driver)) <= UNIVERSE


@pytest.mark.parametrize("driver", sorted(DRIVERS))
def test_driver_emission_stays_under_the_l019_cap(driver):
    """L-019 (BINDING): emissions above ~57 keys silently lose blocks. Assert
    the design cannot creep past the cap as legs or probes are added."""
    per_leg, fixed = DRIVERS[driver]
    assert len(_legs(driver)) * per_leg + fixed <= 57
