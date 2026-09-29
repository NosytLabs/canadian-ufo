import re, os, sys, json, time, threading, queue, urllib.request, urllib.error, html

BASE = "https://www.collectionscanada.gc.ca/databases/ufo/"
OUT = os.path.expanduser("~/canadian-ufo-research/data")
RAW = os.path.expanduser("~/canadian-ufo-research/data/lac_html")
os.makedirs(RAW, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
GROUPS = ["Department of National Defence", "Department of Transport",
          "National Research Council", "Royal Canadian Mounted Police"]

def get(url, tries=4, timeout=60):
    last = None
    for a in range(tries):
        try:
            r = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(r, timeout=timeout) as f:
                return f.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(1.5 * (a + 1))
    print("FAIL", url, last, file=sys.stderr)
    return None

def strip(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

# ---------- 1. harvest record ids from browse listing ----------
def list_page(url):
    h = get(url)
    if h is None: return None, None
    rows = re.findall(
        r'<div class="alt_data_container">\s*<div class="alt_data1">\s*(.*?)</div>\s*'
        r'<div class="alt_data2">\s*(.*?)</div>\s*<div class="alt_data3">\s*(.*?)</div>\s*'
        r'<div class="alt_data4">\s*<a href="([^"]+)"', h, re.S)
    out = []
    for loc, sd, dd, href in rows:
        m = re.search(r'isn_id_nbr=(\d+)&page_id_nbr=(\d+)&record_id=([\d-]+)', href)
        if m:
            out.append({"isn": m.group(1), "page": m.group(2), "rid": m.group(3),
                        "location": strip(loc), "sighting_date": strip(sd), "doc_date": strip(dd)})
    grp = re.findall(r'Record Group: </strong>([^<]{0,80})', h)
    nxt = re.findall(r'href="(/databases/ufo/001057-110\.01-e\.php\?[^"]*sk=\d+[^"]*)"\s*>Next', h)
    nxt = html.unescape(nxt[0]) if nxt else None
    return (out, (grp[0].strip() if grp else None), nxt)

def harvest(g):
    url = BASE + "001057-110.01-e.php?q7=" + urllib.parse.quote(g) + "&interval=50&sk=0"
    recs = []
    seen = set()
    pages = 0
    while url and pages < 400:
        rows, grp, nxt = list_page(url)
        if rows is None: break
        for r in rows:
            r["record_group"] = grp or g
            if r["rid"] not in seen:
                seen.add(r["rid"]); recs.append(r)
        pages += 1
        print(f"[{g}] page {pages} total {len(recs)}", file=sys.stderr)
        if nxt and "sk=" in nxt:
            url = "https://www.collectionscanada.gc.ca" + nxt
        else:
            url = None
        time.sleep(0.25)
    return recs

import urllib.parse
if __name__ == "__main__":
    allr = []
    for g in GROUPS:
        allr += harvest(g)
    with open(os.path.join(OUT, "lac_records.json"), "w") as f:
        json.dump(allr, f, indent=1)
    print("TOTAL", len(allr))
