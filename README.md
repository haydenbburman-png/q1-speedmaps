# Greyhound Speedmaps — Q1 Lakeside & Q2 Parklands

Automatically builds an easy-to-read speedmap for every race at **Q1 Lakeside** and **Q2 Parklands**:
who leads, who's caught wide, where the bumps are likely, and one phone-friendly page per meeting.

- **Source:** fields + form from thedogs.com.au (Field & Form page + Short Form page for each race)
- **Output:** one folder per track, e.g. `output/q2-parklands/YYYY-MM-DD/index.html` (all races, images
  embedded) + one PNG per race, and `output/<track>/latest.html` with that track's newest meeting.
  `output/index.html` is the home page: each track's latest meeting (date, races, link), newest first.
  Each meeting page has an **All meetings** list for its track and an **All tracks** link home.

## Setup (once, in the VS Code terminal)

**Windows**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py --open --debug
```

**Mac / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py --open --debug
```

That first run should open today's speedmaps in your browser (if either track races today). The terminal prints one line per race, for example:

```
R5 390m 6th Grade: 7 dogs, 32 past runs, 19 splits at trip  ->  order 2 7 3 1 6 8 4
```

If a race says **PARSE FAILED**, or shows `0 past runs`, see *Fixing the scraper* below.
Races that have already been run are still mapped (from form before the race) and marked `(already run)`.
Times are Brisbane time.

## Making it fully automatic

**GitHub (no computer needed):** `.github/workflows/speedmaps.yml` builds the maps on GitHub at about 7:17am,
9:17am, 12:47pm and 4:47pm Brisbane time (GitHub often starts scheduled runs late; if the page is behind,
use Run workflow) and publishes them to **https://haydenbburman-png.github.io/q1-speedmaps/**
(home page = track chooser; meetings at `/q1-lakeside/<date>/` and `/q2-parklands/<date>/`; the old Q1 links
`/latest.html` and `/2026-10-13/` redirect into `/q1-lakeside/`). To run it by hand: GitHub → Actions →
speedmaps → Run workflow. On days with no meeting the last pages stay up. If the site blocks GitHub's servers or
a meeting can't be built, the run goes red (GitHub emails you); anything that did build is still published. A keepalive step makes an empty commit if the repo has
been quiet for 45 days, so GitHub doesn't switch the schedule off (it does after 60).

Or run it on your own computer:

**Windows:** run this once in PowerShell from the project folder:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\schedule_windows.ps1
```
That rebuilds the maps daily at 9:00am, 12:30pm and 4:30pm (the later runs pick up scratchings).
On days with no meeting it just exits. A log is kept in `output/run_log.txt`.

**Linux:** run this once from the project folder:
```bash
sh scripts/schedule_linux.sh
```
That adds a systemd user timer for the same times (Brisbane time). If the computer was off at one of them,
the missed build runs when it's back on. Check it with `systemctl --user list-timers q1-speedmaps.timer`,
remove it with `systemctl --user disable --now q1-speedmaps.timer`. Log: `output/run_log.txt`.

**Mac:** run `crontab -e` and add (change the path):
```
0 9,12,16 * * * /Users/you/q1-speedmaps/scripts/run_speedmaps.sh
```

Your computer has to be on (awake) at those times.

## Commands

| Command | What it does |
|---|---|
| `python run.py` | Today's meetings (every track racing today) |
| `python run.py --date tomorrow` | Tomorrow's (fields are usually up the day before) |
| `python run.py --date 2026-10-16` | A specific date |
| `--open` | Open the page in your browser when done |
| `--fresh` | Ignore the 20-minute cache (use it close to race time) |
| `--debug` | Save every raw page to `debug/` |
| `python -m pytest` | Run the offline tests |

## How the map is worked out

1. **Early speed:** each dog's first-split (1SEC) times **at this exact track and distance**, weighted toward
   recent runs and blended with its best, plus the site's "Av 1SEC". Only runs with the track's own code count
   (Q1 Lakeside = QOT, Q2 Parklands = QTT). Split points differ a lot by trip (~4.0s at 352m, ~6.1s at 390m,
   ~5.1s at 520m, ~9.4s at 600m, ~4.6s at 710m), so splits from other distances are never mixed in.
2. **No splits here?** It uses the dog's average early position (first number in its PIR) across recent runs,
   blended with its running-trait letter. These dogs get a dashed rug and a `*` on the map and are marked
   **estimated** in the table (common at 710m, where few dogs have a split).
3. **Lengths:** split differences are converted at about 0.07s per length.
4. **Lane:** each dog starts at its box and drifts toward its preferred line from the R/T code
   (second letter: **R**ailer, **M**iddle, **W**ide, **S**traight).
5. **Notes:** clear or contested lead, hot pace, railers drawn wide that can't cross, likely first-turn bumps.

Everything adjustable is in `speedmap/config.py` (lengths per second, lane drift, rug colours,
optional box adjustments per distance).

**Adding a track:** add a line to `TRACKS` in `speedmap/config.py` — display name, a piece of its meeting
slug (from the URL, e.g. `q2-parklands` in `/racing/ladbrokes-q2-parklands/2026-10-11`) and its track
code(s) as they appear in past-run lines. It gets its own folder, latest page and home-page card.

## Fixing the scraper (use Claude Code)

The parsers read visible text and table headers rather than CSS classes, and were checked against the real
pages in Oct 2026 (trimmed copies in `tests/pages/`, including Q2 Parklands 520m and 710m races). If a site change breaks them:

1. Run `python run.py --debug`
2. In Claude Code, ask:
   > The scraper failed. Look at the pages in debug/ and fix speedmap/parse.py so parse_field and attach_runs
   > read them. Keep the tests passing and add a test using a trimmed copy of the real page.

`CLAUDE.md` gives Claude Code the full context for this.

## Fair use

This is for personal use. Keep the request delay in `config.py` (1.5s) and the cache, and don't run it more often than you need.
