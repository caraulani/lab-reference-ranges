"""Concatenate several PDFs into one text file; page ids are '<stem>-<n>'.
usage: pdftext_multi.py out.txt file1.pdf file2.pdf ..."""
import sys, pathlib, pdfplumber
out = open(sys.argv[1], "w", encoding="utf-8")
for f in sorted(sys.argv[2:]):
    stem = pathlib.Path(f).stem.split("_FB-PA")[0]
    with pdfplumber.open(f) as pdf:
        for i, pg in enumerate(pdf.pages, 1):
            out.write(f"\n===== PAGE {stem}-{i}/{len(pdf.pages)} =====\n")
            out.write((pg.extract_text(layout=True) or "") + "\n")
