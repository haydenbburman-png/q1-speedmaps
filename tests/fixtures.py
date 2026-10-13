"""Sample pages built from real Q1 Lakeside R5 data (13 Oct 2026, 390m, Grade 6).

They mimic thedogs.com.au layout closely enough to test parsing + the model offline.
The real site's markup may differ — if the live parse fails, run `python run.py --debug`
and update speedmap/parse.py against the saved pages in debug/.
"""

DATE = "2026-10-13"
SLUG = "ladbrokes-q1-lakeside"
RACE5 = f"/racing/{SLUG}/{DATE}/5/engineering-by-stp-consultants"

# box, name, best T/D, trainer, R/T, last4, trk/dist, av1sec, last start
FIELD = [
    (1, "Do The Maths", "22.45", "Matthew Heilbronn", "FM", "7388", "6: 0-0-2", "6.14", "8th/8350m 24 Sep QST"),
    (2, "Canya Let Loose", "21.65", "Gerard Agius", "FM", "2157", "2: 1-1-0", "6.04", "7th/7520m 01 Oct QTT"),
    (3, "Maddie's Lakoda", "21.79", "Kirsty Druery", "FM", "11", "2: 2-0-0", "6.07", "1st/8390m 09 Oct QOT"),
    (4, "Hilltop Smile", "22.53", "Colin Graham", "FM", "4816", "3: 0-0-0", "6.28", "6th/8390m 06 Oct QOT"),
    (5, None, None, None, None, None, None, None, None),  # vacant
    (6, "Paw Queston", "NBT", "Craig Roberts", "SR", "4347", "0: 0-0-0", "N/A", "7th/7457m 19 Sep QOT"),
    (7, "Headmaster", "21.85", "Karen Daniels", "RM", "1785", "4: 1-0-0", "6.12", "5th/6520m 04 Oct QTT"),
    (8, "Akuli Phoenix", "22.39", "Karen Tribe", "RM", "5385", "3: 0-0-0", "6.25", "5th/7352m 06 Oct QOT"),
]

# name -> runs (place, dist, date, track, 1sec, pir)
RUNS = {
    "Do The Maths": [
        ("8th/8", 350, "24 Sep 2026", "QST", "3.98", "8"),
        ("8th/8", 300, "21 Sep 2026", "QST", "6.69", "28"),
        ("3rd/8", 352, "15 Sep 2026", "QOT", "4.01", "113"),
        ("7th/8", 350, "10 Sep 2026", "QST", "4.07", "557"),
        ("8th/8", 300, "07 Sep 2026", "QST", "6.65", "28"),
    ],
    "Canya Let Loose": [
        ("7th/7", 520, "01 Oct 2026", "QTT", "5.35", "6667"),
        ("5th/8", 457, "19 Sep 2026", "QOT", "4.55", "8775"),
        ("1st/6", 390, "28 Aug 2026", "QOT", "5.92", "111"),
        ("2nd/8", 390, "21 Aug 2026", "QOT", "6.15", "322"),
    ],
    "Maddie's Lakoda": [
        ("1st/8", 390, "09 Oct 2026", "QOT", "6.12", "111"),
        ("1st/7", 390, "02 Oct 2026", "QOT", "6.07", "111"),
    ],
    "Hilltop Smile": [
        ("6th/8", 390, "06 Oct 2026", "QOT", "6.22", "646"),
        ("1st/4", 350, "28 Sep 2026", "GRAF", "4.19", "111"),
        ("8th/8", 390, "03 Jul 2026", "QOT", "6.34", "748"),
        ("4th/8", 390, "26 Jun 2026", "QOT", "6.28", "434"),
    ],
    "Paw Queston": [
        ("7th/7", 457, "19 Sep 2026", "QOT", "4.55", "7777"),
        ("4th/6", 457, "01 Sep 2026", "QOT", "4.51", "5554"),
        ("3rd/5", 450, "22 Jul 2026", "BAL", "", "3"),
        ("4th/7", 450, "15 Jul 2026", "BAL", "", "4"),
        ("6th/7", 525, "08 Jul 2026", "MEA", "5.33", "6"),
        ("1st/8", 515, "27 Apr 2026", "SAN", "", "1"),
    ],
    "Headmaster": [
        ("5th/6", 520, "04 Oct 2026", "QTT", "5.34", "6665"),
        ("8th/8", 520, "27 Sep 2026", "QTT", "5.17", "3888"),
        ("7th/8", 352, "15 Sep 2026", "QOT", "4.20", "887"),
        ("1st/8", 390, "04 Sep 2026", "QOT", "5.96", "111"),
        ("4th/8", 457, "21 Jul 2026", "QOT", "4.42", "3234"),
    ],
    "Akuli Phoenix": [
        ("5th/7", 352, "06 Oct 2026", "QOT", "4.06", "465"),
        ("8th/8", 390, "22 Sep 2026", "QOT", "6.27", "258"),
        ("3rd/8", 352, "15 Sep 2026", "QOT", "4.02", "233"),
        ("5th/6", 390, "08 Sep 2026", "QOT", "6.24", "455"),
        ("5th/8", 352, "25 Aug 2026", "QOT", "4.12", "755"),
        ("1st/8", 352, "10 Jun 2026", "QOT", "4.07", "121"),
    ],
}


def day_page() -> str:
    return f"""<html><body><h2>Ladbrokes Q1 Lakeside</h2>
<a href="{RACE5}?trial=false">Engineering by Stp Consultants</a>
<a href="/racing/bulli/{DATE}/1/some-race?trial=false">Bulli R1</a></body></html>"""


def field_page() -> str:
    rows = []
    for box, name, best, tr, rt, l4, td, sec, last in FIELD:
        if name is None:
            rows.append(f'<tr><td><img src="/rugs/rug-{box}.png"></td><td>Vacant Box</td>'
                        + "<td></td>" * 8 + "<td>SCR</td></tr>")
            continue
        rows.append(
            f'<tr><td><img src="/rugs/rug-{box}.png" alt=""></td>'
            f'<td><a href="#">{name}</a> <span>{best}</span> T: {tr} R/T: {rt}</td>'
            f"<td>{rt}</td><td>6</td><td>{tr}</td><td>{l4}</td><td>{td}</td><td>{sec}</td>"
            f"<td>{last}</td><td>N/A</td><td></td></tr>"
        )
    return f"""<html><body>
<div class="race-header">R5 Engineering by Stp Consultants 6th Grade 390m</div>
<div>16:39 13 Oct</div>
<table><thead><tr><th></th><th>NAME</th><th>R/T</th><th>G</th><th>TRAINER</th><th>LAST 4</th>
<th>TRK/DIST</th><th>Av 1SEC</th><th>LAST START</th><th>VIDEO</th><th>Odds</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></body></html>"""


def shortform_page(as_tables: bool = True) -> str:
    blocks = []
    for name, runs in RUNS.items():
        if as_tables:
            trs = "".join(
                f"<tr><td>{d}</td><td>{p}</td><td></td><td>27.0kg</td><td>{dist}</td><td>{t}</td>"
                f"<td>6</td><td>22.00</td><td>21.90</td><td>21.50</td><td>{s}</td><td>1.0</td><td>$5.00</td><td>{pir}</td></tr>"
                for p, dist, d, t, s, pir in runs
            )
            blocks.append(
                f"<h3>{name}</h3><table><thead><tr><th>DATE</th><th>PLC</th><th>BOX</th><th>WEIGHT</th>"
                f"<th>DIST</th><th>TRACK</th><th>GRADE</th><th>TIME</th><th>WIN</th><th>BON</th><th>1 SEC</th>"
                f"<th>MGN</th><th>SP</th><th>PIR</th></tr></thead><tbody>{trs}</tbody></table>"
            )
        else:
            lines = "".join(
                f"<div>{p} 27.0kg {dist} {d} {t} 6 22.00 21.90 21.50 {s or '0.00'} 1.00 Some Winner {pir} $5.00</div>"
                for p, dist, d, t, s, pir in runs
            )
            blocks.append(f"<h3>{name}</h3>{lines}")
    return "<html><body>" + "".join(blocks) + "</body></html>"
