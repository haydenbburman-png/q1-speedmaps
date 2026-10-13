"""Generate Q1 Lakeside speedmaps.

Usage:
    python run.py                 # today's meeting (Brisbane time)
    python run.py --date tomorrow
    python run.py --date 2026-10-16 --open
    python run.py --debug         # also save raw pages to debug/ for troubleshooting
"""

from __future__ import annotations

import argparse
import sys
import traceback
import webbrowser
from datetime import datetime, timedelta

from speedmap import config, fetch, model, parse, render, report


def resolve_date(s: str) -> str:
    today = datetime.now(config.BRISBANE).date()
    if s == "today":
        return today.isoformat()
    if s == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    datetime.strptime(s, "%Y-%m-%d")
    return s


def run(date: str, *, debug: bool, fresh: bool, open_browser: bool) -> int:
    day_url = f"{config.BASE_URL}/racing/{date}"
    print(f"Looking for Q1 Lakeside on {date} …")
    day_html = fetch.get(day_url, fresh=fresh)
    meetings = parse.find_meetings(day_html, date)
    if debug:
        fetch.save_debug(f"{date}_day.html", day_html)
    if not meetings:
        if not parse.RACE_HREF.search(day_html):
            # A real day page links to every track's races. None at all = blocked, empty or redesigned page.
            print("The day page has no race links for any track: the site may be blocking requests "
                  "or its layout changed. Not treating this as 'no meeting'.")
            return 1
        print("No Q1 Lakeside meeting found for that date.")
        return 0

    produced = []
    for mt in meetings:
        meet_url = f"{config.BASE_URL}/racing/{mt.slug}/{date}"
        try:
            parse.meeting_races_from_meeting_page(fetch.get(meet_url, fresh=fresh), mt)
        except Exception as e:  # day page links are usually enough
            print(f"  (meeting page skipped: {e})")

        title = "Q1 Lakeside"
        print(f"{mt.slug}: {len(mt.races)} races")
        maps, images = [], {}
        out_dir = config.OUTPUT_DIR / date / (mt.slug if len(meetings) > 1 else "")
        for race in mt.races:
            tag = f"R{race.number}"
            try:
                html = fetch.get(race.url, fresh=fresh)
                if debug:
                    fetch.save_debug(f"{date}_{tag}_field.html", html)
                parse.parse_race_info(html, race)
                race.runners = parse.parse_field(html)
                try:
                    sf = fetch.get(race.url + "/preview", fresh=fresh)
                    if debug:
                        fetch.save_debug(f"{date}_{tag}_shortform.html", sf)
                    n_runs = parse.attach_runs(sf, race.runners)
                except Exception as e:
                    n_runs = 0
                    print(f"  {tag}: short form unavailable ({e})")
                rm = model.build_map(race)
                images[race.number] = render.draw(rm, title, out_dir / f"R{race.number:02d}.png")
                maps.append(rm)
                matched = sum(d.n_sec for d in rm.dogs)
                print(f"  {tag} {race.dist or '?'}m {race.grade}: {len(rm.dogs)} dogs, {n_runs} past runs, "
                      f"{matched} splits at trip  ->  order {' '.join(str(d.runner.box) for d in rm.dogs)}"
                      + ("  (already run)" if race.finished else ""))
            except parse.ParseError as e:
                p = fetch.save_debug(f"{date}_{tag}_FAILED.html", html)
                print(f"  {tag}: PARSE FAILED — {e}. Raw page saved to {p}")
            except Exception:
                print(f"  {tag}: error\n{traceback.format_exc()}")

        if maps:
            root = config.OUTPUT_DIR
            page = report.build(title, date, maps, images, out_dir / "index.html", site_root=root)
            # Built again rather than copied: its "All meetings" links are relative to output/.
            latest = report.build(title, date, maps, images, root / "latest.html", site_root=root)
            produced.append(page)
            print(f"\nSpeedmaps ready: {page}\n(also saved as {latest})")

    if open_browser and produced:
        webbrowser.open(produced[0].resolve().as_uri())
    return 0 if produced else 1


def main() -> None:
    ap = argparse.ArgumentParser(description="Q1 Lakeside greyhound speedmaps")
    ap.add_argument("--date", default="today", help="today | tomorrow | YYYY-MM-DD")
    ap.add_argument("--open", action="store_true", help="open the result in your browser")
    ap.add_argument("--debug", action="store_true", help="save raw pages to debug/")
    ap.add_argument("--fresh", action="store_true", help="ignore the cache (pick up late scratchings)")
    a = ap.parse_args()
    try:  # Windows consoles choke on some characters otherwise
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(run(resolve_date(a.date), debug=a.debug, fresh=a.fresh, open_browser=a.open))


if __name__ == "__main__":
    main()
