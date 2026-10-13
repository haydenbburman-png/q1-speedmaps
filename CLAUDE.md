# CLAUDE.md — Q1 Lakeside Speedmaps

Personal tool that builds greyhound speedmaps for Q1 Lakeside (Queensland) from thedogs.com.au.

## Layout
- `run.py` — CLI entry: finds the meeting, loops races, writes `output/<date>/index.html` + `R##.png`, and `output/latest.html` (built separately, not copied, so its "All meetings" links are relative to `output/`; `report._meetings_list` lists every `<date>/index.html`).
- `speedmap/config.py` — every tunable (URLs, delays, model constants, rug colours).
- `speedmap/fetch.py` — requests session, 1.5s polite delay, 20-min disk cache in `cache/`, `save_debug()`.
- `speedmap/parse.py` — dataclasses (Meeting/Race/Runner/Run) and parsers:
  - `find_meetings(day_html, date)` — race links matching `/racing/<slug containing q1-lakeside>/<date>/<n>/<race-slug>`.
  - `parse_race_info(html, race)` — name (page spelling), distance/grade from text after the race name ("… 6th Grade 390m"), time from the "16:39 13 Oct" element's `data-timestamp` converted to Brisbane, `finished` if the page shows a results table.
  - `parse_field(html)` — the runners table, located by headers NAME + "Av 1SEC" (or NAME + 1ST SEC/MGN on a results page). Box = rug before the name cell / row order; "(into box N)" / "(from box N)" moves a reserve into that box.
  - `attach_runs(html, runners)` — Short Form page (`<race url>/preview`): first tries per-runner tables with DATE/TRACK/1 SEC headers, then falls back to a text regex (`RUN_TEXT_RE`).
- `speedmap/model.py` — `build_map(race)` → `RaceMap` (lengths behind leader at first split, lane, position, confidence, notes).
- `speedmap/render.py` — matplotlib PNG; `speedmap/report.py` — self-contained HTML (base64 images).
- `tests/fixtures.py` — synthetic pages built from real data (13 Oct 2026, R5, 390m). `tests/test_pipeline.py` — offline tests.
- `tests/pages/` — trimmed copies of real pages (13 Oct 2026: day grid, R11 field + short form, R1 result); `tests/test_real_pages.py` tests them.
- `scripts/` — `run_speedmaps.sh`/`.bat` (scheduled entry, `--fresh`, logs to `output/run_log.txt`); `schedule_windows.ps1`; `schedule_linux.sh` (systemd user timer `q1-speedmaps.timer`).
- `.github/workflows/speedmaps.yml` — the main schedule: GitHub Actions 3x/day → GitHub Pages (https://haydenbburman-png.github.io/q1-speedmaps/). Restores the previous Pages artifact first so `/<date>/` folders accumulate; `index.html` = `latest.html`. Official `actions/*` only, pinned by SHA. Keepalive job = empty commit after 45 quiet days.

## Known facts about the source
- Field & Form columns (as of Oct 2026): [rug], NAME, R/T, G, TRAINER, LAST 4, TRK/DIST, Av 1SEC, LAST START, VIDEO, Odds. The name cell also contains best T/D time, "T: trainer" and "R/T: XX".
- R/T = running trait (E/G/F/S/R = Excellent/Good/Fair/Slow/Risky) + starting attribute (R/M/S/W = Railer/Middle/Straight/Wide).
- Short Form run lines: place/field, weight, dist, date, track code, grade, time, win time, BON, 1SEC, margin, winner, PIR, SP.
- Q1 track codes: QOT one-turn, QTT two-turn, QST straight. 1st-split points differ by distance (≈4.0s at 352, ≈6.1s at 390, ≈4.5s at 457, ≈5.3s at 520), so only compare splits at the same track code + distance.
- Expert Form tab loads its run rows with JavaScript — don't use it; Short Form has the same data server-rendered.
- Real markup (checked 13 Oct 2026):
  - Field table has one `<tbody>` per runner (runner row + an empty accordion row). Rug = `<sprite-svg name="rug_N">`.
  - Scratched rows (incl. unused reserves 9/10 and late scratchings "L/S") have class `race-runner--scratched`; "SCR" text isn't always there. Odds are filled by JS.
  - A reserve that gets a run shows "(into box N)" in the name cell; on results pages "(from box N)".
  - Printed times are Sydney time (AEDT in summer); use `data-timestamp`.
  - Once a race is run the page becomes a results table (placing, rug, NAME, R/T, G, TRAINER, WGT, 1ST SEC, 2ND SEC, TIME, MGN, SP), and the day-page link text becomes the result ("2 8 6 9"). Its Short Form still only lists runs before the race.
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
