# Q1 Lakeside Speedmaps

Automatically builds an easy-to-read speedmap for every race at Q1 Lakeside:
who leads, who's caught wide, where the bumps are likely, and one phone-friendly page per meeting.

- **Source:** fields + form from thedogs.com.au (Field & Form page + Short Form page for each race)
- **Output:** `output/YYYY-MM-DD/index.html` (all races, images embedded) + one PNG per race,
  and `output/latest.html` which always has the newest meeting — bookmark it.

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

That first run should open today's speedmaps in your browser. The terminal prints one line per race, for example:

```
R5 390m 6th Grade: 7 dogs, 32 past runs, 19 splits at trip  ->  order 2 7 3 1 6 8 4
```

If a race says **PARSE FAILED**, or shows `0 past runs`, see *Fixing the scraper* below.
Races that have already been run are still mapped (from form before the race) and marked `(already run)`.
Times are Brisbane time.

## Making it fully automatic

**GitHub (no computer needed):** `.github/workflows/speedmaps.yml` builds the maps on GitHub at 9:00am,
12:30pm and 4:30pm Brisbane time and publishes them to **https://haydenbburman-png.github.io/q1-speedmaps/**
(home page = newest meeting, earlier meetings at `/<date>/`). To run it by hand: GitHub → Actions → speedmaps →
Run workflow. On days with no Q1 meeting the last page stays up. If the site blocks GitHub's servers or every
race fails, the run goes red and nothing is replaced. A keepalive step makes an empty commit if the repo has
been quiet for 45 days, so GitHub doesn't switch the schedule off (it does after 60).

Or run it on your own computer:

**Windows:** run this once in PowerShell from the project folder:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\schedule_windows.ps1
```
That rebuilds the maps daily at 9:00am, 12:30pm and 4:30pm (the later runs pick up scratchings).
On days with no Q1 meeting it just exits. A log is kept in `output/run_log.txt`.

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
| `python run.py` | Today's meeting |
| `python run.py --date tomorrow` | Tomorrow's (fields are usually up the day before) |
| `python run.py --date 2026-10-16` | A specific date |
| `--open` | Open the page in your browser when done |
| `--fresh` | Ignore the 20-minute cache (use it close to race time) |
| `--debug` | Save every raw page to `debug/` |
| `python -m pytest` | Run the offline tests |

## How the map is worked out

1. **Early speed:** each dog's first-split (1SEC) times **at this exact track and distance**, weighted toward
   recent runs and blended with its best, plus the site's "Av 1SEC". (Split points differ a lot by trip: ~4.0s at
   352m and ~6.1s at 390m, so splits from other distances are never mixed in.)
2. **No splits here?** It uses the dog's average early position (first number in its PIR) across recent runs,
   blended with its running-trait letter. These dogs get a dashed rug and a `*`.
3. **Lengths:** split differences are converted at about 0.07s per length.
4. **Lane:** each dog starts at its box and drifts toward its preferred line from the R/T code
   (second letter: **R**ailer, **M**iddle, **W**ide, **S**traight).
5. **Notes:** clear or contested lead, hot pace, railers drawn wide that can't cross, likely first-turn bumps.

Everything adjustable is in `speedmap/config.py` (lengths per second, lane drift, rug colours,
optional box adjustments per distance).

## Fixing the scraper (use Claude Code)

The parsers read visible text and table headers rather than CSS classes, and were checked against the real
pages on 13 Oct 2026 (trimmed copies in `tests/pages/`). If a site change breaks them:

1. Run `python run.py --debug`
2. In Claude Code, ask:
   > The scraper failed. Look at the pages in debug/ and fix speedmap/parse.py so parse_field and attach_runs
   > read them. Keep the tests passing and add a test using a trimmed copy of the real page.

`CLAUDE.md` gives Claude Code the full context for this.

## Fair use

This is for personal use. Keep the request delay in `config.py` (1.5s) and the cache, and don't run it more often than you need.
