"""HTML to plain text, one table row per line, cells joined by ' | '.
One file: page id '1'. Several files: page id = file stem.
usage: htmltext.py in.html [in2.html ...] > out.txt"""
import sys, re, html, pathlib
def convert(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S | re.I)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"</t[dh]>", " | ", t, flags=re.I)
    t = re.sub(r"</tr>|<br\s*/?>|</p>|</h\d>|</li>|</div>", "\n", t, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t)
if __name__ == "__main__":
  files = sys.argv[1:]
  for f in sorted(files):
    pid = "1" if len(files) == 1 else pathlib.Path(f).stem
    print(f"===== PAGE {pid}/1 =====")
    print(convert(f))
