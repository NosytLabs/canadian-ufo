import re, os, sys, json, time, html, urllib.request
BASE="https://www.ufobc.ca/Sightings/sights%s_v2.html"
OUT=os.path.expanduser("~/canadian-ufo-research/data")
UA={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
os.makedirs(OUT,exist_ok=True)

def get(u,tries=3):
    for a in range(tries):
        try:
            r=urllib.request.Request(u,headers=UA)
            return urllib.request.urlopen(r,timeout=60).read().decode("utf-8","replace")
        except Exception as e:
            print("retry",u,e,file=sys.stderr); time.sleep(2)
    return None

DATE=re.compile(r'^(\d{1,2}-[A-Z][a-z]{2}-20\d{2})\s*,\s*(.+?)\s*:\s*$',re.M)
out={}
for y in range(2000,2027):
    h=get(BASE%y)
    if not h: print("MISS",y,file=sys.stderr); continue
    t=re.sub(r'<(script|style).*?</\1>','',h,flags=re.S)
    t=html.unescape(t)
    t=re.sub(r'<[^>]+>','\n',t)
    lines=[l.strip() for l in t.split('\n') if l.strip()]
    joined="\n".join(lines)
    ms=list(DATE.finditer(joined))
    recs=[]
    for i,m in enumerate(ms):
        start=m.end(); end=ms[i+1].start() if i+1<len(ms) else len(joined)
        body=re.sub(r'\s+',' ',joined[start:end]).strip()
        recs.append({"date":m.group(1),"place":m.group(2),"report":body})
    out[y]=recs
    print(y,len(recs),file=sys.stderr)
    time.sleep(0.4)
json.dump(out,open(os.path.join(OUT,"ufobc_sightings.json"),"w"),indent=1)
print("TOTAL",sum(len(v) for v in out.values()))
