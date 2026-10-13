"""Build one self-contained HTML page per meeting (images embedded, works offline / on phone)."""

from __future__ import annotations

import base64
import html
from datetime import datetime
from pathlib import Path

from . import config
from .model import RaceMap

CSS = """
:root{--bg:#f4f6f5;--card:#fff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--accent:#0f3d2e}
@media (prefers-color-scheme:dark){:root{--bg:#0b1210;--card:#111c18;--ink:#e8efe9;--muted:#93a69c;--line:#22332b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{padding:20px 16px 8px;max-width:1100px;margin:auto}h1{margin:0;font-size:24px}
.sub{color:var(--muted);font-size:13px}
nav{position:sticky;top:0;background:var(--bg);padding:8px 16px;z-index:5;max-width:1100px;margin:auto;display:flex;gap:6px;flex-wrap:wrap}
nav a{padding:5px 10px;border-radius:999px;background:var(--card);border:1px solid var(--line);color:var(--ink);text-decoration:none;font-weight:600;font-size:13px}
main{max-width:1100px;margin:auto;padding:0 16px 40px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;margin:14px 0;overflow:hidden}
.card img{width:100%;display:block}
.imgwrap{overflow-x:auto;background:#0f3d2e}
@media (max-width:640px){.imgwrap img{width:760px;max-width:none}.basis-text,.trainer{display:none}th,td{padding:6px 4px}}
.body{padding:12px 16px}
.notes{margin:4px 0 10px;padding-left:18px}.notes li{margin:2px 0}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:6px 6px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase}
td.num{font-variant-numeric:tabular-nums}
.rug{display:inline-flex;width:24px;height:24px;border-radius:50%;align-items:center;justify-content:center;font-weight:800;font-size:13px;border:1.5px solid #000}
.conf{font-size:12px;padding:1px 7px;border-radius:999px;border:1px solid var(--line);color:var(--muted)}
.conf.high{color:#15803d;border-color:#15803d}.conf.med{color:#b45309;border-color:#b45309}
.scr{color:var(--muted);font-size:13px;margin-top:6px}
.wrap{overflow-x:auto}
"""


def _rug(box: int) -> str:
    face, num, striped = config.RUGS.get(box, ("#888", "#fff", False))
    bg = (f"repeating-linear-gradient(0deg,#000 0 3px,{face} 3px 6px)" if striped else face)
    inner = (f'<span style="background:{face};border-radius:50%;padding:0 3px;line-height:1.1">{box}</span>'
             if striped else str(box))
    return f'<span class="rug" style="background:{bg};color:{num}">{inner}</span>'


def build(meeting_title: str, date: str, maps: list[RaceMap], images: dict[int, Path], out: Path) -> Path:
    nav = "".join(f'<a href="#r{m.race.number}">R{m.race.number}</a>' for m in maps)
    cards = []
    for m in maps:
        r = m.race
        img = ""
        p = images.get(r.number)
        if p and p.exists():
            b64 = base64.b64encode(p.read_bytes()).decode()
            img = f'<div class=imgwrap><img alt="Speedmap race {r.number}" src="data:image/png;base64,{b64}"></div>'
        rows = []
        for d in m.dogs:
            sec = f"{d.est_sec:.2f}" if d.est_sec else "–"
            rows.append(
                f"<tr><td class=num>{d.pos}</td><td>{_rug(d.runner.box)}</td>"
                f"<td><b>{html.escape(d.runner.display)}</b><div class='sub trainer'>{html.escape(d.runner.trainer)}</div></td>"
                f"<td>{html.escape(d.runner.rt or '–')}</td><td class=num>{sec}</td>"
                f"<td class=num>{d.lengths:.1f}L</td>"
                f"<td><span class='conf {d.conf}'>{d.conf}</span> <span class='sub basis-text'>{html.escape(d.basis)}</span></td></tr>"
            )
        scr = [x for x in r.runners if x.scratched]
        scr_html = (f'<div class=scr>Scratched: {", ".join(f"{x.box}. {html.escape(x.display)}" for x in scr)}</div>'
                    if scr else "")
        notes = "".join(f"<li>{html.escape(n)}</li>" for n in m.notes)
        meta = " · ".join(x for x in [f"{r.dist}m" if r.dist else "", r.grade, r.time,
                                       "already run" if r.finished else ""] if x)
        cards.append(f"""
<section class=card id="r{r.number}">
  {img}
  <div class=body>
    <h2 style="margin:4px 0 2px;font-size:18px">R{r.number} · {html.escape(r.name)}</h2>
    <div class=sub>{html.escape(meta)} · <a href="{html.escape(r.url)}">form</a></div>
    <ul class=notes>{notes}</ul>
    <div class=wrap><table>
      <tr><th>Pos</th><th>Box</th><th>Dog</th><th>R/T</th><th>1st split</th><th>Behind</th><th>Basis</th></tr>
      {''.join(rows)}
    </table></div>
    {scr_html}
  </div>
</section>""")

    stamp = datetime.now(config.BRISBANE).strftime("%a %d %b %Y, %I:%M %p")  # Brisbane even on a UTC server
    page = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{html.escape(meeting_title)} speedmaps {date}</title><style>{CSS}</style></head>
<body><header><h1>{html.escape(meeting_title)} — Speedmaps</h1>
<div class=sub>{date} · updated {stamp} · R/T = running trait (E/G/F/S/R) + line (Rail/Middle/Wide/Straight)</div></header>
<nav>{nav}</nav><main>{''.join(cards)}</main>
<script>document.querySelectorAll('.imgwrap').forEach(w=>w.scrollLeft=w.scrollWidth)</script></body></html>"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out
