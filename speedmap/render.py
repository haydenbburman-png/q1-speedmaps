"""Draw a speedmap PNG for one race."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import config  # noqa: E402
from .model import RaceMap  # noqa: E402

BG = "#0f3d2e"        # track green
LANE = "#14523d"
INK = "#f8fafc"
MUTED = "#a7c4b8"


def _spread(points: list[list[float]]) -> None:
    """Nudge overlapping dogs apart so every rug is readable."""
    for _ in range(40):
        moved = False
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                xi, yi = points[i]
                xj, yj = points[j]
                if abs(xi - xj) < 0.95 and abs(yi - yj) < 0.95:
                    # push the outer dog wider (or the inner one in, if already wide)
                    if yj >= yi:
                        points[j][1] = min(points[j][1] + 0.5, 8.6)
                        if points[j][1] >= 8.6:
                            points[i][1] = max(points[i][1] - 0.5, 0.6)
                    else:
                        points[i][1] = min(points[i][1] + 0.5, 8.6)
                    moved = True
        if not moved:
            break


def draw(rm: RaceMap, meeting_title: str, out_path: Path) -> Path:
    race = rm.race
    dogs = rm.dogs
    span = max(4.5, max((d.lengths for d in dogs), default=0) + 1.0)

    fig, ax = plt.subplots(figsize=(12, 5.6), dpi=130)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # lanes
    for lane in range(1, 9):
        if lane % 2 == 0:
            ax.axhspan(lane - 0.5, lane + 0.5, color=LANE, zorder=0)
    ax.axhline(0.45, color="#e2e8f0", lw=4, zorder=1)
    ax.text(-span - 0.6, 0.45, "RAIL", color=INK, fontsize=9, fontweight="bold", va="center", ha="left",
            bbox=dict(boxstyle="round,pad=0.25", fc=BG, ec="none"), zorder=2)

    # length grid (leader at x=0, dogs behind are negative)
    for L in range(0, int(span) + 1, 1):
        ax.axvline(-L, color="#ffffff", alpha=0.07 if L else 0.25, lw=1, zorder=0)
        ax.text(-L, 8.95, "Leader" if L == 0 else f"{L}L", color=MUTED, fontsize=8, ha="center", va="top")

    pts = [[-d.lengths, d.lane] for d in dogs]
    _spread(pts)

    for d, (x, y) in zip(dogs, pts):
        face, num_col, striped = config.RUGS.get(d.runner.box, ("#888888", "#ffffff", False))
        low = d.conf == "low"
        ax.scatter([x], [y], s=820, c=face, edgecolors="#000000", linewidths=1.6, zorder=4,
                   hatch="---" if striped else None, alpha=0.8 if low else 1.0,
                   linestyle="--" if low else "-")
        ax.text(x, y, str(d.runner.box), color=num_col, fontsize=13, fontweight="bold",
                ha="center", va="center", zorder=5,
                bbox=dict(boxstyle="circle,pad=0.12", fc=face, ec="none", alpha=0.9) if striped else None)
        label = d.runner.display
        if len(label) > 16:
            label = label[:15] + "…"
        ax.text(x, y + 0.46, label + (" *" if low else ""), color=INK, fontsize=8.2,
                ha="center", va="top", zorder=6, fontweight="bold")

    # direction arrow
    ax.annotate("", xy=(1.1, -0.35), xytext=(-1.6, -0.35),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6), annotation_clip=False)
    ax.text(-1.75, -0.35, "running →  first turn", color=MUTED, fontsize=8.5, ha="right", va="center")

    ax.set_xlim(-span - 0.8, 1.3)
    ax.set_ylim(9.0, -0.7)  # rail on top
    ax.axis("off")

    head = f"{meeting_title}  ·  R{race.number}"
    sub = " · ".join(x for x in [f"{race.dist}m" if race.dist else "", race.grade, race.time,
                                 "already run" if race.finished else ""] if x)
    fig.text(0.015, 0.955, head, color=INK, fontsize=17, fontweight="bold", va="top")
    fig.text(0.015, 0.895, f"{race.name}   {sub}", color=MUTED, fontsize=10.5, va="top")
    order = "  ›  ".join(str(d.runner.box) for d in dogs)
    fig.text(0.985, 0.955, "Early order", color=MUTED, fontsize=9, ha="right", va="top")
    fig.text(0.985, 0.905, order, color=INK, fontsize=15, fontweight="bold", ha="right", va="top")
    fig.text(0.015, 0.02, "* estimated — no sectionals at this track/distance.   Position = predicted spot at the first split; "
             "lane = drift toward each dog's preferred line.", color=MUTED, fontsize=7.5)

    fig.subplots_adjust(left=0.01, right=0.99, top=0.84, bottom=0.07)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, facecolor=BG)
    plt.close(fig)
    return out_path
