"""Regenerate the plain-text layer of every included source from the archived raw files.
Reads sources/registry.csv and sources/files.csv; writes _raw/ranges_text/<source_id>.txt.
PDF pages are labelled '===== PAGE <n>/<N> ====='; multi-file sources use '<file stem>-<n>' (PDF) or '<stem>' (HTML).
usage: uv run --with pdfplumber python -I scripts/extract_text.py"""
import csv, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pdfplumber
from htmltext import convert
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT.parent / "_raw" / "ranges"
OUT = ROOT.parent / "_raw" / "ranges_text"
OUT.mkdir(parents=True, exist_ok=True)
reg = list(csv.DictReader(open(ROOT / "sources" / "registry.csv", encoding="utf-8")))
files = list(csv.DictReader(open(ROOT / "sources" / "files.csv", encoding="utf-8")))
for s in reg:
    sid, layout = s["source_id"], s["text_layout"]
    paths = sorted(RAW / f["local_path"] for f in files if f["source_id"] == sid)
    with open(OUT / f"{sid}.txt", "w", encoding="utf-8") as out:
        for p in paths:
            if layout.startswith("pdf"):
                stem = p.stem.split("_FB-PA")[0]
                with pdfplumber.open(p) as pdf:
                    for i, pg in enumerate(pdf.pages, 1):
                        pid = str(i) if layout == "pdf" else f"{stem}-{i}"
                        out.write(f"\n===== PAGE {pid}/{len(pdf.pages)} =====\n")
                        out.write((pg.extract_text(layout=True) or "") + "\n")
            else:
                pid = "1" if layout == "html" else p.stem
                out.write(f"===== PAGE {pid}/1 =====\n" + convert(p) + "\n")
    print(sid, len(paths), "file(s)")
