"""Build docs/index.html (a standalone web page) from gastos.html (the artifact source).

The artifact viewer wraps gastos.html in its own <html><head> skeleton; a normal
web host needs the full document, so this adds it. Run after editing gastos.html:

    python build_site.py
"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "gastos.html"), encoding="utf-8").read()

title = re.search(r"<title>(.*?)</title>", src).group(1)
head_parts = re.findall(r"<link[^>]*>", src)
style = re.search(r"<style>.*?</style>", src, re.S).group(0)
body = src.split("</style>", 1)[1]

reset = """<style>
:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
body{margin:0;font:14px system-ui,-apple-system,"Segoe UI",sans-serif;background:#fafaf8}
img{max-width:100%}
[hidden]{display:none!important}
</style>"""

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="Sort a bank or card statement CSV into spending categories on your phone. Nothing is uploaded or stored.">
<title>{title}</title>
{chr(10).join(head_parts)}
{reset}
{style}
</head>
<body>{body}
</body>
</html>
"""
os.makedirs(os.path.join(HERE, "docs"), exist_ok=True)
out = os.path.join(HERE, "docs", "index.html")
open(out, "w", encoding="utf-8").write(html)
print("wrote", out, len(html), "bytes")
