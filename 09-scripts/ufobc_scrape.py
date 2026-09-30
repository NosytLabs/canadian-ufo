#!/usr/bin/env python3
"""Scrape the Ufobc.ca sighting index, year by year.

Nothing on the site reads this file. It is a held-out cross-check on the federal
record: ufobc.ca is a volunteer database, so its counts are independent of
Library and Archives Canada, and a disagreement between the two is a finding
rather than an error. Keep it out of the build and out of git.

    python3 09-scripts/ufobc_scrape.py

A year whose page parses to zero rows is a failure, not a result. The site would
happily have read a soft-404 or a redesigned date format as "0 sightings in
year N", and a silent zero in a cross-check is worse than no file at all -- it
looks like a finding. Years that genuinely have no reports are not something
this interface can distinguish from a broken fetch, so the run refuses to write
and says which years need a look.
"""
import html
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data")
BASE = "https://www.ufobc.ca/Sightings/sights%s_v2.html"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
YEARS = range(2000, 2027)
# A year page with fewer rows than this has almost certainly failed to parse
# rather than genuinely containing nothing. Observed minimum across the range is
# far above it; if a real empty year ever appears, lower it deliberately.
MIN_ROWS = 5


def get(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 - retry any transport failure
            print("retry %s %s" % (url, exc), file=sys.stderr)
            time.sleep(2)
    return None


DATE = re.compile(r"^(\d{1,2}-[A-Z][a-z]{2}-20\d{2})\s*,\s*(.+?)\s*:\s*$", re.M)


def rows_for(body):
    text = re.sub(r"<(script|style).*?</\1>", "", body, flags=re.S)
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "\n", text)
    joined = "\n".join(l.strip() for l in text.split("\n") if l.strip())
    hits = list(DATE.finditer(joined))
    out = []
    for i, m in enumerate(hits):
        start = m.end()
        end = hits[i + 1].start() if i + 1 < len(hits) else len(joined)
        out.append({"date": m.group(1), "place": m.group(2),
                    "report": re.sub(r"\s+", " ", joined[start:end]).strip()})
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    out, empty, failed = {}, [], []
    for y in YEARS:
        body = get(BASE % y)
        if body is None:
            print("TRANSPORT FAIL %d" % y, file=sys.stderr)
            failed.append(y)
            continue
        recs = rows_for(body)
        if len(recs) < MIN_ROWS:
            # A body arrived but yielded almost nothing. That is a parse failure
            # or a soft-404 until proven otherwise, and writing [] here would
            # turn it into a claim about the year.
            print("SUSPECT %d: only %d rows parsed from a %d-byte page"
                  % (y, len(recs), len(body)), file=sys.stderr)
            empty.append((y, len(recs), len(body)))
            continue
        out[y] = recs
        print(y, len(recs), file=sys.stderr)
        time.sleep(0.4)

    if empty or failed:
        for y, n, size in empty:
            print("  %d: %d rows from %d bytes" % (y, n, size), file=sys.stderr)
        print("refusing to write a partial index: %d year(s) suspect, %d unreachable"
              % (len(empty), len(failed)), file=sys.stderr)
        print("Fix or remove those years, then re-run. Nothing was saved.", file=sys.stderr)
        sys.exit(1)

    path = os.path.join(OUT, "ufobc_sightings.json")
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, path)
    print("TOTAL %d across %d years -> %s" % (sum(len(v) for v in out.values()), len(out), path))


if __name__ == "__main__":
    main()
