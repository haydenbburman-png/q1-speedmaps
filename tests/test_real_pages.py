"""Parsing tests against trimmed copies of real thedogs.com.au pages (Q1 Lakeside, 13 Oct 2026).

tests/pages/ holds the real markup with navigation, ads and scripts stripped:
  day.html          meetings grid row for Q1 (R1/R2 links show results, e.g. "2 8 6 9")
  R11_field.html    Field & Form: one <tbody> per runner, rugs as <sprite-svg name="rug_N">,
                    box 4 scratched, reserve 9 "(into box 4)", reserve 10 scratched
  R11_shortform.html  Short Form for boxes 1, 4 (scratched) and reserve 9, incl. "MOST RECENT 2 WINS"
  R01_result.html   race already run: results table, reserves "(from box N)", 4 scratched
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from speedmap import model, parse  # noqa: E402

PAGES = Path(__file__).resolve().parent / "pages"
DATE = "2026-10-13"


def _page(name: str) -> str:
    return (PAGES / f"{DATE}_{name}.html").read_text(encoding="utf-8")


def _race(n: int, page: str) -> parse.Race:
    mt = parse.find_meetings(_page("day"), DATE)[0]
    race = next(r for r in mt.races if r.number == n)
    html = _page(page)
    parse.parse_race_info(html, race)
    race.runners = parse.parse_field(html)
    return race


def test_day_page():
    mts = parse.find_meetings(_page("day"), DATE)
    assert [m.slug for m in mts] == ["ladbrokes-q1-lakeside"]
    r1 = mts[0].races[0]
    assert r1.number == 1 and r1.name == "Ladbrokes Turn On Flex Multi"   # not the result "2 8 6 9"


def test_field_page():
    race = _race(11, "R11_field")
    assert race.dist == 352 and race.grade == "6th Grade" and not race.finished
    assert race.name == "Gap Greyhounds Make Great Pets"
    assert race.time == "17:36"                     # Brisbane; the page prints Sydney time 18:36

    assert len(race.runners) == 10                  # every <tbody>, not just the first
    starters = {r.box: r for r in race.runners if not r.scratched and not r.reserve}
    assert sorted(starters) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert starters[4].name == "Goldstar Aimee"     # reserve 9 running from box 4
    assert starters[2].name == "Yvonne Gunn" and starters[2].rt == "FM" and starters[2].av_first_sec == 4.08
    assert starters[2].trk_dist_starts == 4 and starters[2].best_td == 19.96 and starters[2].last4 == "4146"

    scratched = {r.name: r.box for r in race.runners if r.scratched}
    assert scratched == {"Beetle Boo": 4, "Lakoda Miley": 10}


def test_shortform_page():
    race = _race(11, "R11_field")
    n = parse.attach_runs(_page("R11_shortform"), race.runners)
    by_name = {r.name: r for r in race.runners}
    assert n == 15                                  # 5 each; "MOST RECENT 2 WINS" copies not counted
    for name in ("Black Is Back", "Beetle Boo", "Goldstar Aimee"):
        assert len(by_name[name].runs) == 5
    assert not by_name["Yvonne Gunn"].runs          # not in the trimmed page

    run = by_name["Goldstar Aimee"].runs[0]
    assert run.date == datetime(2026, 10, 6) and run.track == "QOT" and run.dist == 352
    assert run.first_sec == 4.04 and run.pir == "454" and run.first_pos == 4 and run.box == 5
    dates = [r.date for r in by_name["Black Is Back"].runs]
    assert all(dates) and dates == sorted(dates, reverse=True)

    rm = model.build_map(race)
    assert sorted(d.runner.box for d in rm.dogs) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert "Beetle Boo" not in {d.runner.name for d in rm.dogs}


def test_result_page():
    race = _race(1, "R01_result")
    assert race.finished and race.dist == 457 and race.grade == "Maiden" and race.time == "14:17"
    assert race.name == "Ladbrokes Turn on Flex Multi"
    starters = {r.box: r.name for r in race.runners if not r.scratched and not r.reserve}
    assert starters == {2: "Sergeant", 3: "Paw Jeanie", 4: "Little Lexie", 5: "Better Brew",
                        6: "Paw Huxley", 8: "Rebel Sinner"}
    assert sorted(r.box for r in race.runners if r.scratched) == [1, 3, 5, 7]
    assert all(r.av_first_sec is None for r in race.runners)   # no pre-race Av 1SEC on results
