"""Fill blank 'page' cells: find the page whose single text line holds both the
analyte_printed and range_as_printed (whitespace-insensitive). usage: locate.py <lab_id>"""
import csv, re, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
TXT = ROOT.parent / "_raw" / "ranges_text"
n = lambda s: re.sub(r"\s+", "", s.replace("‐", "-").replace("–", "-"))
lab = sys.argv[1]
t = (TXT / f"{lab}.txt").read_text(encoding="utf-8")
parts = re.split(r"===== PAGE ([^/\s]+)/\d+ =====", t)
pages = {parts[i]: [n(l) for l in parts[i + 1].splitlines()] for i in range(1, len(parts), 2)}
fn = ROOT / "transcriptions" / f"{lab}.csv"
rows = list(csv.DictReader(open(fn, encoding="utf-8")))
for r in rows:
    if r["page"]:
        continue
    a, g = n(r["analyte_printed"]), n(r["range_as_printed"])
    hits = [p for p, ls in pages.items() if any(a in l and g in l and n(r.get("age_printed","")) in l for l in ls)]
    if len(hits) >= 1:
        r["page"] = str(hits[0])
    if len(hits) != 1:
        print("check:", r["analyte_printed"], r["sex"], r["age_printed"], hits)
w = csv.DictWriter(open(fn, "w", newline="", encoding="utf-8"), fieldnames=list(rows[0].keys()))
w.writeheader(); w.writerows(rows)
