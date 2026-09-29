#!/usr/bin/env python3
"""Scrape the complete Library and Archives Canada UFO database index.

The earlier partial scrape reported 207 records; the live database holds several
thousand. This walks every page of every record group and writes the full index,
so the site never overstates its own coverage.

    python3 09-scripts/scrape_lac_full.py            # all four groups
    python3 09-scripts/scrape_lac_full.py NB NS      # named provinces instead
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
    """Follow 'Next' until exhausted, yielding (record fields) tuples."""
    seen, pages = {}, 0
    while url and pages < 400:
        body = get(url)
        if body is None:
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
            print("  [%s] stalled at %d records after %d pages" % (label, len(seen), pages), file=sys.stderr)
            break
        nxt = re.findall(r'href="(/databases/ufo/001057-110\.01-e\.php\?[^"]*sk=\d+[^"]*)"[^>]*>Next', body)
        nxt = html.unescape(nxt[0]) if nxt else None
        url = ("https://www.collectionscanada.gc.ca" + nxt) if (nxt and "sk=" in nxt) else None
        time.sleep(0.2)
        if pages % 10 == 0:
            print("  [%s] page %d, %d records" % (label, pages, len(seen)), file=sys.stderr)
    return list(seen.values())


def main():
    os.makedirs(OUT, exist_ok=True)
    wanted = sys.argv[1:]
    records = {}
    if wanted:
        for code in wanted:
            name = PROVINCES.get(code.upper(), code)
            url = BASE + "?q4=" + code.upper() + "&interval=50&sk=0"
            got = walk(url, name)
            print("%-28s %4d" % (name, len(got)))
            for r in got:
                r["province"] = code.upper()
                records[r["rid"]] = r
    else:
        for grp in GROUPS:
            got = walk(BASE + "?q7=" + urllib.parse.quote(grp) + "&interval=50&sk=0", grp)
            print("%-34s %4d records" % (grp, len(got)))
            for r in got:
                records[r["rid"]] = r
    path = os.path.join(OUT, "lac_full.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(records.values()), f, ensure_ascii=False, indent=1)
    print("total unique records:", len(records), "->", path)
    if not wanted:
        counts = {}
        for r in records.values():
            counts[r["record_group"]] = counts.get(r["record_group"], 0) + 1
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
            print("  %-36s %4d" % (k, v))
        with open(os.path.join(OUT, "lac_counts.json"), "w", encoding="utf-8") as f:
            json.dump(counts, f, indent=1)


if __name__ == "__main__":
    main()
