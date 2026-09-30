#!/usr/bin/env python3
"""Generate one stable, citable page per case file, plus sitemap.xml / robots.txt / llms.txt.

Stable per-record URLs are the single biggest citability win for a static archive, so each
case gets its own document with its own title, description, and JSON-LD.
"""
import json, os, datetime, re, sys
from html import unescape
import html as _html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
DATA = os.path.join(SITE, "data")
BASE = "https://nosytlabs.github.io/canadian-ufo"
TODAY = datetime.date.today().isoformat()

# The sourcing-confidence scale. The labels are NOT written here: they are read
# out of site/assets/core.js at the bottom of this file, which is the one place
# they are defined. There were five copies of this scale and they had already
# drifted -- this one said "Mainstream reporting WITH named sources" where
# core.js said "Mainstream reporting, named sources", and both were on the
# published site. Only the third element, the prose for a case file, is local to
# the build.
CONF_CAVEAT = {
    "primary": "This case is documented in government or archival sources that are linked directly from the file.",
    "reported": "This case rests on named mainstream reporting. The underlying files exist but have not been read directly here.",
    "partial": "This case is included because gaps are worse than thin records, but the sourcing is partial. Do not build on it without reading the original file.",
}
# (label, chip class) per grade, filled in by _read_conf_scale() below.
CONF = {}

CHIP_CLASS = {"primary": "chip-a", "reported": "chip", "partial": "chip-amb"}


def _read_conf_scale():
    """Take the confidence labels from the JavaScript that renders them.

    core.js and this file used to each carry their own. Reading a static asset
    with a regex is not elegant, but it is the only way to have one definition
    without generating core.js at build time, and a build that failed because a
    JS object literal was reformatted would be worse than the problem.
    """
    path = os.path.join(SITE, "assets", "core.js")
    if not os.path.exists(path):
        raise SystemExit("generate_pages: %s is missing; the confidence scale is read from it."
                         % os.path.relpath(path, ROOT))
    src = open(path, encoding="utf-8").read()
    found = {}
    for key, label, short, chip in re.findall(
            r'(primary|reported|partial):\s*\{\s*label:\s*"((?:[^"\\]|\\.)*)",\s*'
            r'short:\s*"((?:[^"\\]|\\.)*)",\s*chip:\s*"(chip[\w-]*)"', src):
        found[key] = (label.encode().decode("unicode_escape"),
                      short.encode().decode("unicode_escape"), chip)
    if set(found) != {"primary", "reported", "partial"}:
        raise SystemExit(
            "generate_pages: read %d of the 3 confidence grades out of core.js. The CONF "
            "object there must keep the shape key/label/short/chip so this can read it: %s"
            % (len(found), sorted(found)))
    for key, chip in CHIP_CLASS.items():
        if found[key][2] != chip:
            raise SystemExit(
                "generate_pages: core.js maps %r to chip class %r; this build writes %r. "
                "They render the same grade differently." % (key, found[key][2], chip))
    # (label, chip class, case-file prose). `short` is read only by the browser
    # cards on the overview page, so it is not carried into the build.
    for key in found:
        found[key] = (found[key][0], found[key][2], CONF_CAVEAT[key])
    return found

NAV = [
    ("index.html", "Overview"), ("releases.html", "Releases"), ("archive.html", "Archive index"),
    ("case.html", "Case files"), ("map.html", "Map"), ("media.html", "Media"), ("data.html", "Open data"),
]


def trim(text, limit):
    """Cut to a whole word inside `limit`, so a meta description is not
    truncated mid-word by a search engine."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.\u2014-")
    return cut + "\u2026"


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
<meta property="og:image" content="{base}/assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="AURORA — Canada&#39;s declassified UAP record, indexed">
<meta property="og:site_name" content="AURORA">
<meta property="og:locale" content="en_CA">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{base}/assets/og.png">
<link rel="stylesheet" href="assets/base.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%2304060c'/%3E%3Ccircle cx='16' cy='16' r='8' fill='none' stroke='%235fd4e8' stroke-width='2.5'/%3E%3Ccircle cx='16' cy='16' r='2.5' fill='%235fd4e8'/%3E%3C/svg%3E">
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
      <h2>Case files</h2>
      <ul>
        <li><a href="case.html">All eighteen cases</a></li>
        <li><a href="map.html">Case map</a></li>
        <li><a href="releases.html">The records behind these cases</a></li>
      </ul>
    </div>
    <div>
      <h2>Machine-readable</h2>
      <ul>
        <li><a href="data/cases.json">cases.json</a></li>
        <li><a href="llms.txt">llms.txt</a></li>
        <li><a href="sitemap.xml">sitemap.xml</a></li>
      </ul>
    </div>
    <div>
      <h2>Related media</h2>
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
<script src="assets/core.js"></script>
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
    return """<article class="card">
          <div class="card-media%s">%s</div>
          <h3>%s</h3>
          <p class="meta" >%s &middot; %s%s</p>
          <p>%s</p>
        </article>""" % ("" if m["kind"] == "yt" else " poster", frame,
                         esc(m["title"]), esc(m["publisher"]), esc(m["date"]),
                         (" &middot; " + esc(m["len"])) if m["len"] != "long form" else "",
                         esc(m["pos"]))


def case_page(c, all_cases, media):
    label, chip, caveat = CONF.get(c["conf"], CONF["partial"])
    title = "%s, %s (%s) — Canadian UAP case file" % (c["title"], c.get("prov", "Canada"), c["date"][:4])
    desc = trim(c["summary"], 155)

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Article",
             "@id": "%s/case-%s.html#article" % (BASE, c["slug"]),
             "headline": title,
             "description": desc,
             "datePublished": TODAY,
             "dateModified": TODAY,
             "inLanguage": "en-CA",
             "author": {"@type": "Organization", "name": "AURORA", "url": "%s/" % BASE},
             "image": "%s/assets/og.png" % BASE,
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
            {"@type": "Citation", "name": label, "text": caveat},
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
    <div class="sec-head">
      <div class="sec-num">&#9654;</div>
      <div class="sec-head-col">
        <h2 class="sec-title">Watch and listen</h2>
        <p class="sec-dek">Broadcast and documentary coverage of this case. Players load on click, so
          opening a case file does not open six trackers before you ask for one.</p>
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
  <section class="hero hero-tight">
    <div class="hero-inner hero-1col">
      <div>
        <p class="kicker">Case file · {esc(c.get('region', 'Canada'))} · {esc(label)}</p>
        <h1 class="hero-h1-sm">{esc(c['title'])}</h1>
        <div class="chips" >
          <span class="chip chip-a">{esc(c['display'])}</span>
          {('<span class="chip">' + esc(c['prov']) + '</span>') if c.get('prov') else ''}
          {('<span class="chip">' + esc(c['tag']) + '</span>') if c.get('tag') else ''}
          <span class="chip">{'%.2f, %.2f' % (c['lat'], c['lon'])}</span>
          <span class="chip chip-a"><a href="map.html#{esc(c['slug'])}" class="inherit">view on map</a></span>
        </div>
        {('<p class="faint mt-2">' + esc(c['date_note']) + '</p>') if c.get('date_note') else ''}
        <p class="hero-lede mt-3">{esc(c['summary'])}</p>
      </div>
    </div>
  </section>

  <section>
    <div class="grid g-2 grid-top">
      <div class="prose">
        <h2 class="sec-title sec-title-sm">The record</h2>
        {detail}
        <div class="card card-note">
          <div class="readout-label">Sourcing quality</div>
          <p class="mt-1"><span class="chip {chip}">{esc(label)}</span></p>
          <p class="note mt-1">{esc(caveat)}</p>
        </div>
      </div>
      <aside class="card" >
        <h3>Primary sources</h3>
        <ul class="linklist" >
{docs}
        </ul>
      </aside>
    </div>
  </section>

{media_section}
  <section>
    <div class="sec-head">
      <div class="sec-num">→</div>
      <div class="sec-head-col">
        <h2 class="sec-title">Other case files</h2>
        <p class="sec-dek">Eighteen cases in the Canadian record, graded by sourcing.</p>
      </div>
    </div>
    <ul class="linklist">
{related}
    </ul>
    <p class="mt-8"><a class="btn" href="case.html">All case files</a></p>
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
- Those documents are reachable only in fragments. LAC's browse interface caps every query at fifty rows and
  its pagination returns the same final page forever, so a single query exposes only the head and tail of its
  result set. AURORA assembled 1,510 distinct descriptions by running 59 queries (each record group, each
  province, and each province-by-group pairing) and taking the union.
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
- /archive.html : 1,510 archival descriptions, searchable and sortable
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
- /data/lac.json : 1,510 archival descriptions with source URLs
- /data/cases.json : 18 case files with coordinates and source links
- /data/timeline.json : the record year by year, 1947 to now
- /data/media.json : video items, each with the case it documents
- /data/podcasts.json : LAC Discover podcast episodes. [{id, title, len, size, published, org,
  case, note, url}]. media.html renders both sections from these two files.
- /data/endpoints.json : the verified government endpoint list, as data rather than prose
- /data/survey.json : the Canadian UFO Survey series. {"meta": {since, catalogued_total, series_url},
  "years": [{year, reports, unexplained_pct, ...}]}. This is the single source for every survey
  figure on the site; the 2025 row carries the full breakdown, the 35-year average and the
  provincial counts. The series record is 1,982 reports (2012) -- 1,052 in 2025 is the biggest
  year since 2020, not the largest on record.
- /data/canada.json : province and territory boundaries, Natural Resources Canada CanVec 15 m
  Administrative theme (Open Government Licence - Canada). One merged feature per jurisdiction, 13
  in all. Alongside "features" it carries "attribution" (the licence), "source" (the FTP URL), plus
  "credit" and "basemap" -- the two short strings map.js writes into the map's credit line, so the
  credit is data rather than markup. The basemap itself is OpenFreeMap and is not in this file.
- /data/lac_stats.json : measured figures about the 1,510 rows in lac.json, written by the build
  from the same rows it serves, and the file generate_pages.py asserts archive.html's prose
  against. "single_group_query_caps" is how many rows ONE record-group query returns -- LAC browse
  stops at 50 and its sk parameter repeats the last page, so these are page caps, not totals, and
  the four sum to the 206 the page quotes. "by_group" is the union of all 59 queries and is the
  real per-group total. "by_route" records which query surfaced each row. "titles" and
  "distinct_titles" exist because doc_title is a series title, not a description: 7 distinct values
  across 1,510 rows. "shag_harbour_paper_trail" is the 22 Barrington Passage rows, which are only
  reachable by adding a province to a record-group query.

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

Sitemap: __BASE__/sitemap.xml
"""


# Pages that state the case count in prose. Hand-written pages are the only
# place a count can rot: the data gained a case and the sentence did not.
PROSE_COUNTS = [
    ("index.html", "Eighteen case files with locations"),
    ("map.html", "Eighteen Canadian UAP cases, mapped"),
    ("map.html", "Eighteen Canadian UAP case locations"),
    ("data.html", "18 case files with coordinates"),
    ("llms.txt", "18 case files with coordinates"),
    ("case.html", "eighteen Canadian UAP cases"),
]

# Numbers that came out of measuring the LAC browse interface. The build writes
# them to site/data/lac_stats.json alongside the rows they describe, so check the
# prose against that rather than trusting it.
LAC_PROSE = [
    ("archive.html", "fifty distinct records", "National Research Council",
     "yields fifty-one distinct records"),
    ("archive.html", "206 visible records into 1,510", None, "207 visible records"),
    # The Shag Harbour card. It replaced a card that claimed a 1958 Shelburne
    # County record was the 1967 sighting, which it is not; the replacement's
    # numbers are measured, so they get the same treatment.
    ("archive.html", "Twenty-two records, found this way", None, "twenty-two records"),
    ("archive.html", "a further 22 rows appear", None, "a further 23 rows appear"),
]

NUMWORD = {8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
           14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen",
           18: "eighteen", 19: "nineteen", 20: "twenty"}


def _count_spellings(n):
    """Every way a page might legitimately write the number n."""
    out = {str(n), NUMWORD.get(n, ""), NUMWORD.get(n, "").capitalize()}
    if 20 < n < 100:
        tens, ones = divmod(n, 10)
        names = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty",
                 6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"}
        ones_n = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
                  6: "six", 7: "seven", 8: "eight", 9: "nine"}
        if tens in names and ones in ones_n:
            out.add("%s-%s" % (names[tens], ones_n[ones]))
    return {s for s in out if s}


def assert_prose_counts(cases):
    """Fail the build if a page states a case count the data does not support.

    This is the class of bug that made map.html claim "twelve" while listing
    eighteen, and llms.txt claim 12 while shipping 18.

    It used to be no guard at all. It checked that each pinned sentence in
    PROSE_COUNTS was still present in the file, computed the number the data
    actually implies, and then threw that number away with `del want` on the last
    line. The docstring promised more than the code did, and a PROSE_COUNTS entry
    pinned to the wrong literal would have sailed through.

    So it now reads the count out of the sentence it matched and compares it with
    the data. Both halves have to be right: the sentence has to be there, and the
    number in it has to be the current one.
    """
    n = len(cases)
    spellings = _count_spellings(n)
    for fn, expected in PROSE_COUNTS:
        path = os.path.join(SITE, fn)
        if not os.path.exists(path):
            print("  WARN  %s: missing" % fn)
            continue
        # Collapse whitespace: the prose is hard-wrapped in the source.
        txt = re.sub(r"\s+", " ", open(path, encoding="utf-8").read())
        expected_flat = re.sub(r"\s+", " ", expected)
        if expected_flat not in txt:
            raise SystemExit(
                "generate_pages: %s no longer contains %r.\n"
                "  Either the case count changed (%d now) or that sentence was edited -- "
                "reconcile PROSE_COUNTS in this script with the page." % (fn, expected, n))
        # The sentence around the match is what has to carry the right number.
        i = txt.find(expected_flat)
        window = txt[max(0, i - 120): i + len(expected_flat) + 120]
        found = {s for s in spellings if re.search(r"\b%s\b" % re.escape(s), window, re.I)}
        if not found:
            raise SystemExit(
                "generate_pages: %s says %r but nowhere near it is the current case count "
                "(%d, or %r). The pinned sentence is present, so this is a case where someone "
                "edited the count out of it or replaced it with a stale one.\n  context: %r"
                % (fn, expected, n, sorted(spellings), window[:200]))


def assert_clean_markup():
    """Fail the build on attributes that splicing damage left behind.

    A scripted pass removed every inline style from the HTML and merged the
    result by string splicing. It produced four tags of the form

        class="stat-pair id="survey-stats"" id="survey-stats"

    -- the id was swallowed into the class value, and because the browser
    recovers from that by treating the rest as junk attributes, the page still
    rendered and nothing looked broken. Four of them survived a full build, a
    link check and a screenshot pass. Cheap to detect, and not detectable by
    reading the diff.
    """
    import glob
    suspects = []
    for path in sorted(glob.glob(os.path.join(SITE, "*.html"))) + \
            sorted(glob.glob(os.path.join(SITE, "*.txt"))):
        for lineno, line in enumerate(open(path, encoding="utf-8"), 1):
            for tag in re.findall(r"<[a-zA-Z][^>]*>", line):
                names = re.findall(r'([a-zA-Z-]+)\s*=\s*"', tag)
                dupes = sorted({x for x in names if names.count(x) > 1})
                spliced = re.search(r'class="[^"]*\b(id|style|href|src|role)="', tag)
                if dupes or spliced:
                    suspects.append("%s:%d  %s\n    %s" % (
                        os.path.relpath(path, ROOT), lineno,
                        "duplicate " + ",".join(dupes) if dupes else
                        "attribute spliced into class", tag[:140]))
    if suspects:
        raise SystemExit("generate_pages: malformed attributes in the HTML:\n  "
                         + "\n  ".join(suspects))


def write_survey_noscript():
    """Render index.html's no-JS survey fallback from survey.json.

    It was a hand-typed paragraph and had drifted into quoting two figures the
    source does not contain -- 46.29%, where the 2025 survey says "about 46 per
    cent", and a count of seventeen pilot reports, which the Sky Canada Project
    report never states. A duplicate of a data file is a fact waiting to rot;
    this one already had. The figures below are the ones the survey supports,
    rounded the way the survey rounds them.
    """
    data_path = os.path.join(SITE, "data", "survey.json")
    if not os.path.exists(data_path):
        return
    survey = json.load(open(data_path, encoding="utf-8"))
    years = survey.get("years") or []
    cur = years[-1] if years else {}
    peak = max(years, key=lambda y: y.get("reports", 0)) if years else {}
    path = os.path.join(SITE, "index.html")
    if not os.path.exists(path):
        return
    txt = open(path, encoding="utf-8").read()
    marker = 'id="survey-noscript"'
    if marker not in txt:
        raise SystemExit("generate_pages: index.html has no #survey-noscript to fill. "
                         "The markup is generated into it, so it must exist.")
    body = (
        "<p><b>These figures need JavaScript.</b> They are in "
        "<code>data/survey.json</code> \u2014 the {year} edition recorded {n:,} reports, "
        "{unexp}% of them unexplained against a {avg}% average over the preceding {span} years, "
        "and about {insuff}% returned as insufficient information. "
        "The record for the series is {peak:,} reports in {peakyear}.</p>"
    ).format(
        year=cur.get("year", "2025"), n=cur.get("reports", 0),
        unexp=cur.get("unexplained_pct", ""),
        avg=cur.get("long_run_unexplained_pct", ""),
        span=cur.get("long_run_years", 35),
        insuff=cur.get("insufficient_pct", ""),
        peak=peak.get("reports", 0), peakyear=peak.get("year", ""))
    txt = re.sub(r'(<div class="noscript-note" id="survey-noscript">).*?(</div>)',
                 lambda m: m.group(1) + body + m.group(2), txt, flags=re.S)
    open(path, "w", encoding="utf-8").write(txt)
    print("wrote index.html survey noscript fallback from survey.json")


def assert_map_credit(canada_path=None):
    """The map's boundary credit exists in two places on purpose, so check them.

    It has to be in the markup for the no-JS case and it has to come from
    data/canada.json when the map boots, because the licence and source URL live
    there. The two copies then drift: map.html once still credited a CARTO
    basemap, in the line directly below one that named OpenFreeMap correctly.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build_aurora_data as bad
    want = "Boundaries: %s · basemap: %s" % (bad.CANVEC_CREDIT, bad.OPENFREEMAP_CREDIT)
    stale = []
    for name in ("index.html", "map.html"):
        path = os.path.join(SITE, name)
        if not os.path.exists(path):
            continue
        txt = re.sub(r"\s+", " ", open(path, encoding="utf-8").read())
        if want not in txt:
            got = re.search(r'id="map-note"[^>]*>([^<]{0,120})', txt)
            stale.append("%s  wants %r  has %r" % (
                name, want, got.group(1).strip() if got else "no #map-note"))
    if stale:
        raise SystemExit(
            "generate_pages: the map boundary credit is out of date. The build writes\n"
            "  CANVEC_CREDIT / OPENFREEMAP_CREDIT in build_aurora_data.py and map.js\n"
            "  renders them, but these pages also carry a copy for the no-JS case:\n  "
            + "\n  ".join(stale))


def assert_section_numbers():
    """Section numbers must run 01, 02, 03... in DOM order on every page.

    They are hand-typed in all seven authored pages, and they had already drifted
    once: releases.html used Roman I/II/III while everything else used decimals.
    Nothing generated them and nothing checked them, so nothing would have said.
    """
    problems = []
    for name in sorted(os.listdir(SITE)):
        if not name.endswith(".html"):
            continue
        # case-*.html use a row marker, not a section number, so not in scope.
        if name.startswith("case-"):
            continue
        txt = open(os.path.join(SITE, name), encoding="utf-8").read()
        body = re.sub(r"(?s)<(script|style)\b.*?</\1>", " ", txt)
        nums = [_html.unescape(n).strip()
                for n in re.findall(r'class="sec-num"[^>]*>(.*?)</', body, re.S)]
        nums = [re.sub(r"<[^>]+>", "", n).strip() for n in nums]
        nums = [n for n in nums if n]
        if not nums:
            continue
        # The bad value is kept, not filtered out. An earlier version selected
        # only the ones matching \d{1,2} and then skipped the page if none were
        # left -- which meant renaming 01/02/03 to I/II/III, the exact drift this
        # exists to catch, made the check pass by finding nothing to check.
        bad = [n for n in nums if not re.fullmatch(r"\d{1,2}", n)]
        expect = ["%02d" % (i + 1) for i in range(len(nums))]
        if bad or nums != expect:
            problems.append("%-18s %-28s %s" % (
                name, " ".join(nums),
                ("non-numeric: " + ", ".join(bad)) if bad
                else "expected " + " ".join(expect)))
    if problems:
        raise SystemExit(
            "generate_pages: section numbers are not a 01,02,03... run in document order:\n  "
            + "\n  ".join(problems))


import re as _re

_FAQ_RE = _re.compile(
    r'<details>\s*<summary>(?P<q>.*?)</summary>\s*<div class="a">(?P<a>.*?)</div>\s*</details>',
    _re.S)


def _text_of(fragment):
    """Flatten an HTML fragment to the string a reader actually sees."""
    return re.sub(r"\s+", " ", unescape(_re.sub(r"<[^>]+>", " ", fragment))).strip()


def sync_faq_structured_data():
    """Rebuild index.html's FAQPage node from the FAQ that is actually visible.

    The two had drifted apart completely -- the JSON-LD advertised seven
    questions, the page showed six, and not one matched. Structured data has
    to describe visible content or it is a lie to a crawler, so derive it.
    """
    path = os.path.join(SITE, "index.html")
    html = open(path, encoding="utf-8").read()

    start = html.index('id="faq"')
    end = html.index("</section>", start)
    faq_html = html[start:end]
    pairs = [(unescape(_re.sub(r"<[^>]+>", "", m.group("q"))).strip(), _text_of(m.group("a")))
             for m in _FAQ_RE.finditer(faq_html)]
    if not pairs:
        raise SystemExit("sync_faq_structured_data: found no visible FAQ on index.html")

    lstart = html.index('<script type="application/ld+json">') + len('<script type="application/ld+json">')
    lend = html.index("</script>", lstart)
    block = json.loads(html[lstart:lend])

    found = False
    for node in block.get("@graph", []):
        if node.get("@type") == "FAQPage":
            node["mainEntity"] = [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in pairs]
            found = True
    if not found:
        raise SystemExit("sync_faq_structured_data: no FAQPage node in index.html's JSON-LD")

    out = json.dumps(block, ensure_ascii=False, indent=2)
    open(path, "w", encoding="utf-8").write(html[:lstart] + "\n" + out + "\n" + html[lend:])
    print("synced FAQPage structured data from %d visible questions" % len(pairs))


def assert_lac_prose():
    """archive.html quotes two measured figures; keep them honest.

    Reads site/data/lac_stats.json, which build_site_data.py writes from the same
    rows it serves. It used to read data/lac_counts.json, a scraper output file
    that nothing regenerated on build -- so a build could pass against a number
    that had drifted months earlier, next to a second file claiming something
    different about the same rows.
    """
    stats_path = os.path.join(SITE, "data", "lac_stats.json")
    if not os.path.exists(stats_path):
        raise SystemExit("generate_pages: %s is missing -- run build_site_data.py first."
                         % stats_path)
    stats = json.load(open(stats_path, encoding="utf-8"))
    caps = stats["single_group_query_caps"]
    total = sum(caps.values())
    words = {50: "fifty", 51: "fifty-one", 52: "fifty-two", 54: "fifty-four",
             206: "206", 207: "207"}
    nrc = caps.get("National Research Council")
    if nrc is not None and words.get(nrc) not in ("fifty", "fifty-one"):
        raise SystemExit("generate_pages: add a spelling for %r in words" % nrc)
    path = os.path.join(SITE, "archive.html")
    # The prose is hard-wrapped in the source, so a phrase written in the copy
    # ("a further 22 rows appear") is split across lines in the file. Collapse
    # runs of whitespace before matching or every wrapped phrase fails.
    txt = re.sub(r"\s+", " ", open(path, encoding="utf-8").read())
    if nrc is not None:
        want = "yields %s distinct records" % words.get(nrc, str(nrc))
        if want not in txt:
            raise SystemExit(
                "generate_pages: archive.html should say %r -- the NRC file yields %d "
                "distinct records. Update the page and LAC_PROSE." % (want, nrc))
    want = "%d visible records into 1,510" % total
    if want not in txt:
        raise SystemExit(
            "generate_pages: archive.html should say %r -- the four record-group queries "
            "sum to %d. Update the page and LAC_PROSE." % (want, total))
    # The record-group totals and the coverage figures are measured in the same
    # pass and printed on archive.html, and nothing checked them: the page could
    # claim 552 National Defence descriptions and 1,357 dated records while the
    # data said anything at all. Each one below is quoted the way the page
    # phrases it, because a prose number and a JSON number are separate facts
    # that only a check ties together.
    def need(fragment, what):
        if re.sub(r"\s+", " ", fragment) not in txt:
            raise SystemExit(
                "generate_pages: archive.html should say %r -- %s. Update the page."
                % (" ".join(fragment.split()), what))

    groups = stats["by_group"]
    need("%s descriptions, the largest group" % "{:,}".format(groups["Department of National Defence"]),
         "the National Defence file is the largest group")
    need("%s descriptions, every one" % "{:,}".format(groups["National Research Council"]),
         "every National Research Council row is accounted for")
    need("%s descriptions" % groups["Department of Transport"],
         "the Transport group has that many descriptions")
    for g in ("Department of National Defence", "National Research Council",
              "Royal Canadian Mounted Police", "Department of Transport"):
        need('%s indexed' % "{:,}".format(groups[g]), "the %s chip count" % g)

    # The coverage pair is quoted twice on the page in slightly different
    # wording. Checking that the expected substring appears once is not enough:
    # it passed with one copy of the number already wrong, because the other
    # copy still matched. So every instance is extracted and every one has to
    # agree with the data.
    _pat = re.compile(r"([\d,]+)\s+(?:of them also )?carry a document date and ([\d,]+)\s+name a location")
    _found = _pat.findall(txt)
    _want = ("{:,}".format(stats["with_doc_date"]), "{:,}".format(stats["with_location"]))
    _bad = [f for f in _found if f != _want]
    if _bad:
        raise SystemExit(
            "generate_pages: archive.html quotes the coverage figures %s but the data says "
            "%d dated and %d located. Offending sentence(s): %s"
            % (" and ".join(_bad[0]), stats["with_doc_date"], stats["with_location"],
               " | ".join("%s ... %s" % f for f in _bad)))
    if len(_found) < 2:
        print("generate_pages: note -- the coverage sentence appears %d time(s) on "
              "archive.html, expected 2" % len(_found), file=sys.stderr)

    if stats["distinct_titles"] != 7:
        raise SystemExit(
            "generate_pages: lac_stats.json reports %d distinct doc_title values but "
            "archive.html's 'How to read the Description column' card says seven. If the "
            "dump changed, the card needs rewriting, not just a number swap -- the point "
            "of the card is that a series title is not a per-document description."
            % stats["distinct_titles"])
    # The card spells the number out, so map it rather than match a digit.
    TITLE_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
                   7: "seven", 8: "eight", 9: "nine", 10: "ten"}
    word = TITLE_WORDS.get(stats["distinct_titles"])
    if word is None:
        raise SystemExit("generate_pages: add a spelling for %d distinct titles"
                         % stats["distinct_titles"])
    need("only %s distinct values across all %s rows" % (word, "{:,}".format(stats["total"])),
         "the Description-column card should say %s distinct titles across %s rows"
         % (word, "{:,}".format(stats["total"])))

    if stats["total"] != 1510 or "1,510" not in want:
        raise SystemExit(
            "generate_pages: lac_stats.json total is %d but the page claims 1,510. "
            "The dump changed; update the prose." % stats["total"])

    # The Shag Harbour card, checked against the rows it describes.
    shag = stats["shag_harbour_paper_trail"]
    n_shag = shag["count"]
    if "a further %d rows appear" % n_shag not in txt:
        raise SystemExit(
            "generate_pages: archive.html should say 'a further %d rows appear' -- the dump has "
            "%d rows at %s with sighting date %s. Update the page."
            % (n_shag, n_shag, shag["location"], shag["sighting_date"]))
    if not any(k in txt for k in words.get(n_shag, "").split()) and \
            str(n_shag) not in txt:
        raise SystemExit(
            "generate_pages: archive.html should spell out the Shag Harbour count %d somewhere. "
            "Add a spelling to words if it is spelled out." % n_shag)
    dates = shag["doc_dates"]
    if dates:
        # The card spells the range out ("15 November and 19 December 1967"), so
        # derive that phrasing from the data instead of matching a raw M/D/YYYY
        # string the page has no reason to contain.
        MONTHS = ["January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December"]

        def spell(d):
            m, day, y = (int(x) for x in d.split("/"))
            return "%d %s" % (day, MONTHS[m - 1]), y

        lo, ylo = spell(dates[0])
        hi, yhi = spell(dates[-1])
        if ylo == yhi:
            span = "between %s and %s %d" % (lo, hi, yhi)
        else:
            span = "between %s %d and %s %d" % (lo, ylo, hi, yhi)
        if span not in txt:
            raise SystemExit(
                "generate_pages: archive.html's Shag Harbour card should say the run was filed "
                "%r -- the %d rows carry document dates %s to %s. Update the page."
                % (span, n_shag, dates[0], dates[-1]))


def rewrite_map_table(cases):
    """Replace map.html's case table with one generated from cases.json.

    The page promises "the same eighteen cases, in text. No JavaScript needed",
    so this stays static HTML -- but it is written here, not by hand.
    """
    path = os.path.join(SITE, "map.html")
    if not os.path.exists(path):
        return
    rows = []
    for c in sorted(cases, key=lambda c: c.get("date", "")):
        label, chip, _caveat = CONF.get(c["conf"], CONF["partial"])
        rows.append(
            "          <tr><td>%s</td><td><a href=\"case-%s.html\">%s</a></td><td>%s</td><td>%s</td>"
            "<td>%.2f, \u2212%.2f</td><td><span class=\"chip %s\">%s</span></td></tr>"
            % (esc(c.get("display") or c["date"]), c["slug"], esc(c["title"]),
               esc(c.get("prov") or "Canada"), esc(c.get("region") or ""),
               c["lat"], abs(c["lon"]), chip, esc(label)))
    html = open(path, encoding="utf-8").read()
    # A bare .index() here raised ValueError with no context, and because this
    # runs after the 18 case pages are already written, that left site/ half
    # regenerated with no clue what had gone wrong.
    try:
        start = html.index('<table id="arc-table-map">')
        tstart = html.index("<tbody>", start)
        tend = html.index("</tbody>", tstart)
    except ValueError as e:
        raise SystemExit(
            "rewrite_map_table: could not find the case table in map.html (%s).\n"
            "  The <table id=\"arc-table-map\"> / <tbody> markers must be present and\n"
            "  unique for the table to be generated." % e)
    if tstart < start:
        raise SystemExit("rewrite_map_table: the <tbody> found precedes the table marker.")
    out = html[:tstart + len("<tbody>\n")] + "\n".join(rows) + html[tend:]
    open(path, "w", encoding="utf-8").write(out)


def main():
    # Before anything reads CONF: the labels live in core.js.
    CONF.update(_read_conf_scale())
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
    open(os.path.join(SITE, "robots.txt"), "w", encoding="utf-8").write(ROBOTS.replace("__BASE__", BASE))
    print("wrote sitemap.xml, robots.txt, llms.txt")

    rewrite_map_table(cases)
    print("wrote map.html case table (%d rows)" % len(cases))

    assert_clean_markup()
    assert_map_credit()
    assert_section_numbers()
    write_survey_noscript()
    assert_prose_counts(cases)
    assert_lac_prose()
    sync_faq_structured_data()


if __name__ == "__main__":
    main()
