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
| `site/data/` | Generated JSON: case files, release index, archival descriptions, media, endpoints, map geometry. |
| `site/vendor/leaflet/` | Vendored Leaflet 1.9.4 (BSD-2), so the map works without a CDN. |
| `03-declassified/` | The 29-volume Canada FOIA series (8,759 pages) and the 2010–2019 CIRVIS compilation. ~1 GB, not in git. |
| `02-official-open-data/` | The Sky Canada Project report (OCSA, June 2025). Not in git; fetched from science.gc.ca. |
| `data/` | Scraped source data — the LAC UFO database index and per-department pulls. |
| `09-scripts/` | Scrapers, data builders, the page generator, and the link checker. |

## Running it

The site must be served from the repository root, not from `site/`, because the
release cards link into `03-declassified/`.

```sh
cd ~/canadian-ufo-research
python3 -m http.server 8811
# open http://127.0.0.1:8811/site/
```

## Rebuilding

```sh
sh 09-scripts/publish.sh                 # rebuild everything and stage docs/ for Pages
```

or step by step:

```sh
python3 09-scripts/build_site_data.py    # release index + LAC index -> site/data
python3 09-scripts/build_aurora_data.py  # cases, timeline, media, endpoints, geometry
python3 09-scripts/generate_pages.py     # one page per case + sitemap/robots/llms.txt
python3 09-scripts/check_links.py        # every internal and external link
```

## Publishing

GitHub Pages only serves from `/` or `/docs`, and the 1 GB source archive must stay
out of the repository, so `site/` is copied to `docs/` by `09-scripts/publish.sh`
and Pages is pointed at `/docs`. The site is published at
<https://nosytlabs.github.io/canadian-ufo/>. Document cards open the public
mirrors rather than the local archive, so the deployed site works standalone.

`build_aurora_data.py` needs `natural-earth-vector` on first run; it caches the
download in `/tmp`. Document thumbnails come from macOS `qlmanage` and are cached
in `.thumbs/`.

## How sourcing is graded

Every case file carries one of three grades, and the grade is about paperwork,
not about how strange the event was:

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
  The 207 descriptions in `site/data/lac.json` are that database's own index, with
  deep links into the live record.
  <https://www.canada.ca/en/library-archives/collection/research-help/science-technology/ufos.html>
- **Canada FOIA series** — 29 volumes, 8,759 pages, released under access to
  information and mirrored here as searchable PDFs.
- **CIRVIS Canada 2010–2019** — 169 pages of pilot and controller vital-information
  reports. Note: this compilation is RCAF/ATC material; a related research pass
  found no MERINT content in it.
- **Sky Canada Project** — Office of the Chief Science Advisor, June 2025, 59 pages,
  14 recommendations. <https://www.science.gc.ca/site/science/sites/default/files/documents/sky-canada-report.pdf>
- **The 2025 Canadian UFO Survey** — Ufology Research. 1,052 reports in 2025, 3.42%
  unexplained. ufologyresearch.ca no longer resolves; the current edition is served
  from the publisher's document host.
- **Parliament** — Written Question 3227 (tabled 28 November 2024, never answered),
  2934, 2812, 1320.
- **Map geometry** — Natural Earth admin-1, public domain, filtered to Canada and
  simplified for the web.

## Machine-readable

`llms.txt`, `robots.txt` (with an explicit AI-crawler allowlist), `sitemap.xml`,
JSON-LD (`WebSite`, `Dataset`, `Article`, `FAQPage`), and one stable URL per case
so any single case can be cited on its own.

## Licence and attribution

Site code and prose: use freely. Government documents are not ours to licence.
Leaflet is BSD-2. Natural Earth is public domain. Map tiles are
© OpenStreetMap contributors. Video and audio remain the property of their
publishers and are linked, not reproduced.
