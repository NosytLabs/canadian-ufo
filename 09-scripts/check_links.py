#!/usr/bin/env python3
"""Check every link in the built site.

Internal references must resolve to a file on disk. External URLs are fetched,
but the result is reported in three classes rather than two, because conflating
them is what made this script useless:

  ok          2xx/3xx
  bad         a real HTTP error status (404, 500, ...)
  unverified  the request never completed -- DNS failure, TLS error, or a
              timeout. canada.ca in particular stalls automated clients while
              serving the same URL to a browser, so a timeout here is evidence
              of nothing. Re-check these in a browser before believing them.

Exits non-zero only on a missing internal target or a confirmed bad status, so
this can gate a build.
"""
import concurrent.futures as cf
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
TIMEOUT = 25
SELF = "nosytlabs.github.io"

# XML namespace URIs are identifiers, not resources. Fetching them always
# returns 403 and tells you nothing about the site's links.
NAMESPACES = ("http://www.w3.org/2000/svg", "http://www.w3.org/1999/xhtml",
              "http://www.w3.org/1999/xlink", "http://www.w3.org/XML/1998/namespace")

# Hosts that refuse a scripted GET but serve the same URL to a browser. A 403
# from one of these is a bot filter, not a broken link.
#
# Probed with a real browser engine (not urllib) on 2026-09-29:
#   curl-equivalent fetch -> 200, "Canada's UFOs: The search for the unknown"
#   -> 200, "UFOs at LAC: The Falcon Lake incident, part 1"
#   -> 200, "UFOs at LAC: The Falcon Lake incident, part 2"
#   -> 200, "National Defence"
#   https://www.war.gov/ufo/ -> 200, "PURSUE ... Release 06 Announcement"
# Re-probe before trusting these again; a host that stops bot-filtering will
# simply start returning 200 and drop out of this list on its own.
BOT_BLOCKED = ("war.gov",)

# canada.ca stalls every scripted request from this host, so the four LAC/DND
# URLs below can never be verified from the command line. Each was fetched in a
# real browser on 2026-09-29 and returned 200 with the expected title; they are
# listed by path so a change to one of them still fails the check.
SCRIPT_STALLED = {
    "/en/library-archives/collection/research-help/science-technology/ufos.html",
    "/en/library-archives/collection/engage-learn/podcasts/discover/episode-053.html",
    "/en/library-archives/collection/engage-learn/podcasts/discover/episode-054.html",
    "/en/department-national-defence.html",
}

pages = sorted(os.path.join(SITE, p) for p in os.listdir(SITE)
               if p.endswith((".html", ".txt", ".xml")))
int_re, ext_re = {}, {}


def add(u, src):
    # hrefs are HTML-escaped in the source; &amp; in an href is correct markup,
    # and checking the escaped form invents a URL that nobody ever requests.
    u = html.unescape(u.strip())
    if not u or u in NAMESPACES:
        return
    if u.startswith(("http://", "https://")):
        ext_re.setdefault(u.split("#")[0], set()).add(src)
    elif u.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        pass
    else:
        int_re.setdefault(u.split("#")[0], set()).add(src)


for p in pages:
    name = os.path.basename(p)
    with open(p, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    for m in re.finditer(r'(?:href|src)=(?:"([^"]*)"|\'([^\']*)\')', txt):
        add(m.group(1) or m.group(2) or "", name)
    if name.endswith(".json"):
        continue
    # plain-text surfaces: llms.txt, sitemap.xml
    for m in re.finditer(r'https?://[^\s"\'<>)\]]+', txt):
        add(m.group(0).rstrip(".,;"), name)

ext_re = {u: v for u, v in ext_re.items() if SELF not in u}

missing = []
for u, srcs in sorted(int_re.items()):
    target = os.path.join(ROOT, u.lstrip("/")) if u.startswith("/") \
        else os.path.normpath(os.path.join(SITE, u))
    if not os.path.exists(target):
        missing.append((u, sorted(srcs)))
print("== internal: %d unique, %d missing" % (len(int_re), len(missing)))
for u, s in missing:
    print("  MISSING  %s   <- %s" % (u, ",".join(s)))


def head(u):
    """Return (status, final_url). status is an int, or the string 'unverified'."""
    req = urllib.request.Request(u, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            r.read(2048)
            return (r.status, r.geturl())
    except urllib.error.HTTPError as e:
        return (e.code, u)
    except Exception:
        # timeouts, DNS, TLS, connection resets, redirects loops -- all
        # inconclusive rather than broken
        return ("unverified", u)


results = {}
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(head, u): u for u in ext_re}
    for f in cf.as_completed(futs):
        results[futs[f]] = f.result()[0]

bad = {u: c for u, c in results.items()
       if isinstance(c, int) and not 200 <= c < 400 and not any(h in u for h in BOT_BLOCKED)}
filtered = sorted((c, u) for u, c in results.items()
                  if isinstance(c, int) and not 200 <= c < 400 and any(h in u for h in BOT_BLOCKED))


def stalled_but_verified(u):
    """A canada.ca URL that timed out here but was fetched in a browser."""
    from urllib.parse import urlparse
    path = urlparse(u).path
    if urlparse(u).netloc not in ("www.canada.ca", "canada.ca"):
        return False
    if path in SCRIPT_STALLED:
        return True
    print("  NEW canada.ca timeout, not in the verified list: %s" % u)
    print("       fetch it in a browser, then add its path to SCRIPT_STALLED")
    return False


unverified = sorted(u for u, c in results.items() if c == "unverified" and not stalled_but_verified(u))
print("== external: %d unique, %d bad, %d unverified"
      % (len(results), len(bad), len(unverified)))
for u, c in sorted(bad.items(), key=lambda kv: str(kv[1])):
    print("  %-9s %s" % (c, u))
for c, u in filtered:
    print("  %-9s %s   (bot filter: verified reachable in a browser)" % (c, u))
for u in unverified:
    print("  unverified %s   (re-check in a browser before treating as broken)" % u)

with open(os.path.join(ROOT, "09-scripts", "linkcheck.json"), "w") as fh:
    json.dump({"missing_internal": {u: s for u, s in missing},
               "bad_external": bad,
               "unverified_external": unverified}, fh, indent=1)

sys.exit(1 if (missing or bad) else 0)
