# AURORA — Canada's UAP record, indexed

An independent, non-governmental index of Canada's federal unidentified aerial
phenomena (UAP) file. Four federal departments kept UFO records between 1947 and
the early 1980s; the access-to-information releases that followed add thousands
more pages. Almost none of it is searchable. This project indexes it.

**AURORA is not affiliated with the Government of Canada.** Government documents
linked here remain Crown property. Nothing here is evidence of extraterrestrial
activity — "unidentified" is the finding, not a conclusion.

## What is here

| Path | What it holds |
|---|---|
| `site/` | The authored website. Static HTML, no build step, no framework. |
| `docs/` | Generated copy of `site/` for GitHub Pages. Do not edit by hand. |
| `site/data/` | Generated JSON: case files, release index, archival records, media, endpoints, map geometry. |
| `site/vendor/maplibre/` | Vendored MapLibre GL JS 5.24.0 (BSD-3) + its stylesheet and licence, so the map needs no CDN. |
| `03-declassified/` | The 29-volume Canada FOIA series (8,759 pages) and the 2010–2019 CIRVIS compilation. ~1 GB, not in git. |
| `02-official-open-data/` | The Sky Canada Project report (OCSA, June 2025). Not in git; fetched from science.gc.ca. |
| `data/` | Raw scraper output. The 1,510-row LAC index and its per-query sources. Nothing here is read by a build. |
| `09-scripts/` | Scrapers, data builders, the page generator, and the link checker. |

`site/` is self-contained: it links to public mirrors of every document, so it
works served on its own. Serving the repository root works too, but is not
required — the 1 GB local archive is not referenced by the site.

## Running it

From the root of your local clone:

```sh
cd site
python3 -m http.server 8811
# open http://127.0.0.1:8811/
```

## Rebuilding

```sh
sh 09-scripts/publish.sh                 # rebuild everything and stage docs/ for Pages
```

or step by step, in this order:

```sh
python3 09-scripts/build_site_data.py    # release index + LAC index -> site/data
python3 09-scripts/build_aurora_data.py  # cases, timeline, media, endpoints, map geometry
python3 09-scripts/generate_pages.py     # one page per case + sitemap/robots/llms.txt
python3 09-scripts/check_links.py        # every internal and external link
```

The order matters in one place only: `generate_pages.py` asserts the figures in
`archive.html`'s prose against `site/data/lac_stats.json`, so `build_site_data.py`
has to run first. It exits non-zero rather than publishing prose it cannot
support.

## Publishing

GitHub Pages only serves from `/` or `/docs`, and the 1 GB source archive must stay
out of the repository, so `site/` is copied to `docs/` by `09-scripts/publish.sh`
and Pages is pointed at `/docs`. The site is published at
<https://nosytlabs.github.io/canadian-ufo/>.

`build_aurora_data.py` downloads the CanVec administrative shapefile on first run
and caches it in `09-scripts/.cache/`. Document thumbnails come from macOS
`qlmanage` and are cached in `.thumbs/`.

## How sourcing is graded

Every case file carries one of three grades, and the grade is about paperwork,
not about how strange the event was. The labels live in exactly two places —
`Aurora.CONF` in `site/assets/core.js` and `.conf-*` in `site/assets/base.css` —
because a third copy in the map code is how a page came to describe the wrong
colour for "mainstream reporting".

- **Archival or official record** — a government or archival document is linked.
- **Mainstream reporting, named sources** — the reporting is solid; the file has
  not been read directly here.
- **Thin sourcing — verify before citing** — included because a marked gap is
  better than a silent one.

Claims that circulate in enthusiast summaries but are not in the primary record
are left out, and where a source contradicts itself the disagreement is shown
rather than resolved. Two examples that stay visible: the initials on the
Shag Harbour memo of 6 October 1967 (W. W. Turner in CBC's transcription, T. T.
Turner in another), and the missing MERINT incident list for Atlantic waters.

## Data sources

- **Library and Archives Canada** — Canada's UFOs: the search for the unknown.
  ~9,500 digitized documents, four origin departments, 1947 to the early 1980s.
  <https://www.canada.ca/en/library-archives/collection/research-help/science-technology/ufos.html>

  The interface that describes this collection caps every query at 50 rows, shows
  no total, and its `sk` parameter is not an offset: page two returns the *last*
  fifty records and every later page repeats them. Paging a single record group
  yields 51 records and then loops. The only way deeper is to vary the query, so
  `09-scripts/scrape_lac_matrix.py` runs 59 of them (four record groups, eleven
  provinces, all forty-four province-by-group pairings) and unions the result:
  **1,510 distinct records**, of which 1,357 carry a document date, 1,311 name a
  location and 1,213 a sighting date. These land in `data/lac_full.json` and reach
  the site as `site/data/lac.json`.

  What that index does *not* contain: a description of each document. The
  collection is scanned images catalogued at series level, so the `doc_title`
  field carries a series title and the 1,510 rows hold **seven distinct values**
  between them. The archive table says so on the card, because a column headed
  "Description" that repeats seven strings looks like a bug otherwise.

  `site/data/lac_stats.json` is written by the build from the same rows, and is
  what `generate_pages.py` checks the prose against. It is the only place the
  measured figures live; the scrapers deliberately do not write a competing
  summary, which is how `with_title: 199` sat in the repo for months after all
  1,510 rows had titles.

  Note LAC's province codes are its own, not the standard abbreviations:
  Newfoundland and Labrador is `Nfld`, Prince Edward Island is `PEI`, and `NL`,
  `PE`, the Northwest Territories and Nunavut all return nothing.

  1,510 is a floor, not a total. The gap to ~9,500 is the part of the collection
  that no combination of the interface's own query fields exposes.
- **Canada FOIA series** — 29 volumes, 8,759 pages, released under access to
  information and mirrored here as searchable PDFs.
- **CIRVIS Canada 2010–2019** — 169 pages of pilot and controller vital-information
  reports. Note: this compilation is RCAF/ATC material; a related research pass
  found no MERINT content in it.
- **Sky Canada Project** — Office of the Chief Science Advisor, June 2025, 59 pages,
  14 recommendations. <https://www.science.gc.ca/site/science/sites/default/files/sky-canada-report.pdf>
- **The 2025 Canadian UFO Survey** — Ufology Research, published 9 March 2026:
  1,052 reports, 3.42% unexplained, 16.83% explained, about 34% probable and about
  46% insufficient information, against a 10.22% unexplained average over the
  preceding 35 years. The last two are the survey's own rounding — it prints
  "about 34 percent" and "about 46 percent", and an earlier version of this file
  gave them as 33.46 and 46.29, which appear nowhere in the document. The series
  record is 1,982 reports in 2012, so 2025 is the biggest year since 2020 and the
  seventh highest on record — not the largest ever.
  ufologyresearch.ca no longer resolves; the current edition is served from the
  publisher's document host, and `site/data/survey.json` is the single source for
  every survey figure on the site, including index.html's no-JS fallback, which
  is generated from it rather than typed.
- **Parliament** — Written Question 3227 (tabled 28 November 2024, never answered),
  2934, 2812, 1320.
- **Map geometry** — Natural Resources Canada, CanVec 15 m Administrative theme,
  `geo_political_region_2` (Open Government Licence – Canada), merged to one
  feature per jurisdiction. This replaced Natural Earth admin-1, which is a US
  dataset: it drew the Arctic and the provincial borders wrong at the scale the
  map is used at. The build reads the shapefile with a stdlib reader, verifies
  every one of the 13 jurisdictions resolved, and fails if any is missing.
- **Basemap** — OpenFreeMap's `dark` style, keyless vector tiles
  (<https://tiles.openfreemap.org/planet>). If the style fails to load, `map.js`
  falls back to a minimal local style so the page still draws the boundaries.

## Machine-readable

`llms.txt`, `robots.txt` (with an explicit AI-crawler allowlist), `sitemap.xml`,
JSON-LD (`WebSite`, `Dataset`, `Article`, `FAQPage`), and one stable URL per case
so any single case can be cited on its own. `llms.txt` documents the shape of
every file in `site/data/`, including the ones whose fields are easy to
misread — `lac_stats.json` and the series-title caveat above are both in it.

## Licence and attribution

Site code and prose: use freely. Government documents are not ours to licence.
MapLibre GL JS is BSD-3; CanVec is Open Government Licence – Canada; OpenFreeMap
tiles are © OpenStreetMap contributors. Video and audio remain the property of
their publishers and are linked, not reproduced.
