"""Render one PDF page to PNG for visual checking. usage: render_page.py file.pdf page out.png [scale]"""
import sys, pypdfium2 as pdfium
pdf = pdfium.PdfDocument(sys.argv[1]); p = pdf[int(sys.argv[2]) - 1]
p.render(scale=float(sys.argv[4]) if len(sys.argv) > 4 else 1.6).to_pil().save(sys.argv[3])
