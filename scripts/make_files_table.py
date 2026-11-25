"""One-off helper (network): list every archived file used by an included source, with SHA-256,
original URL, the URL actually fetched, and an existing Wayback capture if the availability API knows one.
Writes sources/files.csv. No new captures are requested. usage: python -I scripts/make_files_table.py"""
import csv, hashlib, json, pathlib, time, urllib.parse, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT.parent / "_raw" / "ranges"
INCLUDED = [p.stem for p in (ROOT / "transcriptions").glob("*.csv") if not p.stem.startswith("_")]
log = [l.rstrip("\n").split("\t") for l in open(RAW / "fetch_log.tsv", encoding="utf-8")]
latest = {}
for lab, url, rel, code, sha, ts in log:
    if code == "200" and lab in INCLUDED and (RAW / rel).exists():
        latest[rel] = (lab, url, ts)
def wayback(url):
    q = "https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
    try:
        with urllib.request.urlopen(urllib.request.Request(q, headers={"User-Agent": "reference-interval-snapshot"}), timeout=30) as r:
            s = json.load(r).get("archived_snapshots", {}).get("closest") or {}
            return s.get("url", ""), s.get("timestamp", "")
    except Exception:
        return "", ""
rows = []
for rel, (lab, url, ts) in sorted(latest.items()):
    if "web.archive.org/web/" in url:
        orig = url.split("id_/", 1)[1]
        wb, wts = url.replace("id_/", "/"), url.split("/web/")[1].split("id_")[0]
    else:
        orig = url
        wb, wts = wayback(url); time.sleep(1)
    sha = hashlib.sha256((RAW / rel).read_bytes()).hexdigest()
    rows.append(dict(source_id=lab, local_path=rel, original_url=orig, retrieved_url=url, retrieved_utc=ts,
                     sha256=sha, bytes=(RAW / rel).stat().st_size, wayback_url=wb, wayback_timestamp=wts))
with open(ROOT / "sources" / "files.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows), "files")
