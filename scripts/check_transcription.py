"""Check each transcribed row against the archived source text.
usage: python -I scripts/check_transcription.py <lab_id> [<lab_id> ...]
Text files: _raw/ranges_text/<lab_id>.txt, pages split on '===== PAGE n/N ====='.
A row passes when range_as_printed (all whitespace removed) and each numeric
limit occur on the cited page (whitespace removed)."""
import csv, re, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
TXT = ROOT.parent / "_raw" / "ranges_text"
def norm(s):
    s = s.replace("–", "-").replace("−", "-").replace(" ", " ")
    return re.sub(r"\s+", "", s)
def pages(lab):
    t = (TXT / f"{lab}.txt").read_text(encoding="utf-8")
    parts = re.split(r"===== PAGE ([^/\s]+)/\d+ =====", t)
    return {parts[i]: norm(parts[i + 1]) for i in range(1, len(parts), 2)}
def check(lab):
    pg = pages(lab); bad = 0; n = 0
    for r in csv.DictReader(open(ROOT / "transcriptions" / f"{lab}.csv", encoding="utf-8")):
        n += 1
        cited = r["page"].split("|")
        text = "".join(pg.get(p, "") for p in cited)
        miss = [x for x in (r["range_as_printed"], r["low"], r["high"]) if x and norm(x) not in text and norm(x).replace(".", ",") not in text]
        if miss:
            bad += 1; print(f"FAIL {lab} p{r['page']} {r['analyte_printed']} {r['sex']}: {miss}")
    print(f"{lab}: {n} rows, {bad} failures")
    return bad
if __name__ == "__main__":
    sys.exit(1 if sum(check(l) for l in sys.argv[1:]) else 0)
