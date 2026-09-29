import re, os, sys, json, time, html, urllib.parse, urllib.request

BASE="https://www.collectionscanada.gc.ca/databases/ufo/001057-110.01-e.php"
OUT=os.path.expanduser("~/canadian-ufo-research/data")
os.makedirs(OUT,exist_ok=True)
UA={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
GROUPS=["Department of National Defence","Department of Transport","National Research Council","Royal Canadian Mounted Police"]
ROW=re.compile(r'<div class="alt_data_container">\s*<div class="alt_data1">\s*(.*?)</div>\s*'
    r'<div class="alt_data2">\s*(.*?)</div>\s*<div class="alt_data3">\s*(.*?)</div>\s*'
    r'<div class="alt_data4">\s*<a href="([^"]+)"',re.S)
def get(u,tries=3,t=60):
    for a in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=t).read().decode("utf-8","replace")
        except Exception as e:
            print("retry",a,e,file=sys.stderr); time.sleep(1.5)
    return None
def strip(s): return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",s))).strip()

def harvest(g, max_sk=4000):
    seen, recs = set(), []
    sk, stalls, progress = 0, 0, 0
    while sk < max_sk:
        u=BASE+"?q7="+urllib.parse.quote(g)+"&interval=50&sk=%d"%sk
        h=get(u)
        if not h: stalls+=1
        else:
            title=re.findall(r'<strong>Document Title: </strong>([^<]*)',h)
            grp=re.findall(r'Record Group: </strong>([^<]*)',h)
            rows=ROW.findall(h)
            new=0
            for loc,sd,dd,href in rows:
                m=re.search(r'record_id=([\d-]+)',href)
                if not m: continue
                rid=m.group(1)
                if rid in seen: continue
                seen.add(rid); new+=1
                p=re.search(r'isn_id_nbr=(\d+)&page_id_nbr=(\d+)',href)
                recs.append({"rid":rid,"isn":p.group(1) if p else None,"page":p.group(2) if p else None,
                    "record_group":strip(grp[0]) if grp else g,
                    "doc_title":strip(title[0]) if title else "",
                    "location":strip(loc),"sighting_date":strip(sd),"doc_date":strip(dd)})
            if new: stalls=0; progress=sk
            else: stalls+=1
        if stalls>=6:
            print(f"[{g[:14]}] stalled at sk={sk}",file=sys.stderr); break
        sk+=50
        if sk%500==0: print(f"[{g[:14]}] sk={sk} uniq={len(seen)}",file=sys.stderr)
        time.sleep(0.15)
    return recs

if __name__=="__main__":
    allr=[]
    for g in GROUPS:
        r=harvest(g)
        print(f"== {g}: {len(r)}",file=sys.stderr)
        json.dump(r,open(os.path.join(OUT,"lac_"+g.split()[-1].lower()+".json"),"w"),indent=1)
        allr+=r
    json.dump(allr,open(os.path.join(OUT,"lac_records.json"),"w"),indent=1)
    print("TOTAL",len(allr))
