#!/usr/bin/env python3
"""Second pass: recover the document title for every indexed LAC description.

The first pass only harvested titles from the four record-group queries, so most
of the 1,510 rows had a record number but no description. This re-walks the same
59 queries and fills the gap.
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
    for i, q in enumerate(queries, 1):
        harvest(fetch(BASE + q + "&interval=50&sk=0"), titles)
        if i % 15 == 0:
            print("  %d/%d queries, %d titles" % (i, len(queries), len(titles)), file=sys.stderr)
        time.sleep(0.15)
    filled = 0
    for r in records:
        if not r.get("doc_title") and r["rid"] in titles:
            r["doc_title"] = titles[r["rid"]]
            filled += 1
    json.dump(records, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with_title = sum(1 for r in records if r.get("doc_title"))
    print("filled %d titles; %d of %d descriptions now carry one" % (filled, with_title, len(records)))


if __name__ == "__main__":
    main()
