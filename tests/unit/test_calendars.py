"""CME holiday calendar tests, including the ZNM21 Memorial-Day roll that
motivated the `holidays` parameter (validation report 01 §6)."""

from datetime import date

import pytest

from spread_research.calendars import (
    JUNETEENTH_FIRST_YEAR, cme_holidays, cme_holidays_year, easter_sunday,
    good_friday,
)
from spread_research.roll_adjustment import (
    index_roll_schedule, treasury_roll_schedule,
)


@pytest.mark.parametrize("year,expected", [
    (2019, date(2019, 4, 21)), (2021, date(2021, 4, 4)),
    (2024, date(2024, 3, 31)), (2026, date(2026, 4, 5)),
])
def test_easter_known_dates(year, expected):
    assert easter_sunday(year) == expected


def test_good_friday_is_two_days_before_easter():
    for y in range(2018, 2028):
        gf = good_friday(y)
        assert gf.weekday() == 4
        assert (easter_sunday(y) - gf).days == 2


@pytest.mark.parametrize("d", [
    date(2021, 5, 31),   # Memorial Day — the ZNM21 case
    date(2024, 1, 15),   # MLK
    date(2025, 2, 17),   # Presidents' Day
    date(2025, 9, 1),    # Labor Day
    date(2026, 11, 26),  # Thanksgiving
    date(2020, 7, 3),    # Jul 4 2020 was a Saturday -> observed Friday
    date(2022, 12, 26),  # Dec 25 2022 was a Sunday -> observed Monday
    date(2021, 12, 31),  # Jan 1 2022 was a Saturday -> observed Friday
    date(2022, 6, 20),   # Juneteenth 2022 (Sunday) -> observed Monday
])
def test_known_full_closures_present(d):
    assert d in cme_holidays()


def test_juneteenth_not_observed_before_first_year():
    for y in range(2019, JUNETEENTH_FIRST_YEAR):
        assert not any(h.month == 6 and h.day in (18, 19, 20)
                       for h in cme_holidays_year(y))
    assert any(h.month == 6 for h in cme_holidays_year(JUNETEENTH_FIRST_YEAR))


def test_no_weekend_holidays_survive_observation():
    # Observed dates must be weekdays; only weekday closures can move a roll.
    for h in cme_holidays():
        assert h.weekday() < 5, h


def test_holiday_set_spans_requested_years_only():
    hs = cme_holidays(2020, 2021)
    assert {h.year for h in hs} == {2020, 2021}
    with pytest.raises(ValueError):
        cme_holidays(2025, 2024)


# --- integration with the roll schedules -----------------------------------

ZN_CODES = ["ZNH21", "ZNM21", "ZNU21"]


def test_treasury_roll_moves_off_memorial_day():
    """The roll OUT OF ZNM21 (June delivery) is scheduled on the last business
    day of May 2021 = Monday 2021-05-31 = Memorial Day. With holidays the
    splice must land on Friday 2021-05-28."""
    naive = treasury_roll_schedule(ZN_CODES, tz=None)
    row = naive.loc[naive["from_contract"] == "ZNM21"].iloc[0]
    assert row["timestamp"].date() == date(2021, 5, 31)

    fixed = treasury_roll_schedule(ZN_CODES, tz=None, holidays=cme_holidays())
    row = fixed.loc[fixed["from_contract"] == "ZNM21"].iloc[0]
    assert row["timestamp"].date() == date(2021, 5, 28)
    assert row["timestamp"].date().weekday() == 4


def test_all_scheduled_rolls_avoid_holidays_and_weekends():
    hol = cme_holidays()
    index_codes = [f"{r}{m}{y}" for r in ("MES", "MYM")
                   for y in range(19, 27) for m in ("H", "M", "U", "Z")]
    tsy_codes = [f"ZN{m}{y}" for y in range(19, 27) for m in ("H", "M", "U", "Z")]
    for codes, gen in ((index_codes[:32], index_roll_schedule),
                       (tsy_codes, treasury_roll_schedule)):
        sched = gen(sorted(set(codes)), tz=None, holidays=hol)
        for ts in sched["timestamp"]:
            assert ts.date().weekday() < 5, ts
            assert ts.date() not in hol, ts


def test_index_rolls_unaffected_by_holidays_in_this_window():
    """Index rolls sit at expiry-8d, which is always the Thursday of the prior
    week for a 3rd-Friday expiry — never a CME full-closure day in 2019-2026.
    Recorded so the report can state the holiday list is inert for MES/MYM
    rather than implying it fixed something."""
    codes = [f"MES{m}{y}" for y in range(19, 27) for m in ("H", "M", "U", "Z")]
    plain = index_roll_schedule(codes, tz=None)
    with_hol = index_roll_schedule(codes, tz=None, holidays=cme_holidays())
    assert list(plain["timestamp"]) == list(with_hol["timestamp"])
    assert all(ts.date().weekday() == 3 for ts in plain["timestamp"])
