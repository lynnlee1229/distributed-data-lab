#!/usr/bin/env python3
"""Check local links, public allowlist, ZIP isolation, translated pages and privacy markers."""
import hashlib, json, re, sys, zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "build/site"
OUT = SITE / "distributed-data-lab"
errors = []


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = set()
        self.h1 = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if "id" in a:
            self.ids.add(a["id"])
        for attr in ["href", "src"]:
            if attr in a:
                self.urls.append(a[attr])


manifest = json.loads((OUT / "public-files.json").read_text())["files"]
actual = {str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file()}
assert actual == set(manifest) | {"public-files.json"}, "Export manifest differs"
for name, record in manifest.items():
    data = (OUT / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != record["sha256"]:
        errors.append("Hash " + name)
    if name.endswith((".html", ".js", ".mjs", ".json", ".css", ".xml")):
        text = data.decode()
        if re.search(
            r"/(?:Users)/|/(?:home)/(?!runner)|sk-proj[-]|gh[pousr]_[A-Za-z0-9]{20}|BEGIN [A-Z ]*PRIVATE KEY|app\.notion\.com|\.(?:colima)/|\.(?:zshrc)",
            text,
        ):
            errors.append("Privacy marker " + name)
    if name.endswith(".html"):
        parsed = Links()
        parsed.feed(data.decode())
        if name not in ["index.html"] and parsed.h1 != 1:
            errors.append("Need exactly one h1 " + name)
        if name.startswith("en/"):
            other = OUT / ("zh/" + name[3:])
            if not other.exists():
                errors.append("Missing translation " + name)
        for url in parsed.urls:
            p = urlsplit(url)
            if p.scheme or p.netloc:
                continue
            if p.path in ["/websites/", "/zh/websites/"]:
                continue
            target = (
                SITE / unquote(p.path.lstrip("/"))
                if p.path.startswith("/")
                else (OUT / name).parent / unquote(p.path)
            )
            if not p.path:
                target = OUT / name
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                errors.append("Broken link " + name + " -> " + url)
            elif p.fragment and target.suffix == ".html":
                doc = Links()
                doc.feed(target.read_text())
                if p.fragment not in doc.ids:
                    errors.append("Broken anchor " + url)
with zipfile.ZipFile(OUT / "downloads/distributed-data-lab.zip") as z:
    for name in z.namelist():
        if any(part in ["build", ".venv", ".git", ".env"] for part in Path(name).parts):
            errors.append("Private runtime in ZIP " + name)
        if name.endswith((".py", ".mjs", ".md", ".json", ".yml")):
            if re.search(
                r"/(?:Users)/|app\.notion\.com|sk-proj[-]|BEGIN [A-Z ]*PRIVATE KEY",
                z.read(name).decode(),
            ):
                errors.append("Privacy marker in ZIP " + name)
if errors:
    raise SystemExit("\n".join(errors))
print(
    "PASS:",
    len(manifest),
    "export files; links, translations, privacy markers, hashes and isolated companion ZIP",
)
