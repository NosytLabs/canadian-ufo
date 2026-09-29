#!/usr/bin/env python3
"""Build site/data/*.json from the local archive (PDFs + LAC index)."""
import json, os, re, glob, shutil, datetime, subprocess, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
DATA = os.path.join(SITE, "data")
THUMBS = os.path.join(SITE, "assets", "thumbs")
os.makedirs(DATA, exist_ok=True)
os.makedirs(THUMBS, exist_ok=True)

LAC_DETAIL = ("https://www.collectionscanada.gc.ca/databases/ufo/001057-119.01-e.php"
              "?&isn_id_nbr={isn}&page_id_nbr={page}&record_id={rid}&interval=50")
LAC_BROWSE = ("https://www.collectionscanada.gc.ca/databases/ufo/001057-110.01-e.php"
              "?q7={grp}&interval=50&sk=0")
FUND = {
    "Department of National Defence": ("13019", "DND"),
    "Department of Transport": ("37061", "TRANSPORT"),
    "National Research Council": ("1017", "NRC"),
    "Royal Canadian Mounted Police": ("37024", "RCMP"),
}

def w(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote", path, os.path.getsize(path), "bytes")

# NOTE: "file" paths are absolute from the served root, because the site is served
# from the project root with the site living in site/ (python3 -m http.server 8811
# run from ~/canadian-ufo-research). Serving site/ on its own will 404 the PDFs.

# ---------------------------------------------------------------- LAC index
lac = json.load(open(os.path.join(ROOT, "data", "lac_records.json")))
for r in lac:
    isn = r.get("isn") or FUND.get(r["record_group"], ("", ""))[0]
    r["url"] = LAC_DETAIL.format(isn=isn, page=r["page"], rid=r["rid"])
    r["browse"] = LAC_BROWSE.format(grp=r["record_group"].replace(" ", "+"))
    r["abbr"] = FUND.get(r["record_group"], (isn, "OTHER"))[1]
    r["num"] = int(isn) if str(isn).isdigit() else 0
w(os.path.join(DATA, "lac.json"), lac)

# ------------------------------------------------- declassified PDF volumes
docs = []
thumbs_src = os.path.join(ROOT, ".thumbs")

def thumb_for(pdf_path, ident):
    """First-page thumbnail for a document card.

    Prefers a cached render in .thumbs/, and falls back to asking macOS Quick Look
    (qlmanage) to rasterise page one, so the cards survive a clean checkout.
    """
    src = os.path.join(thumbs_src, os.path.basename(pdf_path) + ".png")
    dst = os.path.join(THUMBS, ident + ".png")
    if not os.path.exists(dst):
        if os.path.exists(src):
            shutil.copy(src, dst)
        elif os.path.exists(pdf_path):
            os.makedirs(thumbs_src, exist_ok=True)
            try:
                subprocess.run(["qlmanage", "-t", "-s", "420", "-o", thumbs_src, pdf_path],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
                if os.path.exists(src):
                    shutil.copy(src, dst)
            except (OSError, subprocess.SubprocessError):
                pass
    return "assets/thumbs/%s.png" % ident if os.path.exists(dst) else None

# Black Vault / ATIP Canada FOIA parts
for pdf in sorted(glob.glob(os.path.join(ROOT, "03-declassified/canufodoc/*.pdf"))):
    m = re.search(r"CanUFODoc_(\d+)_pages_(\d+)-(\d+)\.pdf", os.path.basename(pdf))
    if not m:
        continue
    idx, p1, p2 = int(m.group(1)), int(m.group(2)), int(m.group(3))
    ident = "CAN-UAP-D%03d" % idx
    docs.append({
        "id": ident,
        "title": "Canada FOIA Release, Part %02d" % idx,
        "subtitle": "Pages %s-%s of the Canadian federal UFO file release" % (f"{p1:,}", f"{p2:,}"),
        "source": "Department of National Defence / federal departments (ATIP-FOIA)",
        "pages": p2 - p1 + 1,
        "pageRange": [p1, p2],
        "date": "1947-1983",
        "location": "Canada",
        "type": "pdf",
        "release": "02",
        "file": "https://documents.theblackvault.com/documents/ufos/canada/" +
                urllib.parse.quote("Canada - FOIA Part %02d - Pages %d-%d.pdf" % (idx, p1, p2)),
        "local": "/03-declassified/canufodoc/" + os.path.basename(pdf),
        "thumb": thumb_for(pdf, ident),
    })

# CIRVIS compilation
for pdf in glob.glob(os.path.join(ROOT, "03-declassified/cirvis/*.pdf")):
    ident = "CAN-UAP-D101"
    docs.append({
        "id": ident,
        "title": "CIRVIS Reports, Canada 2010-2019",
        "subtitle": "Vital-information sighting reports filed by Canadian pilots, mariners and the public",
        "source": "Transport Canada / DND / Canadian Coast Guard",
        "pages": None,
        "pageRange": [0, 0],
        "date": "2010-2019",
        "location": "Canada / Arctic / three oceans",
        "type": "pdf",
        "release": "03",
        "file": "https://documents2.theblackvault.com/documents/ufos/CIRVIS--Canada-2010-2019.pdf",
        "local": "/03-declassified/cirvis/" + os.path.basename(pdf),
        "thumb": thumb_for(pdf, ident),
    })

# Official Government of Canada reports held locally or served centrally
official = [
    {
        "id": "CAN-UAP-D201",
        "title": "Report of the Sky Canada Project",
        "subtitle": "Management of Public Reporting of Unidentified Aerial Phenomena in Canada - 59 pages, 14 recommendations",
        "source": "Office of the Chief Science Advisor of Canada",
        "pages": 59, "pageRange": [1, 59],
        "date": "2025-06", "location": "Ottawa, ON", "type": "pdf", "release": "04",
        "file": "https://www.science.gc.ca/site/science/sites/default/files/documents/sky-canada-report.pdf",
        "local": "/02-official-open-data/ocsa-ufo-report.pdf",
        "thumb": thumb_for(os.path.join(ROOT, "02-official-open-data/ocsa-ufo-report.pdf"), "CAN-UAP-D201"),
    },
    {
        "id": "CAN-UAP-D202",
        "title": "Sky Canada Project - January 2025 Preview",
        "subtitle": "16-page preview of the forthcoming OCSA report on UAP reporting in Canada",
        "source": "Office of the Chief Science Advisor of Canada",
        "pages": 16, "pageRange": [1, 16],
        "date": "2025-01", "location": "Ottawa, ON", "type": "pdf", "release": "04",
        "external": "https://www.science.gc.ca/site/science/sites/default/files/documents/Sky-Canada-Preview-January-2025.pdf",
        "thumb": None,
    },
    {
        "id": "CAN-UAP-D203",
        "title": "Canada's UFOs: the search for the unknown",
        "subtitle": "Library and Archives Canada - approx. 9,500 digitized records from four federal departments, 1947-early 1980s",
        "source": "Library and Archives Canada",
        "pages": 9500, "pageRange": [0, 0],
        "date": "1947-1983", "location": "Canada", "type": "database", "release": "01",
        "external": "https://www.canada.ca/en/library-archives/collection/research-help/science-technology/ufos.html",
        "thumb": None,
    },
    {
        "id": "CAN-UAP-D204",
        "title": "CADORS - Civil Aviation Daily Occurrence Reporting System",
        "subtitle": "Transport Canada's daily aviation occurrence database; UAP sightings are filed here",
        "source": "Transport Canada",
        "pages": None, "pageRange": [0, 0],
        "date": "current", "location": "Canada", "type": "database", "release": "05",
        "external": "https://tc.canada.ca/en/civil-aviation/canadian-aviation-safety-investigations-reporting/cadors",
        "thumb": None,
    },
    {
        "id": "CAN-UAP-D205",
        "title": "Open Government Data Catalogue - UAP/UFO searches",
        "subtitle": "Live CKAN API queries for UFO, UAP and CADORS datasets on open.canada.ca",
        "source": "Government of Canada Open Data",
        "pages": None, "pageRange": [0, 0],
        "date": "current", "location": "Canada", "type": "api", "release": "05",
        "external": "https://open.canada.ca/data/en/dataset?q=UFO",
        "thumb": None,
    },
    {
        "id": "CAN-UAP-D206",
        "title": "NORAD downing of a high-altitude object, Yukon",
        "subtitle": "11 February 2023 - object downed over Yukon Territory; RCMP recovered debris from a lake shore",
        "source": "NORAD / RCMP (reported by OCSA)", "pages": None, "pageRange": [0, 0],
        "date": "2023-02-11", "location": "Yukon Territory", "type": "record", "release": "05",
        "external": "https://www.science.gc.ca/site/science/sites/default/files/documents/sky-canada-report.pdf",
        "thumb": None,
    },
]
docs.extend(official)

# Library and Archives Canada record-group cards (release 01)
counts = {}
for r in lac:
    counts[r["record_group"]] = counts.get(r["record_group"], 0) + 1
for gi, (grp, (isn, abbr)) in enumerate(FUND.items(), start=1):
    docs.append({
        "id": "CAN-UAP-A%02d" % gi,
        "title": grp,
        "subtitle": "%d digitized descriptions, %s fonds (ISN %s) - browse the live LAC database"
                    % (counts.get(grp, 0), abbr, isn),
        "source": "Library and Archives Canada",
        "pages": None, "pageRange": [0, 0],
        "date": "1947-1983", "location": "Canada", "type": "database",
        "release": "01",
        "external": LAC_BROWSE.format(grp=grp.replace(" ", "+")),
        "thumb": None,
    })


releases = [
    {"n": "01", "title": "The federal UFO file, indexed",
         "date": "Sept. 29, 2026",
         "blurb": "207 archival descriptions from the four federal bodies that kept Canada's UFO records - "
                  "National Defence, Transport, the National Research Council and the RCMP - indexed and "
                  "linked straight into Library and Archives Canada's live database."},
    {"n": "02", "title": "Canada FOIA release, parts 01-29",
         "date": "Sept. 29, 2026",
         "blurb": "8,759 pages of the Canadian federal UFO file, released under access-to-information and "
                  "mirrored as 29 searchable PDF volumes. Correspondence, sightings, memos and procedures, 1947-1983."},
    {"n": "03", "title": "CIRVIS reports, 2010-2019",
         "date": "Sept. 29, 2026",
         "blurb": "A decade of reports filed under Canada's mandatory vital-information sighting rules by "
                  "pilots, vessel crews and observers across Canadian airspace and waters."},
    {"n": "04", "title": "Sky Canada Project",
         "date": "Sept. 29, 2026",
         "blurb": "The Office of the Chief Science Advisor's June 2025 report on how Canada receives, handles "
                  "and publishes UAP reports - plus its January 2025 preview."},
    {"n": "05", "title": "Open data and live endpoints",
         "date": "Sept. 29, 2026",
         "blurb": "Working links into open.canada.ca, CADORS, Library and Archives Canada, science.gc.ca and "
                  "the other endpoints that return Canada's UAP record today."},
]

w(os.path.join(DATA, "releases.json"), {"releases": releases, "documents": docs})

print("documents:", len(docs), "| lac records:", len(lac))
