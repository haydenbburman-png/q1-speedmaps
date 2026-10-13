import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from speedmap import model, parse, render, report  # noqa: E402
from tests import fixtures as fx  # noqa: E402


def _race():
    mts = parse.find_meetings(fx.day_page(), fx.DATE)
    assert len(mts) == 1 and mts[0].slug == fx.SLUG
    race = mts[0].races[0]
    parse.parse_race_info(fx.field_page(), race)
    race.runners = parse.parse_field(fx.field_page())
    return race


def test_meeting_and_field():
    race = _race()
    assert race.number == 5 and race.dist == 390 and race.grade == "6th Grade" and race.time == "16:39"
    boxes = {r.box: r for r in race.runners}
    assert sorted(boxes) == [1, 2, 3, 4, 6, 7, 8]          # box 5 vacant
    assert boxes[3].name == "Maddie's Lakoda" and boxes[3].av_first_sec == 6.07
    assert boxes[6].rt == "SR" and boxes[6].av_first_sec is None
    assert boxes[1].best_td == 22.45 and boxes[6].best_td is None


def test_shortform_tables_and_text():
    for as_tables in (True, False):
        race = _race()
        n = parse.attach_runs(fx.shortform_page(as_tables), race.runners)
        assert n == sum(len(v) for v in fx.RUNS.values()), (as_tables, n)
        lak = next(r for r in race.runners if r.box == 3)
        assert lak.runs[0].first_sec == 6.12 and lak.runs[0].first_pos == 1


def test_model_order():
    race = _race()
    parse.attach_runs(fx.shortform_page(), race.runners)
    rm = model.build_map(race)
    order = [d.runner.box for d in rm.dogs]
    assert order[0] in (2, 7, 3)                      # quickest 390m splits
    assert order[-1] in (4, 8, 6)
    paw = next(d for d in rm.dogs if d.runner.box == 6)
    assert paw.conf == "low"                           # no 390m splits
    assert rm.notes


def test_render(tmp_path):
    race = _race()
    parse.attach_runs(fx.shortform_page(), race.runners)
    rm = model.build_map(race)
    png = render.draw(rm, "Q1 Lakeside", tmp_path / "R05.png")
    page = report.build("Q1 Lakeside", fx.DATE, [rm], {5: png}, tmp_path / "index.html")
    assert png.stat().st_size > 10_000 and "data:image/png" in page.read_text()


def test_meetings_list(tmp_path):
    race = _race()
    parse.attach_runs(fx.shortform_page(), race.runners)
    rm = model.build_map(race)
    for d in ("2026-10-09", fx.DATE):
        report.build("Q1 Lakeside", d, [rm], {}, tmp_path / d / "index.html", site_root=tmp_path)
    home = report.build("Q1 Lakeside", fx.DATE, [rm], {}, tmp_path / "latest.html", site_root=tmp_path).read_text()
    assert "All meetings (2)" in home
    assert home.index('href="2026-10-13/index.html"') < home.index('href="2026-10-09/index.html"')  # newest first
    day = (tmp_path / fx.DATE / "index.html").read_text()
    assert 'href="../latest.html"' in day and 'href="../2026-10-09/index.html"' in day
