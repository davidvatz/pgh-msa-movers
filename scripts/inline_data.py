from pathlib import Path

html = Path("index.html").read_text(encoding="utf-8")
data = Path("data.js").read_text(encoding="utf-8")
old = '<script src="data.js"></script>\n  <script>'
new = "<script>" + data + "</script>\n  <script>"
if old not in html:
    raise SystemExit("marker not found")
Path("index.html").write_text(html.replace(old, new, 1), encoding="utf-8")
print("bytes", Path("index.html").stat().st_size)
