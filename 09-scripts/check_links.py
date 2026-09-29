#!/usr/bin/env python3
"""Check every link in the built site: internal targets exist, external return 200/3xx."""
import os, re, sys, json, urllib.request, urllib.error, concurrent.futures as cf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

pages = sorted(os.path.join(SITE, p) for p in os.listdir(SITE) if p.endswith((".html", ".txt", ".xml")))
int_re, ext_re = {}, {}

def add(d, u, src):
    if u.startswith(("http://", "https://")):
        ext_re.setdefault(u.split("#")[0], set()).add(src)
    elif u.startswith(("#", "mailto:", "javascript:", "data:")):
        pass
    else:
        int_re.setdefault(u.split("#")[0], set()).add(src)

for p in pages:
    name = os.path.basename(p)
    txt = open(p, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r'(?:href|src)="([^"]+)"', txt):
        add(None, m.group(1), name)
    if name.endswith((".json",)):
        continue
    for m in re.finditer(r'https?://[^\s"\'<>)\]]+', txt):
        u = m.group(0).rstrip(".,;")
        if u not in ext_re:
            ext_re.setdefault(u, set()).add(name)

SELF = "nosytlabs.github.io"
ext_re = {u: v for u, v in ext_re.items() if SELF not in u}

missing = []
for u, srcs in int_re.items():
    if u.startswith("/"):
        target = os.path.join(ROOT, u.lstrip("/"))
    else:
        target = os.path.normpath(os.path.join(SITE, u))
    if not os.path.exists(target):
        missing.append((u, sorted(srcs)))
print("== internal references: %d unique, %d missing" % (len(int_re), len(missing)))
for u, s in missing:
    print("  MISSING", u, "<-", ",".join(s))

def head(u):
    try:
        req = urllib.request.Request(u, headers=UA, method="GET")
        with urllib.request.urlopen(req, timeout=25) as r:
            r.read(2048)
            return (r.status, r.geturl())
    except urllib.error.HTTPError as e:
        return (e.code, u)
    except Exception as e:
        return (str(e)[:60], u)

results = {}
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(head, u): u for u in ext_re}
    for f in cf.as_completed(futs):
        results[futs[f]] = f.result()[0]
bad = {u: c for u, c in results.items() if not (isinstance(c, int) and 200 <= c < 400)}
print("== external links: %d unique, %d not OK" % (len(results), len(bad)))
for u, c in sorted(bad.items(), key=lambda kv: str(kv[1])):
    print("  %-6s %s" % (c, u))
json.dump({u: c for u, c in results.items()}, open("/tmp/linkcheck.json", "w"), indent=1)
sys.exit(0)
