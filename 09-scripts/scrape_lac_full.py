#!/usr/bin/env python3
"""Scrape the Library and Archives Canada UFO database index, one query at a time.

This is the NARROW tool. It walks a single query -- one record group, or one
province per argument -- and LAC's browse interface caps each at 50 rows with an
`sk` parameter that repeats the last page rather than offsetting. A full run
therefore yields roughly 207 records, which is a page cap and not a total.

The site's published index comes from scrape_lac_matrix.py, which unions 59
distinct queries to reach 1,510. This script will happily write its ~207 rows
over that file, which is why it now refuses to write at all when a crawl ends on
a transport failure or a safety limit rather than on LAC repeating a page.

    python3 09-scripts/scrape_lac_full.py            # all four groups
    python3 09-scripts/scrape_lac_full.py NB NS      # named provinces instead

If you are rebuilding the published index, use scrape_lac_matrix.py.
"""
import html, http.cookiejar, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data")
BASE = "https://www.collectionscanada.gc.ca/databases/ufo/001057-110.01-e.php"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
GROUPS = ["Department of National Defence", "Department of Transport",
          "National Research Council", "Royal Canadian Mounted Police"]
PROVINCES = {"AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick",
             "NL": "Newfoundland and Labrador", "NS": "Nova Scotia", "NT": "Northwest Territories",
             "NU": "Nunavut", "ON": "Ontario", "PE": "Prince Edward Island", "QC": "Quebec",
             "SK": "Saskatchewan", "YT": "Yukon"}


# LAC paginates on a PHP session. Without a cookie jar the server hands back the
# same page forever, which looks like an endless index. Keep the session alive.
COOKIES = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIES))
OPENER.addheaders = [("User-Agent", UA["User-Agent"])]


def get(url, tries=4, timeout=60):
    for attempt in range(tries):
        try:
            with OPENER.open(urllib.request.Request(url), timeout=timeout) as r:
                return r.read().decode("latin-1")
        except Exception as exc:  # noqa: BLE001 - retry any transport failure
            if attempt == tries - 1:
                print("  FAIL", url, exc, file=sys.stderr)
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


def strip(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def walk(url, label):
    """Follow 'Next' until exhausted, returning (records, reason_it_stopped).

    The reason is the point. This used to `break` on a transport failure and
    hand back whatever it had, and the caller wrote that to lac_full.json and
    exited 0 -- so a crawl that died on page 3 of 30 was written over 1,510
    good rows and was indistinguishable from a complete one. A truncated crawl
    now has to be declared.
    """
    seen, pages = {}, 0
    reason = "exhausted"
    while url and pages < 400:
        body = get(url)
        if body is None:
            reason = "transport failure on page %d" % (pages + 1)
            break
        rows = re.findall(
            r'<div class="alt_data_container">\s*<div class="alt_data1">\s*(.*?)</div>\s*'
            r'<div class="alt_data2">\s*(.*?)</div>\s*<div class="alt_data3">\s*(.*?)</div>\s*'
            r'<div class="alt_data4">\s*<a href="([^"]+)"', body, re.S)
        before = len(seen)
        for loc, sighting, doc_date, href in rows:
            m = re.search(r"isn_id_nbr=(\d+)&page_id_nbr=(\d+)&record_id=([\d-]+)", href)
            if not m:
                continue
            rid = m.group(3)
            if rid in seen:
                continue
            grp = re.findall(r"Record Group: </strong>([^<]{0,90})", body)
            seen[rid] = {
                "rid": rid, "isn": m.group(1), "page": m.group(2),
                "record_group": strip(grp[0]) if grp else label,
                "doc_title": "", "location": strip(loc),
                "sighting_date": strip(sighting), "doc_date": strip(doc_date),
            }
        pages += 1
        if len(seen) == before and pages > 2:
            # LAC's sk parameter is not an offset -- it repeats the last page
            # forever. This is the expected end of a healthy crawl, so it is
            # "exhausted" rather than a failure, and it is why the record counts
            # here are page caps and not totals.
            reason = "pagination repeated at %d records after %d pages (LAC sk is not an offset)" % (len(seen), pages)
            break
        nxt = re.findall(r'href="(/databases/ufo/001057-110\.01-e\.php\?[^"]*sk=\d+[^"]*)"[^>]*>Next', body)
        nxt = html.unescape(nxt[0]) if nxt else None
        url = ("https://www.collectionscanada.gc.ca" + nxt) if (nxt and "sk=" in nxt) else None
        time.sleep(0.2)
        if pages % 10 == 0:
            print("  [%s] page %d, %d records" % (label, pages, len(seen)), file=sys.stderr)
    else:
        reason = "hit the %d-page safety limit" % 400
    return list(seen.values()), reason


def main():
    os.makedirs(OUT, exist_ok=True)
    wanted = sys.argv[1:]
    records = {}
    truncated = []
    if wanted:
        for code in wanted:
            name = PROVINCES.get(code.upper(), code)
            url = BASE + "?q4=" + code.upper() + "&interval=50&sk=0"
            got, reason = walk(url, name)
            print("%-28s %4d   (%s)" % (name, len(got), reason))
            if "transport failure" in reason or "safety limit" in reason:
                truncated.append((name, reason))
            for r in got:
                r["province"] = code.upper()
                records[r["rid"]] = r
    else:
        for grp in GROUPS:
            got, reason = walk(BASE + "?q7=" + urllib.parse.quote(grp) + "&interval=50&sk=0", grp)
            print("%-34s %4d records   (%s)" % (grp, len(got), reason))
            if "transport failure" in reason or "safety limit" in reason:
                truncated.append((grp, reason))
            for r in got:
                records[r["rid"]] = r

    path = os.path.join(OUT, "lac_full.json")
    if truncated:
        # Writing a partial crawl over a good file is the one outcome worse than
        # not writing at all, because the next build cannot tell it happened.
        for name, reason in truncated:
            print("INCOMPLETE: %s -- %s" % (name, reason), file=sys.stderr)
        print("refusing to write %s over the existing index. Nothing was saved."
              % os.path.basename(path), file=sys.stderr)
        print("Re-run to try again; a single record group can be passed as an argument.",
              file=sys.stderr)
        sys.exit(1)

    # Atomic: a plain open(...,"w") leaves a truncated file if the process dies
    # mid-dump, and a truncated lac_full.json is the exact failure above.
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(list(records.values()), f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    print("total unique records:", len(records), "->", path)
    if not wanted:
        counts = {}
        for r in records.values():
            counts[r["record_group"]] = counts.get(r["record_group"], 0) + 1
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
            print("  %-36s %4d" % (k, v))
        # These used to be written to data/lac_counts.json, which
        # generate_pages.py then asserted archive.html's prose against. It no
        # longer is: build_site_data.py computes them from the rows it serves and
        # writes site/data/lac_stats.json, so a build can never check the copy
        # against a scraper file that predates the last re-scrape.
        print("  per-group totals above are for this run only; the published")
        print("  figures come from site/data/lac_stats.json, written by the build.")


if __name__ == "__main__":
    main()
