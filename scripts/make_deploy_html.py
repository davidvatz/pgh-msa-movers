from pathlib import Path

root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text(encoding="utf-8")
html = html.replace(
    '<script src="data.js"></script>',
    '<script src="https://cdn.jsdelivr.net/gh/davidvatz/pgh-msa-movers@main/data.js"></script>',
)
out = root / "_deploy.html"
out.write_text(html, encoding="utf-8")
print(out.stat().st_size)
