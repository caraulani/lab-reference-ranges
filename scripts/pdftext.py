"""Print text of a PDF page by page with layout. usage: pdftext.py file.pdf [first_page last_page]"""
import sys, pdfplumber
f = sys.argv[1]
with pdfplumber.open(f) as pdf:
    n = len(pdf.pages)
    a = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    b = int(sys.argv[3]) if len(sys.argv) > 3 else n
    for i in range(a - 1, min(b, n)):
        print(f"\n===== PAGE {i+1}/{n} =====")
        print(pdf.pages[i].extract_text(layout=True) or "")
