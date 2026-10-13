"""The site around the meeting pages: the home page chooser and redirects for old Q1 URLs.

Layout of output/ (= the GitHub Pages site):
    index.html                      chooser: each track's latest meeting, newest first
    <track>/latest.html             newest meeting for that track
    <track>/<date>/index.html       one meeting (+ R##.png)
    latest.html, <date>/index.html  redirects: Q1 pages lived here before Q2 was added
"""

from __future__ import annotations

import html
import shutil
from datetime import datetime
from pathlib import Path

from . import config
from .report import CSS, DATE_DIR

LEGACY_TRACK = "q1-lakeside"  # before Q2 was added, Q1's pages sat at the site root

HOME_CSS = """
a.card{display:block;color:inherit;text-decoration:none}a.card:hover{border-color:var(--ink)}
.track{font-size:19px;font-weight:700}.when{margin-top:2px}.open{margin-top:6px;font-weight:600;font-size:14px}
.card.none{opacity:.6}
"""


def _is_redirect(page: Path) -> bool:
    with page.open(encoding="utf-8", errors="replace") as f:
        return 'http-equiv="refresh"' in f.read(400)


def _write_redirect(page: Path, target: str) -> None:
    t = html.escape(target)
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(
        f'<!doctype html><meta charset=utf-8><title>Moved</title>'
        f'<meta http-equiv="refresh" content="0; url={t}"><p>Moved to <a href="{t}">{t}</a></p>\n',
        encoding="utf-8",
    )


def keep_old_urls(root: Path) -> None:
    """Move Q1 pages from the old layout (<root>/<date>/, <root>/latest.html) into
    <root>/q1-lakeside/ and leave redirects behind, so old bookmarks keep working."""
    if not root.is_dir():
        return
    q1 = root / LEGACY_TRACK
    moved = []
    for d in sorted(root.iterdir()):
        page = d / "index.html"
        if not (d.is_dir() and DATE_DIR.fullmatch(d.name)) or (page.exists() and _is_redirect(page)):
            continue
        dest = q1 / d.name
        if dest.exists():                       # already rebuilt in the new place
            shutil.rmtree(d)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(d), str(dest))
            moved.append(d.name)
        _write_redirect(page, f"../{LEGACY_TRACK}/{d.name}/index.html")

    latest = root / "latest.html"
    if latest.exists() and not _is_redirect(latest):
        if not (q1 / "latest.html").exists() and moved:  # until Q1's next build writes the real one
            _write_redirect(q1 / "latest.html", f"{max(moved)}/index.html")
        _write_redirect(latest, f"{LEGACY_TRACK}/latest.html")


def _latest_meeting(track_dir: Path) -> tuple[str, int] | None:
    """(date, races) for the newest meeting built for a track."""
    dates = sorted((d for d in track_dir.glob("*") if d.is_dir() and DATE_DIR.fullmatch(d.name)),
                   key=lambda d: d.name, reverse=True)
    for d in dates:
        pages = [p for p in d.glob("**/index.html") if not _is_redirect(p)]
        if pages:
            return d.name, sum(p.read_text(encoding="utf-8").count("<section class=card") for p in pages)
    return None


def build_home(root: Path) -> Path:
    """Write <root>/index.html: one card per track, newest meeting first."""
    found, missing = [], []
    for t in config.TRACKS:
        latest = _latest_meeting(root / t.slug_match)
        (found if latest else missing).append((t, latest))
    found.sort(key=lambda x: x[1][0], reverse=True)

    cards = []
    for t, (date, races) in found:
        d = datetime.strptime(date, "%Y-%m-%d")
        cards.append(
            f'<a class=card href="{html.escape(t.slug_match)}/latest.html"><div class=body>'
            f'<div class=track>{html.escape(t.name)}</div>'
            f'<div class="sub when">{d:%A} {d.day} {d:%B %Y} · {races} race{"s" if races != 1 else ""}</div>'
            f'<div class=open>Open speedmaps →</div></div></a>'
        )
    for t, _ in missing:
        cards.append(f'<div class="card none"><div class=body><div class=track>{html.escape(t.name)}</div>'
                     f'<div class="sub when">No meetings built yet</div></div></div>')

    stamp = datetime.now(config.BRISBANE).strftime("%a %d %b %Y, %I:%M %p")
    page = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Greyhound speedmaps</title><style>{CSS}{HOME_CSS}</style></head>
<body><header><h1>Greyhound speedmaps</h1>
<div class=sub>Latest meeting at each track · updated {stamp} (Brisbane)</div></header>
<main>{''.join(cards)}</main></body></html>"""
    out = root / "index.html"
    root.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out
