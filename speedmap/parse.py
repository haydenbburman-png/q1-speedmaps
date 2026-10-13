"""Turn thedogs.com.au pages into Meeting / Race / Runner / Run objects.

The parsers lean on visible text and table headers rather than CSS class names,
so small site redesigns are less likely to break them. If a page can't be read,
a ParseError is raised and the raw HTML is saved to debug/ so it can be fixed.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from . import config


class ParseError(Exception):
    pass


# --------------------------------------------------------------------------- data


@dataclass
class Run:
    date: datetime | None
    track: str
    dist: int
    first_sec: float | None
    pir: str              # in-running positions, e.g. "113"
    place: int | None = None
    box: int | None = None

    @property
    def first_pos(self) -> int | None:
        digits = re.findall(r"\d", self.pir or "")
        return int(digits[0]) if digits else None


@dataclass
class Runner:
    box: int
    name: str
    trainer: str = ""
    rt: str = ""                 # running trait code e.g. "FM"
    av_first_sec: float | None = None   # Av 1SEC at this track/distance (site figure)
    trk_dist_starts: int = 0
    best_td: float | None = None
    last4: str = ""
    scratched: bool = False
    reserve: bool = False
    runs: list[Run] = field(default_factory=list)

    @property
    def display(self) -> str:
        """Readable name: keep site casing unless it's ALL CAPS."""
        return string.capwords(self.name) if self.name.isupper() else self.name

    @property
    def trait(self) -> str:
        return self.rt[:1].upper() if self.rt else ""

    @property
    def lane_pref(self) -> str:
        return self.rt[1:2].upper() if len(self.rt) >= 2 else ""


@dataclass
class Race:
    number: int
    name: str
    url: str
    dist: int | None = None
    grade: str = ""
    time: str = ""               # Brisbane time
    finished: bool = False       # page already shows the result
    runners: list[Runner] = field(default_factory=list)


@dataclass
class Meeting:
    date: str
    slug: str
    title: str
    races: list[Race] = field(default_factory=list)


# --------------------------------------------------------------------------- helpers

RACE_HREF = re.compile(r"/racing/([^/?#]+)/(\d{4}-\d{2}-\d{2})/(\d{1,2})/([^/?#]+)")
DIST_RE = re.compile(r"(?<![\d/.])([2-9]\d{2})\s?m\b")
TIME_RE = re.compile(r"\b([0-2]?\d:[0-5]\d)\s*(?:[ap]m)?\b", re.I)
START_RE = re.compile(r"\b([0-2]?\d:[0-5]\d)\s+\d{1,2}\s+[A-Z][a-z]{2}\b")   # "16:39 13 Oct"
# A reserve taking a scratched dog's box: "(into box 4)" on fields, "(from box 4)" on results.
INTO_BOX_RE = re.compile(r"\((?:into|from) box (\d{1,2})\)", re.I)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _text(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip() if el else ""


def _float(s: str) -> float | None:
    m = re.search(r"\d+\.\d+", s or "")
    return float(m.group()) if m else None


def _slug_pattern(slug: str) -> re.Pattern:
    words = [w for w in slug.split("-") if w]
    return re.compile(r"\W*".join(re.escape(w) for w in words), re.I)


def _norm_header(s: str) -> str:
    return re.sub(r"[^a-z0-9/]", "", s.lower())


# --------------------------------------------------------------------------- meetings


def find_meetings(day_html: str, date: str) -> list[Meeting]:
    """From https://www.thedogs.com.au/racing/YYYY-MM-DD find Q1 Lakeside meeting(s) + race links."""
    soup = _soup(day_html)
    meetings: dict[str, Meeting] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        m = RACE_HREF.search(href)
        if not m:
            continue
        slug, d, num, race_slug = m.groups()
        if d != date or config.TRACK_SLUG_MATCH not in slug:
            continue
        mt = meetings.setdefault(
            slug, Meeting(date=date, slug=slug, title=slug.replace("-", " ").title())
        )
        n = int(num)
        if any(r.number == n for r in mt.races):
            continue
        url = urljoin(config.BASE_URL, urlparse(href).path)
        name = _text(a)  # once a race is run the link text is the result, e.g. "2 8 6 9"
        if not name or re.fullmatch(r"R?[\d\s]+", name) or len(name) < 4:
            name = race_slug.replace("-", " ").title()
        mt.races.append(Race(number=n, name=name, url=url))
    for mt in meetings.values():
        mt.races.sort(key=lambda r: r.number)
    return list(meetings.values())


def meeting_races_from_meeting_page(html: str, meeting: Meeting) -> None:
    """Fill race links from the meeting page if the day page didn't list them all."""
    found = find_meetings(html, meeting.date)
    for mt in found:
        if mt.slug == meeting.slug:
            have = {r.number for r in meeting.races}
            meeting.races += [r for r in mt.races if r.number not in have]
    meeting.races.sort(key=lambda r: r.number)


# --------------------------------------------------------------------------- race header


def parse_race_info(html: str, race: Race) -> None:
    soup = _soup(html)
    text = _text(soup.body or soup)
    slug = urlparse(race.url).path.rstrip("/").split("/")[-1]
    pat = _slug_pattern(slug)

    # Distance + grade normally sit right after the race name: "R5 Engineering by ... 6th Grade 390m"
    for m in pat.finditer(text):
        tail = text[m.end(): m.end() + 140]
        dm = DIST_RE.search(tail)
        if dm:
            race.name = m.group(0)  # page spelling, e.g. "Garrard's" rather than the slug's "Garrard S"
            race.dist = int(dm.group(1))
            grade = tail[: dm.start()].strip(" -|·,")
            if 0 < len(grade) <= 30:
                race.grade = grade
            break

    if race.dist is None:  # fallback: headings, then title
        for el in soup.find_all(["h1", "h2", "h3", "h4", "title"]):
            dm = DIST_RE.search(_text(el))
            if dm:
                race.dist = int(dm.group(1))
                break

    # Start time e.g. "16:39 13 Oct". That text is Sydney time, so use its timestamp when there is one.
    for el in soup.find_all(attrs={"data-timestamp": True}):
        if START_RE.search(_text(el)) and el["data-timestamp"].isdigit():
            race.time = datetime.fromtimestamp(int(el["data-timestamp"]), config.BRISBANE).strftime("%H:%M")
            break
    else:
        tm = START_RE.search(text)
        if tm:
            race.time = tm.group(1)

    found = _runner_table(soup)
    race.finished = bool(found and found[2])


# --------------------------------------------------------------------------- field table


def _header_cells(table: Tag) -> list[str]:
    head = table.find("thead")
    row = head.find("tr") if head else table.find("tr")
    if not row:
        return []
    return [_norm_header(_text(c)) for c in row.find_all(["th", "td"])]


def _find_col(headers: list[str], *keys: str) -> int | None:
    for k in keys:
        for i, h in enumerate(headers):
            if h == k:
                return i
    for k in keys:
        for i, h in enumerate(headers):
            if k in h:
                return i
    return None


def _box_from_cell(cell: Tag) -> int | None:
    # Rug image/sprite first (thedogs uses <sprite-svg name="rug_3">), then a bare number.
    for el in [cell, *cell.find_all(True)]:
        bits = " ".join(
            [el.get("alt", ""), el.get("title", ""), el.get("src", ""), el.get("name", ""),
             " ".join(el.get("class", []))]
        )
        m = re.search(r"(?:rug|box|number)[-_ ]?(\d{1,2})\b", bits, re.I)
        if m:
            return int(m.group(1))
    t = _text(cell)
    if re.fullmatch(r"\d{1,2}\.?", t):
        return int(t.rstrip("."))
    return None


def _body_rows(table: Tag) -> list[Tag]:
    """Top-level body rows. thedogs wraps each runner in its own <tbody>, and nests copies of
    older runs inside a "MOST RECENT 2 WINS" divider row, so don't search recursively."""
    bodies = table.find_all("tbody")
    if not bodies:
        return table.find_all("tr")[1:]
    return [tr for b in bodies for tr in b.find_all("tr", recursive=False)]


def _runner_table(soup: BeautifulSoup) -> tuple[Tag, list[str], bool] | None:
    """The runners table and its headers: NAME + Av 1SEC on the Field & Form page, or
    NAME + 1ST SEC / MGN once the race has been run (third value True)."""
    for t in soup.find_all("table"):
        hs = _header_cells(t)
        if not any("name" in h for h in hs):
            continue
        if any("1sec" in h for h in hs):
            return t, hs, False
        if any(h in ("1stsec", "mgn") for h in hs):
            return t, hs, True
    return None


NAME_SPLIT = re.compile(r"^(?P<name>.+?)\s+(?P<best>\d{1,2}\.\d{2}|NBT)\b")


def parse_field(html: str) -> list[Runner]:
    soup = _soup(html)
    found = _runner_table(soup)
    if found is None:
        raise ParseError("Runner table (NAME with Av 1SEC, or a results table) not found")

    table, hs, _ = found
    c_name = _find_col(hs, "name")
    c_rt = _find_col(hs, "r/t", "rt")
    c_tr = _find_col(hs, "trainer")
    c_last = _find_col(hs, "last4", "last5", "form")
    c_td = _find_col(hs, "trk/dist", "trkdist")
    c_sec = _find_col(hs, "av1sec", "1sec")
    c_odds = _find_col(hs, "odds")

    runners: list[Runner] = []
    order = 0
    for tr in _body_rows(table):
        cells = tr.find_all(["td", "th"], recursive=False)
        if len(cells) < 3:
            continue
        row_text = _text(tr)
        order += 1
        # The rug sits before the name (results tables put the placing first).
        box = next((b for c in cells[: max(c_name or 0, 1)] if (b := _box_from_cell(c))), None) or order
        if "vacant box" in row_text.lower():
            continue
        moved = INTO_BOX_RE.search(row_text)
        if moved:
            box = int(moved.group(1))

        def cell(i):
            return _text(cells[i]) if i is not None and i < len(cells) else ""

        name_cell = cells[c_name] if c_name is not None and c_name < len(cells) else cells[1]
        link = name_cell.find("a")
        raw = _text(name_cell)
        name = _text(link) if link and len(_text(link)) > 1 else ""
        best = None
        m = NAME_SPLIT.match(raw)
        if not name:
            name = m.group("name") if m else raw.split(" T:")[0]
        if m and m.group("best") != "NBT":
            best = float(m.group("best"))

        rt = cell(c_rt).upper()
        if not re.fullmatch(r"[A-Z]{1,2}", rt or ""):
            rm = re.search(r"R/T:\s*([A-Z]{1,2})", raw)
            rt = rm.group(1) if rm else ""

        td = cell(c_td)
        tdm = re.match(r"(\d+)\s*:", td)
        odds = cell(c_odds).upper()
        scratched = (
            "scratched" in " ".join(tr.get("class", [])).lower()   # thedogs: tr.race-runner--scratched
            or "SCR" in odds
            or re.search(r"\bSCR\b", row_text) is not None
            or "scratched" in row_text.lower()
        )
        rserve = not moved and ("reserve" in row_text.lower() or box > 8)

        runners.append(
            Runner(
                box=box,
                name=name.strip(),
                trainer=cell(c_tr),
                rt=rt,
                av_first_sec=_float(cell(c_sec)),
                trk_dist_starts=int(tdm.group(1)) if tdm else 0,
                best_td=best,
                last4=cell(c_last),
                scratched=scratched,
                reserve=rserve,
            )
        )
    if not runners:
        raise ParseError("Field table found but no runner rows parsed")
    return runners


# --------------------------------------------------------------------------- short form (past runs)

RUN_TEXT_RE = re.compile(
    r"(?P<plc>\d{1,2})(?:st|nd|rd|th)\s*/\s*(?P<field>\d{1,2})\s+"
    r"(?:(?P<box>\d{1,2})\s+)?(?P<wgt>\d{2}\.\d)\s*kg\s+(?P<dist>\d{3,4})\s*m?\s+"
    r"(?P<date>\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+(?P<track>[A-Z]{2,5})\s+(?P<grade>\S+)\s+"
    r"(?P<time>\d{1,2}\.\d{2})\s+(?P<win>\d{1,2}\.\d{2})\s+(?P<bon>\d{1,2}\.\d{2})\s+"
    r"(?P<sec>\d{1,2}\.\d{2})\s+(?P<mgn>[\d.]+|\S+)\s+(?P<winner>.+?)\s+(?P<pir>[\d-]{1,11})\s+\$"
)


def _parse_date(s: str) -> datetime | None:
    s = s.strip()
    m = re.search(r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}", s)  # "17:27 09 October 2026" -> "09 October 2026"
    if m:
        s = m.group()
    for fmt in ("%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d %b %y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def _runs_from_table(table: Tag) -> list[Run]:
    hs = _header_cells(table)
    c_date = _find_col(hs, "date")
    c_track = _find_col(hs, "track", "trk")
    c_dist = _find_col(hs, "dist")
    c_sec = _find_col(hs, "1sec", "sec1", "split")
    c_pir = _find_col(hs, "pir", "inrun")
    c_plc = _find_col(hs, "plc", "place", "pos")
    c_box = _find_col(hs, "box")
    out = []
    for tr in _body_rows(table):
        tds = tr.find_all(["td", "th"], recursive=False)
        if len(tds) < 5:
            continue
        cells = [_text(c) for c in tds]
        g = lambda i: cells[i] if i is not None and i < len(cells) else ""  # noqa: E731
        dist = re.search(r"\d{3,4}", g(c_dist))
        if not dist:
            continue
        plc = re.match(r"(\d+)", g(c_plc))
        box = _box_from_cell(tds[c_box]) if c_box is not None and c_box < len(tds) else None
        out.append(
            Run(
                date=_parse_date(g(c_date)),
                track=g(c_track).upper().strip(),
                dist=int(dist.group()),
                first_sec=_float(g(c_sec)),
                pir=g(c_pir),
                place=int(plc.group(1)) if plc else None,
                box=box,
            )
        )
    return out


def _runs_from_text(text: str) -> list[Run]:
    out = []
    for m in RUN_TEXT_RE.finditer(text):
        out.append(
            Run(
                date=_parse_date(m["date"]),
                track=m["track"],
                dist=int(m["dist"]),
                first_sec=float(m["sec"]),
                pir=m["pir"],
                place=int(m["plc"]),
                box=int(m["box"]) if m["box"] else None,
            )
        )
    return out


def attach_runs(shortform_html: str, runners: list[Runner]) -> int:
    """Attach past runs from the Short Form page to each runner. Returns runs attached."""
    soup = _soup(shortform_html)
    names = {r.name.lower(): r for r in runners}
    total = 0

    # 1) Table-based layout: each runner has a table with DATE/TRACK/1 SEC headers.
    for t in soup.find_all("table"):
        hs = _header_cells(t)
        if not (any("sec" in h for h in hs) and any("track" in h or h == "trk" for h in hs)):
            continue
        owner = None
        for s in t.find_all_previous(string=True):
            st = s.strip().lower()
            st = re.sub(r"\s*\(\d+\)$", "", st)  # "headmaster (6)" -> grade suffix
            if st in names:
                owner = names[st]
                break
        if owner is None:
            continue
        runs = _runs_from_table(t)
        owner.runs.extend(runs)
        total += len(runs)

    if total:
        _dedupe(runners)
        return sum(len(r.runs) for r in runners)

    # 2) Text fallback: slice the page text between runner names.
    text = _text(soup.body or soup)
    low = text.lower()
    spots = []
    for r in runners:
        i = low.find(r.name.lower())
        if i >= 0:
            spots.append((i, r))
    spots.sort(key=lambda x: x[0])
    for k, (i, r) in enumerate(spots):
        end = spots[k + 1][0] if k + 1 < len(spots) else len(text)
        runs = _runs_from_text(text[i:end])
        r.runs.extend(runs)
    _dedupe(runners)
    return sum(len(r.runs) for r in runners)


def _dedupe(runners: list[Runner]) -> None:
    for r in runners:
        seen, keep = set(), []
        for run in r.runs:
            key = (run.date, run.track, run.dist, run.first_sec)
            if key not in seen:
                seen.add(key)
                keep.append(run)
        keep.sort(key=lambda x: x.date or datetime.min, reverse=True)
        r.runs = keep
