# CLAUDE.md — Greyhound Speedmaps (Q1 Lakeside, Q2 Parklands)

Personal tool that builds greyhound speedmaps for the Queensland tracks in `config.TRACKS` (Q1 Lakeside, Q2 Parklands) from thedogs.com.au. Repo is still called q1-speedmaps.

## Layout
- `run.py` — CLI entry: for every track in `config.TRACKS` with a meeting that day, loops races, writes `output/<track>/<date>/index.html` + `R##.png` and `output/<track>/latest.html` (built separately, not copied, so its links are relative to the track folder; only replaced if this is the track's newest date). Then `site.build_home`. Exit 1 if the day page looks blocked or a meeting produced no maps.
- `speedmap/config.py` — every tunable: `TRACKS` (name, slug_match = meeting-slug fragment + output folder, codes = past-run track codes), URLs, delays, model constants, rug colours.
- `speedmap/site.py` — `build_home` (output/index.html: each track's latest meeting, newest first, races counted from `<section class=card`), `keep_old_urls` (moves the pre-Q2 root layout `output/<date>/`, `output/latest.html` into `q1-lakeside/` and leaves meta-refresh redirects).
- `speedmap/fetch.py` — requests session, 1.5s polite delay, 20-min disk cache in `cache/`, `save_debug()`.
- `speedmap/parse.py` — dataclasses (Meeting/Race/Runner/Run) and parsers:
  - `find_meetings(day_html, date, slug_match)` — race links matching `/racing/<slug containing slug_match>/<date>/<n>/<race-slug>`.
  - `parse_race_info(html, race)` — name (page spelling), distance/grade from text after the race name ("… 6th Grade 390m"), time from the "16:39 13 Oct" element's `data-timestamp` converted to Brisbane, `finished` if the page shows a results table.
  - `parse_field(html)` — the runners table, located by headers NAME + "Av 1SEC" (or NAME + 1ST SEC/MGN on a results page). Box = rug before the name cell / row order; "(into box N)" / "(from box N)" moves a reserve into that box.
  - `attach_runs(html, runners, before=meeting_date)` — Short Form page (`<race url>/preview`): first tries per-runner tables with DATE/TRACK/1 SEC headers, then falls back to a text regex (`RUN_TEXT_RE`). Drops runs on/after `before`.
- `speedmap/model.py` — `build_map(race, codes)` → `RaceMap` (lengths behind leader at first split, lane, position, confidence, notes). Splits only from runs whose track code is in `codes` at the same distance; otherwise early-position + trait fallback (conf "low", shown as "estimated" / `*`).
- `speedmap/render.py` — matplotlib PNG; `speedmap/report.py` — self-contained HTML (base64 images), "All meetings" list for the track, "All tracks" link.
- `tests/fixtures.py` — synthetic pages built from real data (13 Oct 2026, R5, 390m). `tests/test_pipeline.py` — offline tests.
- `tests/pages/` — trimmed copies of real pages: Q1 13 Oct 2026 (day grid, R11 field + short form, R1 result) → `tests/test_real_pages.py`; Q2 11 Oct R8 520m + 24 Sep R5 710m (result + short form) and the 11 Oct day grid → `tests/test_q2_pages.py`. Tipster comments and photo links are stripped (public repo).
- `scripts/` — `run_speedmaps.sh`/`.bat` (scheduled entry, `--fresh`, logs to `output/run_log.txt`); `schedule_windows.ps1`; `schedule_linux.sh` (systemd user timer `q1-speedmaps.timer`).
- `.github/workflows/speedmaps.yml` — the main schedule: GitHub Actions 3x/day → GitHub Pages (https://haydenbburman-png.github.io/q1-speedmaps/). Restores the previous Pages artifact first so `/<track>/<date>/` folders accumulate; run.py writes the home page. If run.py exits 1 it still publishes, then fails the run. Official `actions/*` only, pinned by SHA. Keepalive job = empty commit after 45 quiet days.

## Known facts about the source
- Field & Form columns (as of Oct 2026): [rug], NAME, R/T, G, TRAINER, LAST 4, TRK/DIST, Av 1SEC, LAST START, VIDEO, Odds. The name cell also contains best T/D time, "T: trainer" and "R/T: XX".
- R/T = running trait (E/G/F/S/R = Excellent/Good/Fair/Slow/Risky) + starting attribute (R/M/S/W = Railer/Middle/Straight/Wide).
- Short Form run lines: place/field, weight, dist, date, track code, grade, time, win time, BON, 1SEC, margin, winner, PIR, SP.
- Track codes in past-run lines (verified from the run links, Oct 2026): QOT = Q1 Lakeside (352/390/457/550m), QTT = Q2 Parklands (520/600/710m), QST = Q Straight, a separate meeting `ladbrokes-q-straight` (300/350m, not built). 1st-split points differ by distance (≈4.0s at 352, ≈6.1s at 390, ≈4.5s at 457, ≈9.1s at 550, ≈5.1s at 520, ≈9.4s at 600, ≈4.6s at 710), so only compare splits at the same track code + distance.
- Q2 Parklands meetings: mostly Sundays, some Thursdays/Saturdays; usually 11 races, mostly 520m, some 600m and 710m. Few dogs have 710m splits, so 710m maps lean on the fallback.
- Expert Form tab loads its run rows with JavaScript — don't use it; Short Form has the same data server-rendered.
- Real markup (checked 13 Oct 2026):
  - Field table has one `<tbody>` per runner (runner row + an empty accordion row). Rug = `<sprite-svg name="rug_N">`.
  - Scratched rows (incl. unused reserves 9/10 and late scratchings "L/S") have class `race-runner--scratched`; "SCR" text isn't always there. Odds are filled by JS.
  - A reserve that gets a run shows "(into box N)" in the name cell; on results pages "(from box N)".
  - Printed times are Sydney time (AEDT in summer); use `data-timestamp`.
  - Once a race is run the page becomes a results table (placing, rug, NAME, R/T, G, TRAINER, WGT, 1ST SEC, 2ND SEC, TIME, MGN, SP), and the day-page link text becomes the result ("2 8 6 9"). Its Short Form is a snapshot from race time (no later runs). The race's own win can appear in the "MOST RECENT 2 WINS" box (ignored), and a reserve that ran earlier that day shows that run (dropped by `before`).
  - Short Form: per runner, a one-row NAME table then a table PLC, BOX (rug), WGT, DIST, DATE ("17:27 09 October 2026"), TRACK, G, TIME, WIN, BON, 1 SEC, MGN, W/2G, PIR, SP — last 5 runs. A "MOST RECENT 2 WINS" divider row nests copies of older wins; only top-level rows are read.

## When parsing breaks
1. `python run.py --debug` → raw pages land in `debug/` (`*_FAILED.html` for failures).
2. Inspect the real markup, then fix `parse.py`. Prefer header/text-based selectors over CSS class names.
3. Save a trimmed real page into `tests/pages/` and add a test for it. Keep `python -m pytest` green.
4. If the site starts returning 403/blank pages (bot protection), switch `fetch.get` to Playwright (`playwright` + chromium) and keep the same function signature.

## Ideas not yet built
- Learn `BOX_ADJUST_LENGTHS` from results (actual first-section position vs predicted, per distance and box).
- Backtest: compare predicted early order with actual PIR first digit after each meeting.
- Push the finished page to phone (Telegram bot or email) at the end of `run.py`.
