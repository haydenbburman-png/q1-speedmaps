"""Q2 Parklands tests against trimmed copies of real thedogs.com.au pages.

tests/pages/:
  2026-10-11_q2_day.html        meetings grid: Q2 Parklands + Healesville rows
  2026-10-11_q2_R08_*.html      520m, race already run. Short form for Bionic Bill (box 7; his R8 win
                                is only inside "MOST RECENT 2 WINS"), Bagless Brute (QTT/QST/QOT runs)
                                and reserve He's Paranormal (scratched; ran in R6 the same day)
  2026-09-24_q2_R05_*.html      710m. Midnight Queen (710 + 600 + QOT 642 runs), Roma Keeping
                                (no 710 run: estimated), Arthur Tango (4 x 710)
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from speedmap import config, model, parse, report  # noqa: E402

PAGES = Path(__file__).resolve().parent / "pages"
Q1, Q2 = config.TRACKS


def _page(name: str) -> str:
    return (PAGES / f"{name}.html").read_text(encoding="utf-8")


def _race(day: str, n: int, url: str) -> parse.Race:
    race = parse.Race(n, "", url)
    html = _page(f"{day}_q2_R{n:02d}_result")
    parse.parse_race_info(html, race)
    race.runners = parse.parse_field(html)
    return race


def _r8() -> parse.Race:
    mt = parse.find_meetings(_page("2026-10-11_q2_day"), "2026-10-11", Q2.slug_match)[0]
    race = next(r for r in mt.races if r.number == 8)
    html = _page("2026-10-11_q2_R08_result")
    parse.parse_race_info(html, race)
    race.runners = parse.parse_field(html)
    return race


def test_q2_day_page():
    day = _page("2026-10-11_q2_day")
    mts = parse.find_meetings(day, "2026-10-11", Q2.slug_match)
    assert [(m.slug, len(m.races)) for m in mts] == [("ladbrokes-q2-parklands", 11)]
    assert parse.find_meetings(day, "2026-10-11", Q1.slug_match) == []   # Healesville row not picked up


def test_q2_race_and_track_codes():
    race = _r8()
    assert race.dist == 520 and race.grade == "5th Grade" and race.finished and race.time == "19:34"
    starters = {r.box: r.name for r in race.runners if not r.scratched and not r.reserve}
    assert sorted(starters) == [1, 2, 3, 4, 5, 6, 7, 8] and starters[7] == "Bionic Bill"
    assert sorted(r.box for r in race.runners if r.scratched) == [9, 10]

    n = parse.attach_runs(_page("2026-10-11_q2_R08_shortform"), race.runners, before=date(2026, 10, 11))
    by = {r.name: r for r in race.runners}
    assert n == 14                                     # 5 + 5 + 4: He's Paranormal's same-day R6 run dropped
    assert all(x.date.date() < date(2026, 10, 11) for r in race.runners for x in r.runs)
    assert by["Bionic Bill"].runs[0].date.date() == date(2026, 10, 4)   # his R8 win (wins box) never read

    q2 = {d.runner.name: d for d in model.build_map(race, Q2.codes).dogs}
    assert q2["Bionic Bill"].n_sec == 4 and q2["Bionic Bill"].conf == "high"   # QTT 520 only, not QOT 457
    assert q2["Bagless Brute"].n_sec == 1                                     # not QST 350 / QOT 457
    q1 = {d.runner.name: d for d in model.build_map(race, Q1.codes).dogs}
    assert q1["Bionic Bill"].n_sec == 0 and q1["Bagless Brute"].n_sec == 0     # QTT never counts for Q1


def test_q2_710m_fallback(tmp_path):
    race = _race("2026-09-24", 5,
                 "https://www.thedogs.com.au/racing/ladbrokes-q2-parklands/2026-09-24/5/engineering-by-stp-consultants")
    assert race.dist == 710 and race.grade == "5th/6th Grade"
    assert sorted(r.box for r in race.runners if not r.scratched and not r.reserve) == [1, 2, 3, 4, 5, 6, 7, 8]
    parse.attach_runs(_page("2026-09-24_q2_R05_shortform"), race.runners, before=date(2026, 9, 24))

    rm = model.build_map(race, Q2.codes)
    by = {d.runner.name: d for d in rm.dogs}
    mq = by["Midnight Queen"]
    assert mq.n_sec == 3 and abs(mq.est_sec - (0.7 * ((4.75 + 4.8 * 0.85 + 4.6 * 0.85 ** 2) / (1 + 0.85 + 0.85 ** 2))
                                                + 0.3 * 4.6)) < 1e-9   # 710 splits only, not 600/642
    assert by["Arthur Tango"].n_sec == 4

    roma = by["Roma Keeping"]                                  # only 600m and QOT runs: estimated
    assert roma.conf == "low" and roma.n_sec == 0 and "no splits here" in roma.basis
    assert any(n.startswith("Estimated") and "Roma Keeping (5)" in n for n in rm.notes)

    page = report.build(Q2.name, "2026-09-24", [rm], {}, tmp_path / "index.html").read_text()
    assert "Q2 Parklands — Speedmaps" in page
    assert "<span class='conf low'>estimated</span>" in page
