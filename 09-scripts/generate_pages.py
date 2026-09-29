#!/usr/bin/env python3
"""Generate one stable, citable page per case file, plus sitemap.xml / robots.txt / llms.txt.

Stable per-record URLs are the single biggest citability win for a static archive, so each
case gets its own document with its own title, description, and JSON-LD.
"""
import json, os, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
DATA = os.path.join(SITE, "data")
BASE = "https://nosytlabs.github.io/canadian-ufo"

CONF = {
    "primary": ("Archival or official record", "chip-a",
                "This case is documented in government or archival sources that are linked directly from the file."),
    "reported": ("Mainstream reporting with named sources", "chip",
                 "This case rests on named mainstream reporting. The underlying files exist but have not been read directly here."),
    "partial": ("Thin sourcing — verify before citing", "chip-amb",
                "This case is included because gaps are worse than thin records, but the sourcing is partial. Do not build on it without reading the original file."),
}

NAV = [
    ("index.html", "Overview"), ("releases.html", "Releases"), ("archive.html", "Archive index"),
    ("case.html", "Case files"), ("map.html", "Map"), ("media.html", "Media"), ("data.html", "Open data"),
]


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def nav(current):
    out = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == current else ""
        out.append('<a href="%s"%s>%s</a>' % (href, cur, label))
    return "\n    ".join(out)


HEAD = """<!DOCTYPE html>
<html lang="en-CA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{base}/case-{slug}.html">
<meta name="theme-color" content="#04060c">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{base}/case-{slug}.html">
<link rel="stylesheet" href="assets/base.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%2304060c'/%3E%3Ccircle cx='16' cy='16' r='8' fill='none' stroke='%2322d3ee' stroke-width='2'/%3E%3Ccircle cx='16' cy='16' r='2.5' fill='%234ade80'/%3E%3C/svg%3E">
<script type="application/ld+json">
{jsonld}
</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="aurora-field" aria-hidden="true"></div>
<div class="shell">

<header class="site-head">
  <a class="brand" href="index.html">
    <span class="brand-mark" aria-hidden="true"></span>
    <span><span class="brand-name">AURORA</span><span class="brand-sub">Canada's UAP record</span></span>
  </a>
  <button class="nav-toggle" aria-expanded="false" aria-controls="nav" aria-label="Menu">&#9776;</button>
  <nav class="nav" id="nav" aria-label="Primary">
    {nav}
  </nav>
</header>

<main id="main">
"""

FOOT = """</main>

<footer>
  <div class="foot-inner">
    <div>
      <h4>Case files</h4>
      <ul>
        <li><a href="case.html">All eighteen cases</a></li>
        <li><a href="map.html">Case map</a></li>
        <li><a href="releases.html">The records behind these cases</a></li>
      </ul>
    </div>
    <div>
      <h4>Machine-readable</h4>
      <ul>
        <li><a href="data/cases.json">cases.json</a></li>
        <li><a href="llms.txt">llms.txt</a></li>
        <li><a href="sitemap.xml">sitemap.xml</a></li>
      </ul>
    </div>
    <div>
      <h4>Related media</h4>
      <ul>
        <li><a href="media.html">Documentaries and news film</a></li>
      </ul>
    </div>
  </div>
  <div class="disclaimer">
    <b>Not a government website.</b> AURORA is an independent research project, not affiliated with the
    Government of Canada or Library and Archives Canada. "Unidentified" is a finding, not a conclusion.
  </div>
</footer>
</div>
<script src="assets/aurora.js"></script>
</body>
</html>
"""


def media_block(slug):
    """Embedded players for whatever video belongs to this case."""
    path = os.path.join(DATA, "media.json")
    if not os.path.exists(path):
        return ""
    media = {m["id"]: m for m in json.load(open(path, encoding="utf-8"))}
    return slug, media


def player(m):
    if m["kind"] == "yt":
        frame = ('<iframe src="%s?rel=0&amp;modestbranding=1" title="%s" loading="lazy"'
                 ' allow="accelerometer; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
                 % (m["src"], esc(m["title"])))
    else:
        frame = ('<span class="pb" aria-hidden="true"></span>'
                 '<span class="pm">CBC player &middot; click to load</span>'
                 '<a href="%s" target="_blank" rel="noopener" class="poster-link"'
                 ' aria-label="Play: %s"></a>' % (m["src"], esc(m["title"])))
    return """<article class="card reveal">
          <div class="card-media%s">%s</div>
          <h3>%s</h3>
          <p class="meta" style="color:var(--muted);font-size:12.5px">%s &middot; %s%s</p>
          <p>%s</p>
        </article>""" % ("" if m["kind"] == "yt" else " poster", frame,
                         esc(m["title"]), esc(m["publisher"]), esc(m["date"]),
                         (" &middot; " + esc(m["len"])) if m["len"] != "long form" else "",
                         esc(m["pos"]))


def case_page(c, all_cases, media):
    label, chip, caveat = CONF.get(c["conf"], CONF["partial"])
    title = "%s, %s (%s) — Canadian UAP case file" % (c["title"], c.get("prov", "Canada"), c["date"][:4])
    desc = c["summary"][:300]

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Article",
             "@id": "%s/case-%s.html#article" % (BASE, c["slug"]),
             "headline": title,
             "description": desc,
             "datePublished": "2026-09-29",
             "dateModified": "2026-09-29",
             "inLanguage": "en-CA",
             "articleSection": "UAP case file",
             "about": {"@type": "Place",
                       "name": "%s, %s" % (c["title"], c.get("prov", "Canada")),
                       "geo": {"@type": "GeoCoordinates", "latitude": c["lat"], "longitude": c["lon"]}},
             "citation": [d["url"] for d in c.get("docs", [])],
             "isPartOf": {"@type": "WebSite", "name": "AURORA", "url": "%s/" % BASE},
             "publisher": {"@type": "Organization", "name": "AURORA", "url": "%s/" % BASE}},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "AURORA", "item": "%s/" % BASE},
                {"@type": "ListItem", "position": 2, "name": "Case files", "item": "%s/case.html" % BASE},
                {"@type": "ListItem", "position": 3, "name": c["title"], "item": "%s/case-%s.html" % (BASE, c["slug"])}]},
            {"@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": "What happened at %s, %s?" % (c["title"], c.get("prov", "Canada")),
                 "acceptedAnswer": {"@type": "Answer", "text": c["summary"]}},
                {"@type": "Question", "name": "What is the sourcing quality for this case?",
                 "acceptedAnswer": {"@type": "Answer", "text": "%s. %s" % (label, caveat)}}]},
        ]
    }, ensure_ascii=False, indent=1)

    detail = "\n".join('<p>%s</p>' % esc(p) for p in c["detail"])
    docs = "\n".join(
        '<li><span class="bullet"></span><div><a href="%s" target="_blank" rel="noopener">%s</a></div></li>'
        % (esc(d["url"]), esc(d["label"])) for d in c.get("docs", []))

    mine = [media[m] for m in (c.get("media") or []) if m in media][:3]
    media_section = ""
    if mine:
        media_section = """  <section>
    <div class="sec-head reveal">
      <div class="sec-num">&#9654;</div>
      <div class="sec-head-col">
        <h2 class="sec-title">Watch and listen</h2>
        <p class="sec-dek">Broadcast and documentary coverage of this case. Every player was checked to load; CBC players start only when you click.</p>
      </div>
    </div>
    <div class="grid g-3">
%s
    </div>
  </section>

""" % ("\n".join("      " + player(m) for m in mine))

    others = [x for x in all_cases if x["slug"] != c["slug"]][:5]
    related = "\n".join(
        '<li><span class="bullet"></span><div><a href="case-%s.html">%s</a> '
        '<span class="chip">%s</span><div class="desc">%s</div></div></li>'
        % (esc(x["slug"]), esc(x["title"]), esc(x.get("prov", "")), esc(x["summary"][:120]) + "…")
        for x in others)

    body = HEAD.format(
        title=esc(title), desc=esc(desc), base=BASE, slug=c["slug"],
        jsonld=jsonld, nav=nav("case.html")) + f"""
  <section class="hero" style="padding-bottom:8px">
    <div class="hero-inner" style="grid-template-columns:1fr">
      <div>
        <p class="kicker">Case file · {esc(c.get('region', 'Canada'))} · {esc(label)}</p>
        <h1 style="font-size:clamp(34px,5.6vw,64px)">{esc(c['title'])}</h1>
        <div class="chips" style="margin:18px 0 0">
          <span class="chip chip-a">{esc(c['display'])}</span>
          {('<span class="chip">' + esc(c['prov']) + '</span>') if c.get('prov') else ''}
          {('<span class="chip">' + esc(c['tag']) + '</span>') if c.get('tag') else ''}
          <span class="chip">{'%.2f, %.2f' % (c['lat'], c['lon'])}</span>
          <span class="chip chip-a map-link"><a href="map.html#' + esc(c['slug']) + '" style="color:inherit">view on map</a></span>
        </div>
        {('<p style="color:var(--faint);font-size:12.5px;margin:12px 0 0">' + esc(c['date_note']) + '</p>') if c.get('date_note') else ''}
        <p class="hero-lede" style="margin-top:22px;max-width:64ch">{esc(c['summary'])}</p>
      </div>
    </div>
  </section>

  <section>
    <div class="grid g-2" style="align-items:start">
      <div class="prose">
        <h2 class="sec-title" style="font-size:26px;margin-bottom:18px">The record</h2>
        {detail}
        <div class="card" style="margin-top:26px;padding:18px 20px">
          <div class="readout-label">Sourcing quality</div>
          <p style="margin:10px 0 0"><span class="chip {chip}">{esc(label)}</span></p>
          <p style="margin:10px 0 0;font-size:13.6px">{esc(caveat)}</p>
        </div>
      </div>
      <aside class="card" style="position:sticky;top:96px">
        <h3>Primary sources</h3>
        <ul class="linklist" style="margin-top:14px">
{docs}
        </ul>
      </aside>
    </div>
  </section>

{media_section}
  <section>
    <div class="sec-head reveal">
      <div class="sec-num">→</div>
      <div class="sec-head-col">
        <h2 class="sec-title">Other case files</h2>
        <p class="sec-dek">Eighteen cases in the Canadian record, graded by sourcing.</p>
      </div>
    </div>
    <ul class="linklist reveal">
{related}
    </ul>
    <p style="margin-top:24px"><a class="btn" href="case.html">All case files</a></p>
  </section>
""" + FOOT

    path = os.path.join(SITE, "case-%s.html" % c["slug"])
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return os.path.basename(path)


LLMS = """# AURORA — Canada's UAP record

> An independent, non-governmental index of Canada's federal unidentified aerial phenomena (UAP) file.
> Not affiliated with the Government of Canada. Nothing here is evidence of extraterrestrial activity.

AURORA indexes Canadian government records on unidentified flying objects: declassified federal releases,
archival descriptions from Library and Archives Canada, graded case files with primary-source links, and
the live open-data endpoints that serve the record today.

## Key facts (with sources)

- Canada collected UFO reports for roughly four decades. About 9,500 digitized documents from four federal
  departments (National Defence, Transport, National Research Council, RCMP) span 1947 to the early 1980s.
  Source: https://www.canada.ca/en/library-archives/collection/research-help/science-technology/ufos.html
- Project Magnet began in 1950, when the Department of Transport let engineer Wilbert Smith research whether
  UFOs could use Earth's magnetic field for propulsion; it was terminated in 1954.
- Project Second Storey was formed in 1952 by the Defence Research Board, chaired by NRC astronomer
  Dr. Peter Millman. Source: Sky Canada Project report, June 2025.
- The National Research Council ran the file from 1967 into the 1990s, after the Minister of National Defence
  transferred responsibility to it.
- The June 2025 Report of the Sky Canada Project (Office of the Chief Science Advisor) makes 14
  recommendations, the first being to name a federal department to hold public UAP data.
  Source: https://www.science.gc.ca/site/science/sites/default/files/documents/sky-canada-report.pdf
- Canada has no equivalent of the US Department of War's PURSUE releases (begun 2026).

## Pages

- / : overview, map, release index, case grid, timeline, FAQ
- /releases.html : 40 records in five tranches, searchable
- /archive.html : 207 archival descriptions, searchable and sortable
- /case.html : all case files, graded by sourcing quality
- /map.html : eighteen case locations on an interactive Canada map
- /media.html : verified Canadian documentary and news video
- /data.html : open-government endpoints, live CKAN queries, how to request records
- /case-<slug>.html : one stable, citable page per case (Shag Harbour, Falcon Lake, Gander 1951,
  Gander 1974, Stephenville, the Night of the UFOs, Saint John, Fredericton, Moncton, Clarenville,
  Kensington, Baffin Island, Prince George, Montreal, the Yukon row of lights, the New Brunswick
  protected-airspace report, the Yukon intercept, and the Falcon Lake region wave)

## Data

- /data/releases.json : 40 release records
- /data/lac.json : 207 archival descriptions with source URLs
- /data/cases.json : 12 case files with coordinates and source links
- /data/timeline.json, /data/media.json, /data/podcasts.json, /data/endpoints.json, /data/survey.json
- /data/canada.json : Natural Earth province boundaries (public domain)

## Conventions

"UAP" means unidentified aerial phenomenon; "UFO" means unidentified flying object. Case files are graded:
archival or official record / mainstream reporting with named sources / thin sourcing. Gaps are marked
rather than filled.
"""

ROBOTS = """User-agent: *
Allow: /

# AI answer engines are explicitly welcome: this archive exists to be cited.
User-agent: GPTBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Claude-SearchBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: CCBot
Allow: /
User-agent: anthropic-ai
Allow: /
User-agent: Applebot-Extended
Allow: /

Sitemap: https://aurora-uap.example/sitemap.xml
"""


def main():
    cases = json.load(open(os.path.join(DATA, "cases.json"), encoding="utf-8"))
    media = {}
    mp = os.path.join(DATA, "media.json")
    if os.path.exists(mp):
        media = {m["id"]: m for m in json.load(open(mp, encoding="utf-8"))}
    made = [case_page(c, cases, media) for c in cases]
    print("wrote %d case pages" % len(made))

    today = datetime.date.today().isoformat()
    urls = [("", "weekly"), ("releases.html", "weekly"), ("archive.html", "weekly"), ("case.html", "weekly"),
            ("map.html", "monthly"), ("media.html", "monthly"), ("data.html", "monthly")]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, freq in urls:
        loc = "%s/%s" % (BASE, path) if path else "%s/" % BASE
        sm.append("  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq>"
                  "<priority>%s</priority></url>" % (loc, today, freq, "1.0" if not path else "0.8"))
    for c in cases:
        sm.append("  <url><loc>%s/case-%s.html</loc><lastmod>%s</lastmod>"
                  "<changefreq>monthly</changefreq><priority>0.7</priority></url>"
                  % (BASE, c["slug"], today))
    sm.append("</urlset>")
    open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(sm))

    open(os.path.join(SITE, "llms.txt"), "w", encoding="utf-8").write(LLMS)
    open(os.path.join(SITE, "robots.txt"), "w", encoding="utf-8").write(ROBOTS)
    print("wrote sitemap.xml, robots.txt, llms.txt")


if __name__ == "__main__":
    main()
