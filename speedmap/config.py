"""All the knobs in one place. Edit these freely."""

from datetime import timedelta, timezone
from pathlib import Path
from typing import NamedTuple

# Queensland has no daylight saving. thedogs prints times in Sydney time, so race
# times are converted to this from the page's timestamps.
BRISBANE = timezone(timedelta(hours=10))

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"   # speedmaps land here: output/YYYY-MM-DD/index.html
CACHE_DIR = ROOT / "cache"     # raw HTML cache (so re-runs don't hammer the site)
DEBUG_DIR = ROOT / "debug"     # raw pages saved when --debug is used or parsing fails

BASE_URL = "https://www.thedogs.com.au"


class Track(NamedTuple):
    name: str               # shown on pages and maps
    slug_match: str         # a meeting whose URL slug contains this is this track (the sponsor
                            # prefix changes, e.g. "ladbrokes-q1-lakeside"); also its output folder
    codes: frozenset[str]   # track code(s) in past-run lines; splits only count from these


# Every track with a meeting that day gets built. Codes checked against past-run links (Oct 2026):
#   QOT = Q1 Lakeside (352/390/457/550m), QTT = Q2 Parklands (520/600/710m),
#   QST = Q Straight, a separate meeting (ladbrokes-q-straight, 300/350m) — not built here.
TRACKS = [
    Track("Q1 Lakeside", "q1-lakeside", frozenset({"QOT"})),
    Track("Q2 Parklands", "q2-parklands", frozenset({"QTT"})),
]

# Be polite: seconds between requests, and how long cached pages stay fresh.
REQUEST_DELAY_SEC = 1.5
CACHE_TTL_MIN = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# ---- Speed model ----------------------------------------------------------
SEC_PER_LENGTH = 0.07          # ~1 greyhound length at the first split
RECENT_RUNS = 6                # how many recent runs to look at
MIN_RUNS_HIGH_CONF = 3         # sectionals at this track/dist for "high" confidence

# When a dog has no sectional at this track/distance, fall back to its
# running-trait letter (first letter of R/T): E=Excellent ... R=Risky.
# Value = assumed early position in an 8-dog field.
TRAIT_DEFAULT_POSITION = {"E": 2.0, "G": 3.5, "F": 5.0, "S": 6.5, "R": 6.0}

# Second letter of R/T = where the dog likes to run.
#   R = railer, M = middle, W = wide, S = runs straight off its box
# How strongly it drifts toward its preferred lane by the first turn (0-1).
LANE_DRIFT = 0.45

# Optional per-distance box adjustment in LENGTHS (+ = slower to the turn).
# Leave at 0 until you have data; e.g. {390: {8: 0.3}} gives box 8 a 0.3L penalty at 390m.
BOX_ADJUST_LENGTHS: dict[int, dict[int, float]] = {}

# ---- Look ------------------------------------------------------------------
# Australian rug colours: (face colour, number colour, striped?)
RUGS = {
    1: ("#d62828", "#ffffff", False),   # red
    2: ("#ffffff", "#d62828", True),    # black & white stripes
    3: ("#ffffff", "#111111", False),   # white
    4: ("#1d4ed8", "#ffffff", False),   # blue
    5: ("#facc15", "#111111", False),   # yellow
    6: ("#15803d", "#ffffff", False),   # green
    7: ("#111111", "#facc15", False),   # black
    8: ("#f472b6", "#111111", False),   # pink
    9: ("#15803d", "#ffffff", True),    # reserve
    10: ("#d62828", "#ffffff", True),   # reserve
}
