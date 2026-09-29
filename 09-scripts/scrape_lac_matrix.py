#!/usr/bin/env python3
"""Index as much of the Library and Archives Canada UFO database as is publicly reachable.

Why this exists
---------------
LAC's browse interface caps every query at 50 rows, and its `sk` pagination is
broken: page 2 returns the *last* 50 rows and every page after that repeats them.
So a single department query exposes only the head and tail of its result set.

The only way deeper is to vary the query. Running the four record groups, the
province field, and the province x record-group matrix returns substantially more
distinct descriptions, and this script unions them all into one index.

Provincial codes are LAC's own, not the standard abbreviations: Newfoundland and
Labrador is `Nfld` and Prince Edward Island is `PEI`, while `NL`, `PE`,
`Northwest Territories` and `Nunavut` return nothing.

    python3 09-scripts/scrape_lac_matrix.py
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
        except Exception as exc:  # noqa: BLE001
            if attempt == tries - 1:
                print("  FAIL", url, exc, file=sys.stderr)
                return None
            time.sleep(1.2 * (attempt + 1))
    return None


def strip(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse(body, seen, source):
    if not body:
        return 0
    rows = re.findall(
        r'<div class="alt_data_container">\s*<div class="alt_data1">\s*(.*?)</div>\s*'
        r'<div class="alt_data2">\s*(.*?)</div>\s*<div class="alt_data3">\s*(.*?)</div>\s*'
        r'<div class="alt_data4">\s*<a href="([^"]+)"', body, re.S)
    grp = re.findall(r"Record Group: </strong>([^<]{0,90})", body)
    added = 0
    for loc, sighting, doc_date, href in rows:
        m = re.search(r"isn_id_nbr=(\d+)&page_id_nbr=(\d+)&record_id=([\d-]+)", href)
        if not m or m.group(3) in seen:
            continue
        seen[m.group(3)] = {
            "rid": m.group(3), "isn": m.group(1), "page": m.group(2),
            "record_group": strip(grp[0]) if grp else "",
            "doc_title": "", "location": strip(loc), "sighting_date": strip(sighting),
            "doc_date": strip(doc_date), "via": source,
            "url": ("https://www.collectionscanada.gc.ca/databases/ufo/001057-119.01-e.php"
                    "?&isn_id_nbr=%s&page_id_nbr=%s&record_id=%s&interval=50" % (m.group(1), m.group(2), m.group(3))),
        }
        added += 1
    return added


def title_for(body, seen_id):
    """Pull the document title that sits immediately above its record row."""
    if not body:
        return ""
    m = re.search(r"Document Title: </strong>(.*?)</td>.*?record_id=" + re.escape(seen_id), body, re.S)
    return strip(m.group(1))[:180] if m else ""


def main():
    os.makedirs(OUT, exist_ok=True)
    seen, queries = {}, 0

    def run(query, label):
        nonlocal queries
        queries += 1
        body = fetch(BASE + query + "&interval=50&sk=0")
        return parse(body, seen, label)

    for grp in GROUPS:
        n = run("?q7=" + urllib.parse.quote(grp), "record group")
        print("group  %-34s +%3d  (total %d)" % (grp, n, len(seen)))
    for prov in PROVINCES:
        n = run("?q4=" + urllib.parse.quote(prov), "province")
        print("prov   %-34s +%3d  (total %d)" % (prov, n, len(seen)))
    for prov in PROVINCES:
        for grp in GROUPS:
            n = run("?q4=" + urllib.parse.quote(prov) + "&q7=" + urllib.parse.quote(grp), "province + group")
            if n:
                print("matrix %-4s %-30s +%3d  (total %d)" % (prov, grp[:28], n, len(seen)))

    # document titles: one pass per record is too slow, so pull them from the
    # group queries we already know are stable
    for grp in GROUPS:
        body = fetch(BASE + "?q7=" + urllib.parse.quote(grp) + "&interval=50&sk=0")
        for rid in list(seen):
            t = title_for(body, rid)
            if t:
                seen[rid]["doc_title"] = t
        time.sleep(0.2)

    records = sorted(seen.values(), key=lambda r: (r["record_group"], r["rid"]))
    path = os.path.join(OUT, "lac_full.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)

    counts, vias, titled, dated, located = {}, {}, 0, 0, 0
    for r in records:
        g = r["record_group"] or "Unattributed"
        counts[g] = counts.get(g, 0) + 1
        vias[r["via"]] = vias.get(r["via"], 0) + 1
        titled += bool(r["doc_title"])
        dated += not r["doc_date"].startswith("[")
        located += not r["location"].startswith("[")
    summary = {
        "total": len(records), "queries": queries, "by_group": counts, "by_route": vias,
        "with_title": titled, "with_doc_date": dated, "with_location": located,
        "provinces_searched": PROVINCES,
        "note": "LAC browse caps each query at 50 rows and its sk pagination repeats the last page; "
                "coverage here is the union of %d distinct queries, not the whole collection." % queries,
    }
    with open(os.path.join(OUT, "lac_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    print("\nTOTAL %d descriptions from %d queries" % (len(records), queries))
    for g, c in sorted(counts.items(), key=lambda kv: -kv[1]):
        print("  %-38s %4d" % (g, c))
    print("  with document title: %d   with document date: %d   with location: %d" % (titled, dated, located))
    print("->", path)


if __name__ == "__main__":
    main()
