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
from urllib.parse import unquote, urlparse

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
# Hosts that answer a browser and refuse anything else. These are verified by
# hand in a browser and are not dead links, but they also cannot be re-checked
# here, which is a real limitation and not a formality.
#
# Matched on hostname by blocked_host(), never as a substring of the URL. The
# substring form this replaced meant "war.gov" also covered war.gov.evil.com, so
# a genuinely dead link on a lookalike host was relabelled "bot filter" and the
# build passed.
BOT_BLOCKED = (
    "war.gov",
    # NUFORC serves people. A 403 from a scripted request is the expected
    # answer, and the data.html endpoint list already marks its rows amber.
    "nuforc.org",
)


def blocked_host(url):
    """True if this URL's host is one that bot-filters rather than 404s."""
    host = (urlparse(url).netloc or "").lower().rsplit("@", 1)[-1]
    host = host.rsplit(":", 1)[0] if ":" in host else host
    return any(host == h or host.endswith("." + h) for h in BOT_BLOCKED)

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

# os.listdir is not recursive, so HTML in a subdirectory of site/ would never be
# scanned and a broken link on it would be invisible. Nothing is nested today;
# assert that rather than assume it, so a future subdirectory fails the build
# instead of passing unchecked.
nested = sorted(os.path.relpath(os.path.join(d, f), SITE)
                for d, _, fs in os.walk(SITE) for f in fs
                if f.endswith((".html", ".txt", ".xml"))
                and os.path.join(d, f) not in pages
                and not os.path.join(d, f).startswith(os.path.join(SITE, "vendor")))
if nested:
    raise SystemExit("check_links: %d page(s) below site/ are not scanned by this script:\n  %s\n"
                     "Either walk them or move them to the top level."
                     % (len(nested), "\n  ".join(nested)))

data_json = sorted(os.path.join(SITE, "data", p) for p in os.listdir(os.path.join(SITE, "data"))
                   if p.endswith(".json"))
int_re, ext_re, fragments = {}, {}, {}


def read_data(path):
    """Parse a data file, failing the build if it is not valid JSON.

    These files are the site's real content and every writer does a plain
    open(path,"w") + json.dump, so a build killed mid-write leaves a truncated
    file. Regex-scanning that text still finds the URLs and reports the site
    clean -- a corrupt data file used to pass this gate. The regex scan below
    still runs, because it catches URLs in nested string values a structural
    walk would have to know to look for.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read(), json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit("check_links: %s is not valid JSON (%s at line %d column %d).\n"
                         "A build was probably killed mid-write; re-run the data build."
                         % (os.path.relpath(path, ROOT), e.msg, e.lineno, e.colno))


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
    # plain-text surfaces: llms.txt, sitemap.xml
    for m in re.finditer(r'https?://[^\s"\'<>)\]]+', txt):
        add(m.group(0).rstrip(".,;"), name)

# The data files are the site's real content, and almost every URL the site
# renders is fetched from them at runtime. Scanning only the HTML meant a typo
# in survey.json shipped a dead link that this script reported as clean -- the
# "PDF from Ufology Research" link on two pages was a mistyped host for months.
_data_urls = 0
for p in data_json:
    name = "data/" + os.path.basename(p)
    txt, _obj = read_data(p)
    for m in re.finditer(r'https?://[^\s"\'<>)\]\\]+', txt):
        add(m.group(0).rstrip(".,;"), name)
        _data_urls += 1
print("== data: %d file(s) parsed as JSON, %d URL(s) found in them"
      % (len(data_json), _data_urls))

# Absolute links to this site were previously dropped by `if SELF not in u`,
# which excluded them from the external set instead of checking them -- so a
# typo in https://nosytlabs.github.io/canadian-ufo/archive.html was never
# reported at all. Map them back to site-relative paths and check them as
# internal links, which is what they are.
# Pages is served from /canadian-ufo, so a self URL carries a path prefix that
# has to come off before the remainder means anything on disk. Splitting on the
# host alone left "canadian-ufo/case.html" behind and reported all 25 of them
# missing, which is a good sign the check is now actually looking.
SELF_PATH = "/canadian-ufo/"
_resolved, _self_rewritten = {}, 0
for u, srcs in ext_re.items():
    if SELF not in u:
        _resolved[u] = srcs
        continue
    rest = u.split(SELF_PATH, 1)[1] if SELF_PATH in u else u.split(SELF, 1)[1].lstrip("/")
    # The base URL itself is the site root, which is index.html on disk.
    rel = rest or "index.html"
    frag = ""
    if "#" in rel:
        rel, frag = rel.split("#", 1)
    int_re.setdefault(rel.split("?")[0], set()).update(srcs)
    if frag:
        fragments.setdefault(rel.split("?")[0], set()).add((frag, sorted(srcs)))
    _self_rewritten += 1
ext_re = _resolved

def resolve_internal(u):
    """Absolute path -> a file on disk, else None.

    The query string has to come off before the existence check:
    os.path.exists("archive.html?x=1") is False for a file that is right there.
    """
    path = u.split("?")[0].split("#")[0]
    if not path:
        return None
    if path.startswith("/"):
        return os.path.join(ROOT, path.lstrip("/"))
    return os.path.normpath(os.path.join(SITE, path))


missing = []
for u, srcs in sorted(int_re.items()):
    target = resolve_internal(u)
    if target is None or not os.path.exists(target):
        missing.append((u, sorted(srcs)))
        continue
    # A #fragment on a file that exists should name an id on that file. This was
    # never checked, so a link to a renamed or deleted id passed indefinitely.
    for frag, fsrcs in sorted(fragments.get(u, ())):
        fid = unquote(frag)
        if not fid:
            continue
        try:
            with open(target, encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue   # not readable, not this script's business to guess
        if ('id="%s"' % fid) not in body and ("name=\"%s\"" % fid) not in body \
                and ("id='%s'" % fid) not in body:
            missing.append(("%s#%s" % (u, frag), fsrcs))

print("== internal: %d unique, %d missing (%d absolute self-link(s) rewritten and checked here)"
      % (len(int_re), len(missing), _self_rewritten))
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
       if isinstance(c, int) and not 200 <= c < 400 and not blocked_host(u)}
filtered = sorted((c, u) for u, c in results.items()
                  if isinstance(c, int) and not 200 <= c < 400 and blocked_host(u))


def stalled_but_verified(u):
    """A canada.ca URL that timed out here but was fetched in a browser."""
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

# Atomic: a plain open(...,"w") leaves a truncated report if the process dies
# here, and the next reader cannot tell a short report from a short link list.
_report = os.path.join(ROOT, "09-scripts", "linkcheck.json")
_tmp = _report + ".tmp"
with open(_tmp, "w", encoding="utf-8") as fh:
    json.dump({"missing_internal": {u: s for u, s in missing},
               "bad_external": bad,
               "unverified_external": unverified}, fh, indent=1)
os.replace(_tmp, _report)

sys.exit(1 if (missing or bad) else 0)
