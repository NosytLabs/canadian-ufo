#!/usr/bin/env python3
"""Second pass: recover the document title for every indexed LAC description.

The first pass only harvested titles from the four record-group queries, so most
of the 1,510 rows had a record number but no title. This re-walks the same 59
queries and fills the gap.

What a "title" actually is, and why the site's copy is careful about it: it is
the SERIES title from the catalogue record, not a description of the individual
document. All 1,510 rows end up carrying one, but they carry only seven distinct
strings, because the holdings are scanned images catalogued at series level. A
column of those in archive.html's table is honest as long as the page says so.

Writes in place, atomically, and refuses to write if the harvest came back empty
-- a run where every fetch failed used to write the file back unchanged, print
"filled 0 titles" and exit 0, which looks exactly like a successful no-op.
"""
import http.cookiejar, html, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data")
BASE = "https://www.collectionscanada.gc.ca/databases/ufo/001057-110.01-e.php"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
GROUPS = ["Department of National Defence", "Department of Transport",
          "National Research Council", "Royal Canadian Mounted Police"]
PROVINCES = ["NB", "NS", "Nfld", "PEI", "ON", "QC", "MB", "SK", "AB", "BC", "YT"]

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def fetch(url, tries=3, timeout=45):
    for attempt in range(tries):
        try:
            with opener.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
                return r.read().decode("latin-1")
        except Exception:
            if attempt == tries - 1:
                return None
            time.sleep(1.2 * (attempt + 1))
    return None


def strip(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def harvest(body, titles):
    """Each row is preceded by a <td> holding 'Document Title: ...'."""
    if not body:
        return
    for m in re.finditer(r"Document Title: </strong>(.*?)</td>(.*?)(?=Document Title:|</table>)", body, re.S):
        title = strip(m.group(1))[:200]
        for rid in re.findall(r"record_id=([\d-]+)", m.group(2)):
            if title and title.lower() != "document title:":
                titles.setdefault(rid, title)


def main():
    path = os.path.join(OUT, "lac_full.json")
    records = json.load(open(path, encoding="utf-8"))
    titles = {}
    queries = []
    for g in GROUPS:
        queries.append("?q7=" + urllib.parse.quote(g))
    for p in PROVINCES:
        queries.append("?q4=" + urllib.parse.quote(p))
        for g in GROUPS:
            queries.append("?q4=" + urllib.parse.quote(p) + "&q7=" + urllib.parse.quote(g))
    failed = 0
    for i, q in enumerate(queries, 1):
        body = fetch(BASE + q + "&interval=50&sk=0")
        if body is None:
            failed += 1
            print("  query %d/%d failed: %s" % (i, len(queries), q), file=sys.stderr)
        else:
            harvest(body, titles)
        if i % 15 == 0:
            print("  %d/%d queries, %d titles" % (i, len(queries), len(titles)), file=sys.stderr)
        time.sleep(0.15)

    # Every fetch failing used to write the file back unchanged, print
    # "filled 0 titles" and exit 0 -- indistinguishable from a successful run
    # that genuinely had nothing left to fill.
    if not titles:
        print("no titles harvested from %d queries (%d failed). Refusing to write."
              % (len(queries), failed), file=sys.stderr)
        sys.exit(1)
    if failed:
        print("%d of %d queries failed; titles may be incomplete. Writing anyway."
              % (failed, len(queries)), file=sys.stderr)

    filled = 0
    for r in records:
        if not r.get("doc_title") and r["rid"] in titles:
            r["doc_title"] = titles[r["rid"]]
            filled += 1
    if filled == 0 and not any(r.get("doc_title") for r in records):
        print("harvested %d titles but none matched a record id, and no record has a "
              "title at all. That is a schema change upstream, not a no-op." % len(titles),
              file=sys.stderr)
        sys.exit(1)

    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    with_title = sum(1 for r in records if r.get("doc_title"))
    distinct = len({r["doc_title"] for r in records if r.get("doc_title")})
    print("filled %d titles; %d of %d rows now carry one, across %d distinct series "
          "titles" % (filled, with_title, len(records), distinct))


if __name__ == "__main__":
    main()
