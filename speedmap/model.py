"""Early-speed model: where each dog should be at the first split / first turn."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass, field
from statistics import mean

from . import config
from .parse import Race, Runner


@dataclass
class MapDog:
    runner: Runner
    est_sec: float | None       # estimated 1st split (s) at this track/distance
    lengths: float = 0.0        # lengths behind the leader at the first split
    lane: float = 0.0           # 1 = rail ... 8 = widest
    pos: int = 0                # predicted early position
    conf: str = "low"           # high / med / low
    basis: str = ""             # short note on what the estimate is based on
    n_sec: int = 0
    avg_first_pos: float | None = None


@dataclass
class RaceMap:
    race: Race
    dogs: list[MapDog]
    notes: list[str] = field(default_factory=list)
    leader_gap: float = 0.0


def _matching_runs(r: Runner, dist: int | None, codes: Collection[str]):
    """Recent runs with a split at this exact track (code) and distance."""
    if not dist:
        return []
    return [
        run for run in r.runs
        if run.dist == dist and run.track in codes and run.first_sec
    ][: config.RECENT_RUNS]


def _weighted(vals: list[float]) -> float:
    ws = [0.85 ** i for i in range(len(vals))]  # most recent first, weighted highest
    return sum(v * w for v, w in zip(vals, ws)) / sum(ws)


def _quantile(sorted_vals: list[float], q: float) -> float:
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    q = min(max(q, 0.0), 1.0)
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def build_map(race: Race, codes: Collection[str]) -> RaceMap:
    """codes: the track code(s) of the race's track (config.TRACKS); splits only count from those."""
    starters = [r for r in race.runners if not r.scratched and not r.reserve]
    dogs: list[MapDog] = []

    for r in starters:
        runs = _matching_runs(r, race.dist, codes)
        secs = [run.first_sec for run in runs]
        recent_pos = [run.first_pos for run in r.runs[: config.RECENT_RUNS] if run.first_pos]
        avg_pos = mean(recent_pos) if recent_pos else None

        est, n, basis = None, 0, ""
        if secs:
            est = 0.7 * _weighted(secs) + 0.3 * min(secs)
            n = len(secs)
            basis = f"{n} split{'s' if n != 1 else ''} at {race.dist}m"
            if r.av_first_sec and n < 2:
                est = (est + r.av_first_sec) / 2
                basis += f" + site avg ({r.trk_dist_starts} starts)"
                n = max(n, r.trk_dist_starts)
        elif r.av_first_sec:
            est = r.av_first_sec
            n = r.trk_dist_starts or 1
            basis = f"site avg 1st split ({n} start{'s' if n != 1 else ''})"

        conf = "high" if n >= config.MIN_RUNS_HIGH_CONF else ("med" if n else "low")
        dogs.append(MapDog(runner=r, est_sec=est, conf=conf, basis=basis, n_sec=n, avg_first_pos=avg_pos))

    known = sorted(d.est_sec for d in dogs if d.est_sec)
    field_n = max(len(dogs), 2)

    # Dogs without sectionals here: estimate from early positions in recent runs, then trait.
    for d in dogs:
        if d.est_sec is not None:
            continue
        trait_pos = config.TRAIT_DEFAULT_POSITION.get(d.runner.trait)
        if d.avg_first_pos is not None:
            pos = d.avg_first_pos if trait_pos is None else (d.avg_first_pos + trait_pos) / 2
            d.basis = f"early pos avg {d.avg_first_pos:.1f} + trait (no splits here)"
        else:
            pos = config.TRAIT_DEFAULT_POSITION.get(d.runner.trait, 5.0)
            d.basis = f"running trait '{d.runner.rt or '?'}' only" if d.runner.rt else "no form — guess"
        frac = (pos - 1) / 7
        if len(known) >= 2:
            d.est_sec = _quantile(known, frac) + 0.03  # small penalty for uncertainty
        else:
            d.lengths = (pos - 1) * 1.2

    # Convert seconds to lengths behind the fastest.
    if any(d.est_sec for d in dogs):
        fastest = min(d.est_sec for d in dogs if d.est_sec)
        for d in dogs:
            if d.est_sec:
                d.lengths = (d.est_sec - fastest) / config.SEC_PER_LENGTH

    # Optional box adjustment from config.
    adj = config.BOX_ADJUST_LENGTHS.get(race.dist or 0, {})
    for d in dogs:
        d.lengths = min(max(d.lengths + adj.get(d.runner.box, 0.0), 0.0), 12.0)
    if dogs:
        lead = min(d.lengths for d in dogs)
        for d in dogs:
            d.lengths -= lead

    # Lane by the first turn: start from the box, drift toward preferred running line.
    for d in dogs:
        box = d.runner.box
        pref = d.runner.lane_pref
        target = {"R": 1.0, "M": 4.5, "W": min(box + 2, 8.0)}.get(pref, float(box))
        d.lane = box + (target - box) * config.LANE_DRIFT

    dogs.sort(key=lambda d: (d.lengths, d.runner.box))
    for i, d in enumerate(dogs, 1):
        d.pos = i

    rm = RaceMap(race=race, dogs=dogs)
    rm.notes = _notes(dogs)
    if len(dogs) >= 2:
        rm.leader_gap = dogs[1].lengths - dogs[0].lengths
    return rm


def _notes(dogs: list[MapDog]) -> list[str]:
    notes: list[str] = []
    if len(dogs) < 2:
        return notes
    a, b = dogs[0], dogs[1]
    gap = b.lengths - a.lengths
    nm = lambda d: f"{d.runner.display} ({d.runner.box})"  # noqa: E731
    if gap >= 1.5:
        notes.append(f"Clear early leader: {nm(a)} — about {gap:.1f}L up at the first split.")
    elif gap >= 0.5:
        notes.append(f"Slight edge to {nm(a)} over {nm(b)} ({gap:.1f}L).")
    else:
        notes.append(f"Lead is contested between {nm(a)} and {nm(b)}.")

    near = [d for d in dogs if d.lengths <= 1.0]
    if len(near) >= 3:
        notes.append(f"Hot early pace — {len(near)} dogs within a length of the lead.")

    for d in dogs:
        if d.runner.lane_pref == "R" and d.runner.box >= 5 and d.pos > 2:
            notes.append(f"{nm(d)} is a railer drawn wide and not quick enough to cross cleanly — trouble risk.")
        if d.runner.lane_pref == "W" and d.runner.box <= 3:
            inside_fast = [o for o in dogs if o.runner.box > d.runner.box and o.lengths < d.lengths - 0.5]
            if inside_fast:
                notes.append(f"{nm(d)} likes it wide but is drawn inside quicker dogs — may get carried/checked.")

    for i, x in enumerate(dogs):
        for y in dogs[i + 1:]:
            if abs(x.lengths - y.lengths) < 0.6 and abs(x.lane - y.lane) < 1.3 and x.pos <= 5:
                notes.append(f"Possible bump at the first turn: {nm(x)} & {nm(y)}.")

    guessed = [nm(d) for d in dogs if d.conf == "low"]
    if guessed:
        notes.append("Estimated (no sectionals at this trip): " + ", ".join(guessed) + ".")
    return notes
