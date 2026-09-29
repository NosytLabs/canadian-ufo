import re, os, sys, json, time, html, urllib.parse, urllib.request

BASE = "https://www.collectionscanada.gc.ca/databases/ufo/001057-110.01-e.php"
OUT  = os.path.expanduser("~/canadian-ufo-research/data")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
GROUPS = ["Department of National Defence", "Department of Transport",
          "National Research Council", "Royal Canadian Mounted Police"]

def get(url, tries=4, timeout=60):
    for a in range(tries):
        try:
            r = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(r, timeout=timeout) as f:
                return f.read().decode("utf-8", "replace")
        except Exception as e:
            print("retry", a, url, e, file=sys.stderr); time.sleep(1.5 * (a + 1))
    return None

def strip(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

ROW = re.compile(
    r'<div class="alt_data_container">\s*<div class="alt_data1">\s*(.*?)</div>\s*'
    r'<div class="alt_data2">\s*(.*?)</div>\s*<div class="alt_data3">\s*(.*?)</div>\s*'
    r'<div class="alt_data4">\s*<a href="([^"]+)"', re.S)

def harvest(g):
    url = BASE + "?q7=" + urllib.parse.quote(g) + "&interval=50&sk=0"
    seen, recs, prev_ids = set(), [], None
    for page in range(1, 500):
        h = get(url)
        if not h:
            break
        title = re.findall(r'<strong>Document Title: </strong>([^<]*)', h)
        grp   = re.findall(r'Record Group: </strong>([^<]*)', h)
        rows  = ROW.findall(h)
        ids   = [re.search(r'record_id=([\d-]+)', r[3]).group(1) for r in rows if re.search(r'record_id=([\d-]+)', r[3])]
        for (loc, sd, dd, href), rid in zip(rows, ids):
            if rid in seen: continue
            seen.add(rid)
            m = re.search(r'isn_id_nbr=(\d+)&page_id_nbr=(\d+)', href)
            recs.append({"rid": rid, "isn": m.group(1) if m else None,
                         "page": m.group(2) if m else None,
                         "record_group": strip(grp[0]) if grp else g,
                         "doc_title": strip(title[0]) if title else "",
                         "location": strip(loc), "sighting_date": strip(sd), "doc_date": strip(dd)})
        nxt = re.findall(r'href="(/databases/ufo/001057-110\.01-e\.php\?[^"]*sk=\d+[^"]*)"\s*>Next', h)
        print(f"[{g[:12]}] p{page} +{len(rows)} uniq={len(seen)}", file=sys.stderr)
        if not nxt or ids == prev_ids:
            break
        prev_ids = ids
        url = "https://www.collectionscanada.gc.ca" + html.unescape(nxt[0])
        time.sleep(0.3)
    return recs

if __name__ == "__main__":
    allr = []
    for g in GROUPS:
        r = harvest(g)
        print(f"== {g}: {len(r)}", file=sys.stderr)
        json.dump(r, open(os.path.join(OUT, "lac_" + g.split()[-1].lower() + ".json"), "w"), indent=1)
        allr += r
    json.dump(allr, open(os.path.join(OUT, "lac_records.json"), "w"), indent=1)
    print("TOTAL", len(allr))
