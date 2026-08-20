from pathlib import Path

html = Path("index.html").read_text(encoding="utf-8")
start = html.find("<script>window.MSA_ROWS=")
end = html.find("</script>\n  <script>", start)
if start < 0 or end < 0:
    raise SystemExit(f"markers {start} {end}")
html = html[:start] + '<script src="data.js"></script>\n  <script>' + html[end + len("</script>\n  <script>") :]
Path("index.html").write_text(html, encoding="utf-8")
print("restored", Path("index.html").stat().st_size)
