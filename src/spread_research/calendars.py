"""CME full-closure holidays for the locked universe (equity-index micros on
CME/CBOT and U.S. Treasury futures on CBOT).

Why this exists: `roll_adjustment.index_roll_schedule` /
`treasury_roll_schedule` snap a roll date back to the previous business day and
accept a `holidays` set. Without it a scheduled roll can land on an exchange
holiday, so the splice spans an abnormally long quiet boundary and trips the
conservative 5 bp floor in `splice_audit` (observed: the ZNM21 roll scheduled
on 2021-05-31, Memorial Day — validation report 01 §6).

Scope and honesty notes:

- These are **full-closure** days for the products in the locked universe.
  CME runs *shortened* sessions around several of them (e.g. the 1:00 p.m. ET
  close before Thanksgiving/Christmas/July 4). Early closes are deliberately
  NOT in this set: bars exist on those days, so a splice is still measurable,
  and excluding them would move rolls for no data reason. If a future audit
  shows early closes distorting splices, add a separate `early_closes()`.
- Good Friday: equity-index futures are closed; Treasury futures trade a
  shortened session in years when the exchange schedules one (a March/April
  employment-report Friday). Treated as a closure here — conservative, and no
  roll date in this project's window falls near Easter, so it is inert.
- Weekend-observed rules are included for completeness, but the schedule
  generators already step back over Saturdays and Sundays, so only *weekday*
  closures can change a roll date.
- 2025-01-09 (National Day of Mourning, President Carter) was a modified
  CME schedule, not a uniform full closure, and is not a roll date under
  either generator in this project's window. It is documented here and
  intentionally excluded rather than guessed at.

[ESTABLISHED] The rule set below is the standard CME Group holiday calendar
(U.S. federal holidays plus Good Friday); it is derived from published rules,
not scraped, because cmegroup.com blocks scripted fetches (L-002 history).
"""

from __future__ import annotations

from datetime import date, timedelta

# Juneteenth became a federal holiday in June 2021; CME Group first observed it
# as a full holiday in 2022.
JUNETEENTH_FIRST_YEAR = 2022


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """n-th `weekday` (Mon=0) of a month, 1-indexed."""
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(days=7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    nxt = date(year + (month == 12), (month % 12) + 1, 1)
    d = nxt - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d: date) -> date:
    """U.S. federal observation rule: Saturday -> preceding Friday,
    Sunday -> following Monday."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def easter_sunday(year: int) -> date:
    """Anonymous Gregorian computus."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    month, day = divmod(h + ll - 7 * m + 114, 31)
    return date(year, month, day + 1)


def good_friday(year: int) -> date:
    return easter_sunday(year) - timedelta(days=2)


def cme_holidays_year(year: int) -> set[date]:
    """Full-closure days for CME/CBOT equity-index and Treasury futures."""
    out = {
        _observed(date(year, 1, 1)),                 # New Year's Day
        _nth_weekday(year, 1, 0, 3),                 # MLK Jr. Day
        _nth_weekday(year, 2, 0, 3),                 # Presidents' Day
        good_friday(year),
        _last_weekday(year, 5, 0),                   # Memorial Day
        _observed(date(year, 7, 4)),                 # Independence Day
        _nth_weekday(year, 9, 0, 1),                 # Labor Day
        _nth_weekday(year, 11, 3, 4),                # Thanksgiving
        _observed(date(year, 12, 25)),               # Christmas
    }
    if year >= JUNETEENTH_FIRST_YEAR:
        out.add(_observed(date(year, 6, 19)))
    return out


def cme_holidays(start_year: int = 2018, end_year: int = 2027) -> frozenset[date]:
    """Holiday set spanning the research window with a year of margin on each
    side. Pass straight into `index_roll_schedule(..., holidays=...)` /
    `treasury_roll_schedule(..., holidays=...)`."""
    if end_year < start_year:
        raise ValueError(f"end_year {end_year} precedes start_year {start_year}")
    days: set[date] = set()
    for y in range(start_year, end_year + 1):
        days |= cme_holidays_year(y)
    return frozenset(days)
