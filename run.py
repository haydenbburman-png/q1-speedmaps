"""Generate greyhound speedmaps for every track in speedmap/config.py TRACKS (Q1 Lakeside, Q2 Parklands).

Usage:
    python run.py                 # today's meetings (Brisbane time)
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
from pathlib import Path

from speedmap import config, fetch, model, parse, render, report, site


def resolve_date(s: str) -> str:
    today = datetime.now(config.BRISBANE).date()
    if s == "today":
        return today.isoformat()
    if s == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    datetime.strptime(s, "%Y-%m-%d")
    return s


def run(date: str, *, debug: bool, fresh: bool, open_browser: bool) -> int:
    root = config.OUTPUT_DIR
    site.keep_old_urls(root)
    try:
        status, produced = _build_day(date, debug=debug, fresh=fresh)
    finally:  # the home page always reflects what's in output/, even after a failure
        home = site.build_home(root)
    print(f"\nHome page: {home}")
    if open_browser and produced:
        webbrowser.open((produced[0] if len(produced) == 1 else home).resolve().as_uri())
    return status


def _build_day(date: str, *, debug: bool, fresh: bool) -> tuple[int, list[Path]]:
    """Build every track in config.TRACKS that has a meeting on `date`.
    Status 1 if the day page looks blocked or a meeting produced no maps, else 0 (also when no meetings)."""
    day_url = f"{config.BASE_URL}/racing/{date}"
    print(f"Looking for {' / '.join(t.name for t in config.TRACKS)} meetings on {date} …")
    day_html = fetch.get(day_url, fresh=fresh)
    if debug:
        fetch.save_debug(f"{date}_day.html", day_html)
    if not parse.RACE_HREF.search(day_html):
        # A real day page links to every track's races. None at all = blocked, empty or redesigned page.
        print("The day page has no race links for any track: the site may be blocking requests "
              "or its layout changed. Not treating this as 'no meeting'.")
        return 1, []

    produced, failed = [], False
    for track in config.TRACKS:
        meetings = parse.find_meetings(day_html, date, track.slug_match)
        if not meetings:
            print(f"\nNo {track.name} meeting on {date}.")
            continue
        for mt in meetings:
            page = _build_meeting(track, mt, date, mt.slug if len(meetings) > 1 else "",
                                  debug=debug, fresh=fresh)
            if page:
                produced.append(page)
            else:
                failed = True
    return (1 if failed else 0), produced


def _build_meeting(track: config.Track, mt: parse.Meeting, date: str, sub: str, *,
                   debug: bool, fresh: bool) -> Path | None:
    """Map every race of one meeting into output/<track>/<date>/. None if no race could be mapped."""
    meet_url = f"{config.BASE_URL}/racing/{mt.slug}/{date}"
    try:
        parse.meeting_races_from_meeting_page(fetch.get(meet_url, fresh=fresh), mt)
    except Exception as e:  # day page links are usually enough
        print(f"  (meeting page skipped: {e})")

    print(f"\n{track.name} ({mt.slug}): {len(mt.races)} races")
    track_dir = config.OUTPUT_DIR / track.slug_match
    out_dir = track_dir / date / sub
    prefix = f"{date}_{track.slug_match}"
    meeting_day = datetime.strptime(date, "%Y-%m-%d").date()
    maps, images = [], {}
    for race in mt.races:
        tag = f"R{race.number}"
        try:
            html = fetch.get(race.url, fresh=fresh)
            if debug:
                fetch.save_debug(f"{prefix}_{tag}_field.html", html)
            parse.parse_race_info(html, race)
            race.runners = parse.parse_field(html)
            try:
                sf = fetch.get(race.url + "/preview", fresh=fresh)
                if debug:
                    fetch.save_debug(f"{prefix}_{tag}_shortform.html", sf)
                n_runs = parse.attach_runs(sf, race.runners, before=meeting_day)
            except Exception as e:
                n_runs = 0
                print(f"  {tag}: short form unavailable ({e})")
            rm = model.build_map(race, track.codes)
            images[race.number] = render.draw(rm, track.name, out_dir / f"R{race.number:02d}.png")
            maps.append(rm)
            matched = sum(d.n_sec for d in rm.dogs)
            print(f"  {tag} {race.dist or '?'}m {race.grade}: {len(rm.dogs)} dogs, {n_runs} past runs, "
                  f"{matched} splits at trip  ->  order {' '.join(str(d.runner.box) for d in rm.dogs)}"
                  + ("  (already run)" if race.finished else ""))
        except parse.ParseError as e:
            p = fetch.save_debug(f"{prefix}_{tag}_FAILED.html", html)
            print(f"  {tag}: PARSE FAILED — {e}. Raw page saved to {p}")
        except Exception:
            print(f"  {tag}: error\n{traceback.format_exc()}")

    if not maps:
        return None
    page = report.build(track.name, date, maps, images, out_dir / "index.html", site_root=track_dir)
    newest = max(d.name for d in track_dir.iterdir() if d.is_dir() and report.DATE_DIR.fullmatch(d.name))
    if date >= newest:  # an older meeting built later (e.g. --date 2026-09-24) mustn't replace latest
        # Built again rather than copied: its links are relative to the track folder.
        latest = report.build(track.name, date, maps, images, track_dir / "latest.html", site_root=track_dir)
        print(f"Speedmaps ready: {page}\n(also saved as {latest})")
    else:
        print(f"Speedmaps ready: {page}\n(latest.html left on the newer {newest} meeting)")
    return page


def main() -> None:
    ap = argparse.ArgumentParser(description="Greyhound speedmaps for Q1 Lakeside and Q2 Parklands")
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
