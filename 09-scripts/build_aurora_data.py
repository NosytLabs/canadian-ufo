#!/usr/bin/env python3
"""AURORA - build site data: map geometry, case files, timeline, media, open-data endpoints.

Sources are recorded inline so every card on the site can be traced back.
Run from anywhere:  python3 09-scripts/build_aurora_data.py
"""
import json, os, re, subprocess, urllib.request, urllib.error, ssl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
DATA = os.path.join(SITE, "data")
os.makedirs(DATA, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


# Anything the site cannot render without. If a scrape comes back empty the
# build used to carry on, write an empty file and exit 0 -- publishing a site
# with nothing in it and no error anywhere.
MUST_NOT_BE_EMPTY = {"cases.json", "timeline.json", "endpoints.json", "media.json",
                     "survey.json", "canada.json"}


def w(name, obj):
    p = os.path.join(DATA, name)
    if name in MUST_NOT_BE_EMPTY and not obj:
        raise SystemExit("build_aurora_data: %s came back empty. Refusing to write it -- "
                         "check the scrape or the upstream source before publishing." % name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote %-20s %8d bytes" % (name, os.path.getsize(p)))


def get(url, timeout=45):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print("  fetch failed", url, e)
        return b""


# ----------------------------------------------------------------- 1. geometry
# Natural Earth 50m admin-1, filtered to Canada, coordinates rounded for a
# ~200 KB payload. Source: public domain (naturalearthdata.com).
def build_geometry():
    src = "/tmp/ne_50m_admin_1_states_provinces.geojson"
    if not os.path.exists(src):
        get("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
            "ne_50m_admin_1_states_provinces.geojson")
        if not os.path.exists(src):
            open(src, "wb").write(get("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
                                      "geojson/ne_50m_admin_1_states_provinces.geojson"))
    gj = json.load(open(src, encoding="utf-8"))
    feats = []
    for f in gj["features"]:
        p = f["properties"]
        if p.get("adm0_a3") != "CAN":
            continue

        def round_coords(c, nd=2):
            if isinstance(c[0], (int, float)):
                return [round(c[0], nd), round(c[1], nd)]
            return [round_coords(x, nd) for x in c]

        def ring_area(ring):
            a = 0.0
            for i in range(len(ring) - 1):
                a += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
            return abs(a) / 2

        def clean(geom):
            t, c = geom["type"], geom["coordinates"]
            if t == "Polygon":
                keep = [c[0]] + [r for r in c[1:] if ring_area(r) > 0.0006]
                return {"type": "Polygon", "coordinates": [round_coords(r) for r in keep]}
            out = []
            for poly in c:
                keep = [poly[0]] + [r for r in poly[1:] if ring_area(r) > 0.0006]
                out.append([round_coords(r) for r in keep])
            return {"type": "MultiPolygon", "coordinates": out}

        feats.append({
            "type": "Feature",
            "properties": {
                "name": p.get("name"),
                "abbr": p.get("postal"),
                "type_en": p.get("type_en"),
                "woe_name": p.get("woe_name"),
            },
            "geometry": clean(f["geometry"]),
        })
    feats.sort(key=lambda f: f["properties"]["name"] or "")
    w("canada.json", {"type": "FeatureCollection",
                      "attribution": "Natural Earth (public domain), admin-1 provinces & territories",
                      "features": feats})
    print("  provinces:", len(feats))


# ------------------------------------------------------------ 2. case files
# `conf`: primary  = government/archival/primary reporting
#         reported = mainstream reporting with named sources
#         partial  = exists but thin sourcing (flagged in the UI)
CASES = [
    {
        "slug": "shag-harbour", "title": "Shag Harbour", "prov": "NS", "region": "Atlantic",
        "date": "1967-10-04", "display": "4 October 1967", "conf": "primary",
        "lat": 43.85, "lon": -65.50, "tag": "Water entry",
        "summary": "Four lights in sequence over Shag Harbour, Nova Scotia, then one low, fast object "
                   "over the town that struck the water about 300 m offshore. The RCMP launched a search, "
                   "the navy sent divers, and nothing was ever found.",
        "detail": [
            "Laurie Wickens, then 17, was driving home from a dance and called the RCMP from a payphone. "
            "The dispatcher asked if he had been drinking. The phone rang back almost immediately: more calls were coming in.",
            "Const. Ron O'Brien, one of the responding officers, reported a light about 800 m offshore, being carried "
            "out to sea by the tide and gone before a boat could reach it.",
            "RCMP commandeered two fishing boats and found a trail of yellow foam roughly 24 m wide and 800 m long. "
            "Some witnesses said it smelled of sulphur. No aircraft was reported missing.",
            "On Friday 6 October a naval diving team searched for two days and found nothing on a flat sand bottom "
            "in good visibility. One fisherman said divers raised aluminium-coloured debris.",
            "On 6 October 1967 Colonel W. W. Turner, director of operations at National Defence headquarters, wrote that "
            "the Rescue Co-ordination Centre \"discounted the possibilities that the sighting was produced by an aircraft, "
            "flares, floats, or any other known objects.\" A later memo from Turner called it an unidentified flying object - "
            "which, as CBC puts it, does not make it extraterrestrial.",
            "It was not only Shag Harbour. That night produced reports from Wedgeport, Sambro, Halifax and Mahone Bay. "
            "Researcher Chris Styles - a 12-year-old Dartmouth boy at the time - calls it \"the Night of the UFOs\", and "
            "himself saw an orange orb over Halifax harbour.",
        ],
        "docs": [
            {"label": "CBC News - the man who phoned in Canada's most famous UFO sighting", "url": "https://www.cbc.ca/news/canada/nova-scotia/shag-harbour-ufo-incident-oct-4-1967-laurie-wickens-nova-scotia-9.7292815"},
            {"label": "LAC research guide - 1967 Shag Harbour UFO sighting and related research", "url": "https://recherche-research.bac-lac.gc.ca/eng/public/list/43130"},
            {"label": "Shag Harbour UFO Incident Society (interpretive centre, Hwy 3)", "url": "https://www.shagharbourincident.ca/"},
            {"label": "RCI - Oct 4 1967: the enduring Shag Harbour mystery", "url": "https://www.rcinet.ca/en/2017/10/04/canada-history-oct-4-1967-the-enduring-shag-harbour-mystery/"},
        ],
        "media": ["cbc-shag-2001", "cbc-shag-2010a", "cbc-shag-2010b", "cbc-shag-2017-history", "yt-shag-full"],
    },
    {
        "slug": "falcon-lake", "title": "Falcon Lake", "prov": "MB", "region": "Prairies / North",
        "date": "1967-05-20", "display": "20 May 1967", "conf": "primary",
        "lat": 50.10, "lon": -96.55, "tag": "Close encounter",
        "summary": "Stefan Michalak, a mechanic and amateur geologist prospecting near Falcon Lake, "
                   "watched a disc settle on flat rock, touched it, and was burned by a jet from it in a "
                   "grid pattern. The case remains officially unexplained.",
        "detail": [
            "Michalak heard geese flush, then a hissing sound and a smell of warm air and sulphur. The craft was smooth "
            "metal with no seams, with a bright doorway and panels of coloured light. He called out in eight languages; "
            "nothing answered. When he leaned towards the opening, a side door slid shut.",
            "His glove melted on contact. A panel of small holes rotated towards him and a blast of hot gas set his shirt "
            "and cap alight, leaving a grid of burns across his chest and stomach.",
            "He walked out of the bush, hitchhiked, and was treated at Winnipeg's Misericordia Hospital for first-degree "
            "burns. He did not mention a flying disc to medical staff. Items he recovered were analysed at an RCMP crime "
            "laboratory; the cause of the burns was never determined.",
            "Investigated by the RCMP, the RCAF and the Department of National Defence, and reviewed outside Canada by the "
            "US Air Force's Project Blue Book and the University of Colorado's Condon study. Editorials in 1967 called for "
            "the file to be released; on 6 November 1967 Defence Minister L\u00e9o Cadieux said the government would not publish it.",
            "Stan Michalak and Chris Rutkowski published When They Appeared - Falcon Lake 1967 in 2017. The Royal Canadian Mint "
            "struck a commemorative coin in 2018. The Canadian Mint and Library and Archives Canada both still describe the case as unsolved.",
            "Some details that circulate online - notably a 1967 reopening of Project Magnet and a 1968 DND report reading "
            "\"the case is unexplained\" - come only from enthusiast summaries and are not in the primary record. They are not repeated here as fact.",
        ],
        "docs": [
            {"label": "LAC podcast - UFOs at LAC: The Falcon Lake incident, part 1 (1:02:17)", "url": "https://www.canada.ca/en/library-archives/collection/engage-learn/podcasts/discover/episode-053.html"},
            {"label": "LAC podcast - part 2 (59:22)", "url": "https://www.canada.ca/en/library-archives/collection/engage-learn/podcasts/discover/episode-054.html"},
            {"label": "CBC News - Canada's best-documented UFO case, 50 years later", "url": "https://www.cbc.ca/news/canada/manitoba/falcon-lake-incident-book-anniversary-1.4121639"},
            {"label": "CBC News - Mint coin marks the Falcon Lake encounter", "url": "https://www.cbc.ca/news/canada/manitoba/mint-coin-manitoba-ufo-encounter-1.4602786"},
        ],
        "media": ["cbc-falcon-1983", "yt-falcon-full"],
    },
    {
        "slug": "gander-1974", "title": "Gander", "prov": "NL", "region": "Atlantic",
        "date": "1974-10-10", "display": "10-11 October 1974", "conf": "partial",
        "lat": 48.95, "lon": -54.60, "tag": "Airborne",
        "summary": "Over two nights at Gander, a Cessna pilot and later a Capital Airlines DC-8 each had an "
                   "object escort their aircraft. Radar saw nothing. The reports were copied to the NRC's "
                   "Upper Atmosphere Research Section in Ottawa.",
        "detail": [
            "At about 10:10 p.m. on 10 October a three-year Gander controller-pilot, flying a Cessna at 5,000 ft from "
            "Deer Lake, saw a solitary greenish light about 3,000 ft directly below. It stayed after he killed his "
            "navigation lights, then sped up, slowed down and lagged behind, repeating for roughly 25 minutes.",
            "A supervisor got it on radar for two sweeps only. It did not show as an aircraft. The track ran "
            "northwest to west and was believed to be at treetop level. Goose Bay early-warning was notified.",
            "At about 4:15 a.m. on 11 October a Capital Airlines DC-8 descending into Gander at 7,500 ft had an object "
            "of indistinguishable shape or size, flashing red and white, pull alongside on a parallel course for five "
            "to seven minutes, then enter cloud and vanish about five miles west. Radar showed nothing but the DC-8.",
            "The file was copied to the Upper Atmosphere Research Section, Astrophysics Branch, at the National Research "
            "Council in Ottawa - which had taken over UAP reporting that same year of 1967.",
            "Surviving here as a transcription of the archival file, not the file itself. The originals are worth an "
            "access-to-information request; treat the wording as provisional until they are read.",
        ],
        "docs": [
            {"label": "Transcription of the RCMP / Gander file (ufologie.patrickgross.org)", "url": "http://ufologie.patrickgross.org/htm/offica07.htm"},
            {"label": "LAC UFO database - query by province NL", "url": "https://www.collectionscanada.gc.ca/databases/ufo/001057-110.01-e.php?q4=NL&sk=0"},
        ],
        "media": [],
    },
    {
        "slug": "stephenville-2013", "title": "Stephenville", "prov": "NL", "region": "Atlantic",
        "date": "2013-03-31", "display": "31 March 2013", "conf": "primary",
        "lat": 48.55, "lon": -58.75, "tag": "Multi-aircraft",
        "summary": "Four aircraft at flight level 350 reported a large brightly lit object descending and "
                   "\"breaking up\" near Stephenville, one pilot describing it as resembling \"a large vehicle\" "
                   "and another as \"a space launch vehicle\".",
        "detail": [
            "The sequence begins with a low-level aircraft from Stephenville to Deer Lake reporting an unknown object "
            "descending at very high speed directly in front of it, near Stephenville.",
            "Within about ten minutes, four aircraft at FL350 reported a rapidly descending large object emitting bright "
            "lights. Pilots could not determine its colour or other specifics beyond its resemblance to a large vehicle.",
            "A Jazz Air crew described something that \"resembled a 'space launch vehicle'.\" The reports were passed to "
            "the Canadian National Defence Research and Development branch CANRADDT.",
            "This is one of the few Canadian cases with a contemporaneous, multi-aircraft, instrument-adjacent description "
            "rather than a single ground witness - and it sits inside the CIRVIS compilation released for 2010-2019.",
        ],
        "docs": [
            {"label": "CIRVIS Canada 2010-2019 compilation (p. 22) - local PDF, Release 03", "url": "#releases"},
            {"label": "Internet Archive mirror - CanadaUFO collection", "url": "https://archive.org/details/CanadaUFO"},
        ],
        "media": [],
    },
    {
        "slug": "nova-scotia-wave-1967", "title": "The Night of the UFOs", "prov": "NS", "region": "Atlantic",
        "date": "1967-10-04", "display": "4 October 1967", "conf": "reported",
        "lat": 44.37, "lon": -64.31, "tag": "Multi-site",
        "summary": "The same night as Shag Harbour, Nova Scotia produced a cluster of independent reports: "
                   "three lights in a triangle over a Lunenburg beach, an orange orb over Halifax harbour, "
                   "lights over Wedgeport and Sambro, and a cargo flight crew near Yarmouth.",
        "detail": [
            "On a Lunenburg beach at about 10:30 p.m., Wilfred C. Eisnor watched three motionless lights arranged in a "
            "triangle - two amber, one blue - and photographed them on a long exposure. They did not move for more than "
            "fifteen minutes.",
            "Near Hassett, shortly after 11 p.m., Cst. Ian Andrew saw a glowing light 60 to 90 m above the treeline, "
            "shaped like an upside-down candle flame with a corona, throwing sparks, making no sound.",
            "At Eastern Passage, William Thibeault watched three slow-moving white lights just before 8 p.m. Chris Styles, "
            "then 12, saw an orange orb over Halifax harbour that same night.",
            "A cargo flight near Yarmouth in the small hours of 5 October reported an object that \"danced\" with the "
            "aircraft on approach. Charles Bruce of Yarmouth also reported lights that night.",
            "The event is the anchor of a documentary tradition rather than a resolved file: CBC has returned to it in "
            "2001, 2010, twice in 2017 and again in 2026, when the last surviving public face of it, Laurie Wickens, died.",
        ],
        "docs": [
            {"label": "CBC News - the Night of the UFOs, 2026 retrospective", "url": "https://www.cbc.ca/news/canada/nova-scotia/shag-harbour-ufo-incident-oct-4-1967-laurie-wickens-nova-scotia-9.7292815"},
            {"label": "Vice - in search of the truth behind Canada's most infamous UFO sighting", "url": "https://www.vice.com/en/article/in-search-of-the-truth-behind-canadas-most-infamous-ufo-sighting/"},
        ],
        "media": ["cbc-shag-2017-history"],
    },
    {
        "slug": "saint-john-2012", "title": "Saint John", "prov": "NB", "region": "Atlantic",
        "date": "2012-06-19", "display": "19 June 2012", "conf": "reported",
        "lat": 45.27, "lon": -66.06, "tag": "Urban",
        "summary": "An object over Saint John, New Brunswick, near the Irving Oil refinery, left one man shaken. "
                   "CBC's own report paired it with the drone explanation - the media's default reading.",
        "detail": [
            "The sighting landed in the middle of a busy refinery district, which is exactly the situation in which "
            "commercial drones and aircraft are common and a witness is likely to be told what they saw.",
            "CBC's package included a video segment on drone encounters, which is the useful part: the mainstream "
            "explanation was available the same morning.",
            "It is included here as a case file because it shows the modern reporting pattern - witness, video, "
            "conventional explanation within 24 hours - that the 1967 files never got.",
        ],
        "docs": [
            {"label": "CBC News - 'UFO' sighting leaves Saint John man shaken", "url": "https://www.cbc.ca/news/canada/new-brunswick/ufo-sighting-leaves-saint-john-man-shaken-1.2818237"},
        ],
        "media": ["cbc-nb-drone"],
    },
    {
        "slug": "fredericton-2023", "title": "Fredericton", "prov": "NB", "region": "Atlantic",
        "date": "2023-07-26", "display": "26 July 2023", "conf": "reported",
        "lat": 45.95, "lon": -66.65, "tag": "Hearsay",
        "summary": "CBC reported a New Brunswick man convinced aliens were walking in the provincial capital, "
                   "on the same week as the United States' first UAP hearing in Congress.",
        "detail": [
            "The story is here as a document of the news cycle rather than an aviation or archival case: a regional "
            "UFO broadcast on national television in the week the US Congress held its first UAP hearing.",
            "Stanton Friedman, the physicist who became the public face of the subject, lived in Fredericton from the "
            "1970s until his death in 2020. His papers went to the Provincial Archives of New Brunswick. Whether they "
            "contain sighting reports is not established here, and is worth a direct request.",
        ],
        "docs": [
            {"label": "CBC - Are aliens walking around New Brunswick's capital city?", "url": "https://www.cbc.ca/player/play/video/1.6933942"},
        ],
        "media": ["cbc-nb-fredericton"],
    },
    {
        "slug": "moncton-2014", "title": "Moncton", "prov": "NB", "region": "Atlantic",
        "date": "2014-12-29", "display": "29 December 2014", "conf": "partial",
        "date_note": "Community report, not an official file",
        "lat": 46.09, "lon": -64.77, "tag": "Lights",
        "summary": "Three blinking lights in a diagonal pattern over Moncton on a December evening, "
                   "recorded on video and photographs by a witness and reported to a UFO society.",
        "detail": [
            "Reported at roughly 7 p.m. with video and photographs, and published by a regional UFO research society. "
            "This is a witness report, not a government record, and the site labels it that way.",
            "It appears here because maritime and eastern Canadian reports are systematically thinner in the archive "
            "than the two famous 1967 cases, and one honest small record is worth more than a gap.",
        ],
        "docs": [
            {"label": "No live source: the original regional UFO society record (psican.org) is offline", "url": ""},
        ],
        "media": [],
    },
    {
        "slug": "clarenville-1978", "title": "Clarenville", "prov": "NL", "region": "Atlantic",
        "date": "1978-10-26", "display": "26 October 1978", "conf": "partial",
        "lat": 48.16, "lon": -55.88, "tag": "Police observation",
        "summary": "A cigar-shaped object with a curved tail was seen by police at Clarenville, who used a "
                   "ball-scope and a size estimate; DND radar at Gander was alerted.",
        "detail": [
            "Const. Blackwood is recorded as using a ball-scope - a device borrowed from the Royal Canadian Mounted "
            "Police traffic bureau for estimating distance and size - and reporting the object at roughly forty feet "
            "across, hovering about five hundred feet above sea level.",
            "Defence radar at Gander was tasked with tracking it. The estimate is a witness estimate through an optical "
            "device, not an instrument measurement, and the file has not been read directly.",
            "October and November 1978 produced a run of reports up the Labrador coast, in Lethbridge, Catalina, "
            "Gander, St. Anthony and north, according to a published maritime case collection.",
        ],
        "docs": [
            {"label": "Case summary with provenance (ufoevidence.org)", "url": "http://ufoevidence.org/cases/case583.htm"},
        ],
        "media": [],
    },
    {
        "slug": "kensington-pei-2014", "title": "Kensington", "prov": "PE", "region": "Atlantic",
        "date": "2014-06-04", "display": "4 June 2014", "conf": "partial",
        "lat": 46.57, "lon": -63.57, "tag": "Video",
        "summary": "A Prince Edward Island man filmed about 22 minutes of unusual lights over the Gulf of St. "
                   "Lawrence while putting out a bonfire; MUFON later called it a confirmed sighting, and CBC "
                   "published conventional explanations.",
        "detail": [
            "The 22-minute recording is long enough to be checked frame by frame, which is rarer and more useful than "
            "most videos, and it attracted both a civilian determination and a broadcast debunking in the same week.",
            "The disagreement between \"confirmed\" and \"conventional explanations\" is the honest state of the record, "
            "and the site leaves it standing rather than picking a side.",
        ],
        "docs": [
            {"label": "Case listing with source trail", "url": "https://en.wikipedia.org/wiki/UFO_sightings_in_Canada"},
        ],
        "media": [],
    },
    {
        "slug": "yukon-2023", "title": "Yukon shootdown", "prov": "YT", "region": "North",
        "date": "2023-02-11", "display": "11 February 2023", "conf": "primary",
        "lat": 63.50, "lon": -136.00, "tag": "Military intercept",
        "summary": "NORAD downed a small cylindrical object at about 40,000 feet over central Yukon after it "
                   "violated Canadian airspace; Canadian and US aircraft were scrambled and a US F-22 fired on it. "
                   "RCMP recovered debris from a lake shore.",
        "detail": [
            "Prime Minister Trudeau ordered the object taken down, describing it as unidentified and saying it had "
            "violated Canadian airspace. A US F-22 fired on it and Canadian Forces were tasked with recovery and analysis.",
            "Defence Minister Anita Anand described a small cylindrical object at roughly 40,000 feet, downed about "
            "100 miles from the US border. RCMP said to CTV News that debris on a lake shore was recovered.",
            "It was the third such interception in a week: 10 February over northern Alaska, 11 February over Yukon, "
            "12 February over Lake Huron - an object first detected over Alberta.",
            "Canadian MPs have since filed written questions on the follow-up. Question 3227, tabled 28 November 2024 "
            "by MP Larry Maguire, asks how many such objects have been tracked since 1 January 2023 and refers to the "
            "Yukon object as \"UAP 23\". It is the clearest paper trail from the intercept to Parliament - and it was never answered.",
        ],
        "docs": [
            {"label": "CBC - Trudeau on the takedown of an unidentified object", "url": "https://www.cbc.ca/news/politics/norad-monitoring-airborne-object-north-1.6745575"},
            {"label": "CBC - the objects downed over Yukon, Alberta and Lake Huron", "url": "https://www.cbc.ca/news/politics/trudeau-unidentified-objects-1.6746708"},
            {"label": "House of Commons - Written Question 3227 (28 November 2024)", "url": "https://www.ourcommons.ca/written-questions/44-1/q-3227"},
            {"label": "Sky Canada Project report, June 2025 - the same incident in the federal record", "url": "https://www.science.gc.ca/site/science/sites/default/files/documents/sky-canada-report.pdf"},
        ],
        "media": [],
    },
    {
        "slug": "falcon-lake-wave-1967", "title": "Falcon Lake region, 1967 wave", "prov": "MB", "region": "Prairies / North",
        "date": "1967-06-30", "display": "June-November 1967", "conf": "reported",
        "lat": 50.75, "lon": -97.10, "tag": "Wave",
        "summary": "Falcon Lake was not a single event. Through the summer of 1967, reports clustered across "
                   "southeastern Manitoba, which is why Defence ministers were questioned in the press and why "
                   "the file stayed closed.",
        "detail": [
            "By 30 June 1967 the press was reporting that Michalak's case was under Defence investigation amid a "
            "surge of reports in the area, and by November 1967 newspaper comic strips were dramatising the case.",
            "By the following year, Michalak himself was publicly alleging a cover-up to avoid a panic, and editorials "
            "were pressing for release of the file.",
            "The 1967 concentration of reports across Manitoba and eastern Canada is the closest Canada came to the "
            "kind of wave that made the US records newsworthy - and the official response was closure, not study.",
        ],
        "docs": [
            {"label": "LAC podcast - Falcon Lake investigation, part 1", "url": "https://www.canada.ca/en/library-archives/collection/engage-learn/podcasts/discover/episode-053.html"},
            {"label": "LAC podcast - part 2", "url": "https://www.canada.ca/en/library-archives/collection/engage-learn/podcasts/discover/episode-054.html"},
        ],
        "media": [],
    },
    {
        "slug": "baffin-island-2018", "title": "Baffin Island", "prov": "NU", "region": "North",
        "date": "2018-11-24", "display": "24 November 2018", "conf": "primary",
        "lat": 66.50, "lon": -61.25, "tag": "Airborne, official record",
        "summary": "A Nolinor Aviation Boeing 737-200 crew reported an unidentified object at 8:30 p.m. while "
                   "flying from Iqaluit toward the Mary River mine. Transport Canada logged it, advised NORAD, and "
                   "closed it as preliminary and unsubstantiated.",
        "detail": [
            "The filing offered the usual menu of explanations - weather balloon, meteor, rocket, or an "
            "unidentified flying object - and NORAD was notified, as procedure requires when a civilian pilot "
            "reports something at altitude.",
            "The flight was logged with no impact to operations. Transport Canada described the information as "
            "preliminary, unsubstantiated and subject to change, which is what an official record looks like when "
            "it stays inconclusive on purpose.",
            "Nunavut has no case in this index other than this one, and that imbalance is itself worth noting: the "
            "federal file is thickest where witnesses are densest.",
        ],
        "docs": [
            {"label": "Nunatsiaq - pilots spot possible UFO above Nunavut's northern Baffin Island", "url": "https://nunatsiaq.com/stories/article/65674pilots_spot_possible_ufo_above_nunavuts_northern_baffin_island/"},
            {"label": "Transport Canada - high-altitude object incidents", "url": "https://tc.canada.ca/en/binder/4-high-altitude-object-incidents"},
        ],
        "media": [],
    },
    {
        "slug": "montreal-1990", "title": "Bonaventure Hotel, Montreal", "prov": "QC", "region": "Quebec",
        "date": "1990-11-07", "display": "7 November 1990", "conf": "reported",
        "lat": 45.50, "lon": -73.57, "tag": "Multi-witness",
        "summary": "About forty people on a Montreal rooftop pool watched for three hours as eight to ten lights "
                   "in a ring projected bright rays around a round object, then drifted north. Air traffic control "
                   "recorded nothing.",
        "detail": [
            "The sighting ran from roughly 7:20 to 10:20 p.m. The object was described as a flattened metallic "
            "form some 540 metres across, with lights arranged in a circle on its perimeter.",
            "Wingers varied in intensity as the object moved, which is the detail investigators kept returning to: "
            "a wing-shaped craft banking should change the angle, and observers said it did not.",
            "Air traffic control confirmed no radar activity corresponding to the object. Several witnesses later "
            "appeared on CBC Television.",
            "It is one of the better-sourced Canadian cases outside the two 1967 events, and it sits in the "
            "hundreds-of-witnesses category rather than the single-witness category that dominates the archive.",
        ],
        "docs": [
            {"label": "Case summary with press sourcing (La Presse, CBC-TV)", "url": "https://en.wikipedia.org/wiki/UFO_sightings_in_Canada"},
        ],
        "media": [],
    },
    {
        "slug": "yukon-1996", "title": "The row of lights", "prov": "YT", "region": "North",
        "date": "1996-12-11", "display": "11 December 1996", "conf": "reported",
        "lat": 60.72, "lon": -135.05, "tag": "Multi-site",
        "summary": "At least 31 people across four separate areas of the Yukon reported a row of lights in the "
                   "sky, several describing it as spacecraft-like, with others seeing it later from different places.",
        "detail": [
            "The distinguishing feature is dispersion: four separate groups, different locations, and later "
            "observations from further away - the kind of geometry that lets researchers reconstruct a track "
            "rather than a single anecdote.",
            "The Sky Canada Project report cites this case among Canada's notable historical encounters, which "
            "makes it part of the federal record's own history section.",
            "Contemporary reporting is thin, and no original file has been read. The count of 31 comes from the "
            "Canadian Press retrospective, which is press rather than archive.",
        ],
        "docs": [
            {"label": "Canadian Press retrospective on well-known Canadian UFO sightings", "url": "https://winnipeg.citynews.ca/2025/07/18/some-of-the-best-known-canadian-ufo-sightings-over-the-years/"},
            {"label": "Sky Canada Project report - the same case in the federal record", "url": "https://www.science.gc.ca/site/science/sites/default/files/documents/sky-canada-report.pdf"},
        ],
        "media": [],
    },
    {
        "slug": "gander-1951", "title": "Gander", "prov": "NL", "region": "Atlantic",
        "date": "1951-02-10", "display": "10 February 1951", "conf": "partial",
        "lat": 48.95, "lon": -54.60, "tag": "Airborne",
        "summary": "A United States Navy aircraft bound for Iceland reported a near-collision with a large "
                   "orange circular object that, in the pilot's words, almost literally flew circles around it.",
        "detail": [
            "It is the earliest dated case in this index and it sits in the same place as the 1974 Gander "
            "encounters: the Gander terminal has been a recurring waypoint for reports of objects near the "
            "transatlantic track.",
            "The report came from a US Navy crew, which means it would have entered American systems - and the "
            "Canadian side of it is a reference rather than a file anyone here has read.",
            "Sourcing is a published summary of a Blue Book-era report rather than the report itself. Treat the "
            "wording as indicative until the original is found.",
        ],
        "docs": [
            {"label": "Case listing with source trail", "url": "https://en.wikipedia.org/wiki/UFO_sightings_in_Canada"},
        ],
        "media": [],
    },
    {
        "slug": "new-brunswick-nuclear-2002", "title": "New Brunswick protected airspace", "prov": "NB", "region": "Atlantic",
        "date": "2002-02-14", "display": "14 February 2002", "conf": "reported",
        "lat": 45.85, "lon": -66.75, "tag": "Official record",
        "summary": "A CADORS report logged an unidentified aerial phenomenon over protected airspace in New "
                   "Brunswick — the kind of record that sits in a federal database and never gets analysed.",
        "detail": [
            "CADORS report 2002A0096 covers an incident on 14 February 2002 near protected airspace in the "
            "province. It is a real entry in a real federal system, and it is the kind of record most researchers "
            "never see because nobody publishes the analysis.",
            "The pairing matters: this sits in the same series as the 2018 Baffin Island report and the 2013 "
            "Stephenville reports, and all three are cases where the government logged the sighting and then "
            "did nothing with it.",
            "Coverage comes from The Walrus, which is journalism rather than the file itself. The report number is "
            "given so it can be requested directly.",
        ],
        "docs": [
            {"label": "The Walrus - the truth behind UFO sightings over Canada's nuclear facilities", "url": "https://thewalrus.ca/the-truth-behind-ufo-sightings-over-canadas-nuclear-facilities/"},
            {"label": "Transport Canada - CADORS Manual TP 4044", "url": "https://tc.canada.ca/en/aviation/aviation-publications/civil-aviation-daily-occurrence-reporting-system-cadors-manual-tp-4044"},
        ],
        "media": [],
    },
    {
        "slug": "prince-george-1969", "title": "Prince George", "prov": "BC", "region": "West",
        "date": "1969-01-01", "display": "1 January 1969", "conf": "partial",
        "lat": 53.92, "lon": -122.75, "tag": "Multi-witness",
        "summary": "Three unrelated witnesses in British Columbia reported a round object radiating a yellow-orange "
                   "light, apparently climbing from 2,000 to 10,000 feet in the late afternoon.",
        "detail": [
            "Three independent witnesses with no apparent connection to each other is the strongest part of this "
            "report, and the apparent climb is the detail that most distinguishes a disc from a balloon.",
            "It is included to keep the west in the record: almost every well-documented Canadian case is eastern, "
            "and that skew is a property of the archive rather than of the sky.",
            "Sourcing is thin and no original file has been located. UFO*BC maintains a separate history index for "
            "British Columbia material.",
        ],
        "docs": [
            {"label": "Case listing with source trail", "url": "https://en.wikipedia.org/wiki/UFO_sightings_in_Canada"},
            {"label": "UFO*BC - British Columbia UFO history index", "url": "https://ufobc.ca/History/index.htm"},
        ],
        "media": [],
    },
]

# ----------------------------------------------------------------- 3. timeline
TIMELINE = [
    ("1947", "Project Sign era begins", "The first modern sighting wave reaches Canada. Wartime security apparatus in both Canada and the United States is already watching the sky."),
    ("1950", "Project Magnet starts", "The Department of Transport lets engineer Wilbert Smith research, part time, whether UFOs could ride Earth's magnetic field. Smith later sets up a UFO observatory outside Ottawa and launches a balloon over the city to watch for reports. The project is terminated in 1954."),
    ("1952", "Project Second Storey", "The Defence Research Board forms a committee to look at flying saucers crossing Canadian territory as reported by the armed services. It is chaired by the NRC astronomer Dr. Peter Millman."),
    ("1954", "JANAP 146(C)", "Joint Chiefs of Staff issue Communication Instructions for Reporting Vital Intelligence Sightings from airborne and waterborne sources - the ancestor of the mandatory pilot reports that run for decades."),
    ("1957", "The federal file opens", "One of the earliest documents in the National Defence UFO file is dated 24 November 1957. The Library and Archives Canada collection eventually runs from 1947 to the early 1980s, about 9,500 digitized documents."),
    ("1967", "Two cases that stuck", "20 May, Falcon Lake, Manitoba: Stefan Michalak is burned by a disc. 4 October, Shag Harbour, Nova Scotia: an object goes into the water and is never found. Both remain officially unexplained."),
    ("1967", "The NRC takes over", "On the recommendation of the Minister of National Defence, responsibility for UFO reports transfers to the National Research Council, which runs the file into the 1990s."),
    ("1970", "Maritime reports accumulate", "An RCMP report on a Halifax County sighting of 9 December 1970 lands in the NRC's Herzberg Institute file - one of many Atlantic records that were filed and then forgotten."),
    ("1974", "Gander", "Two nights of airborne encounters over Newfoundland, with a Cessna at 5,000 ft and a Capital Airlines DC-8 both reporting an object; the file is copied to the NRC's Upper Atmosphere Research Section in Ottawa."),
    ("1978", "The Labrador run", "Reports move up the Labrador coast through late 1978 - Clarenville, Gander, St. Anthony - with police and radar involved in at least one of them."),
    ("1990s", "The file closes", "NRC collection ends. For decades there is no federal body collecting public UAP reports at all, and pilots still file mandatory occurrence reports into CADORS with no analysis."),
    ("2010-2019", "CIRVIS", "Vital-information sighting reports continue to be filed by pilots, air traffic controllers and crews, and are released as a ten-year compilation in 2021 through an access-to-information request."),
    ("2019", "Library and Archives Canada publishes the podcast", "The LAC Discover podcast runs a two-part episode on the Falcon Lake case with Stan Michalak, Chris Rutkowski and Palmiro Campagna, drawing directly on the archived files."),
    ("2023-02-11", "Yukon", "NORAD downs an object at 40,000 feet over central Yukon after Canadian and US aircraft are scrambled. A third interception in a week; the RCMP recovers debris."),
    ("2024-11-28", "Question 3227", "MP Larry Maguire tables a written question asking how many unidentified objects have been tracked since January 2023, referring to the Yukon intercept as \"UAP 23\"."),
    ("2025-06", "Sky Canada Project", "The Office of the Chief Science Advisor publishes Management of Public Reporting of Unidentified Aerial Phenomena in Canada - 59 pages, 14 recommendations, and a recommendation that a federal department be named to hold the file."),
    ("2026", "The question goes unanswered", "Written Question 3227, on the Yukon intercept, sat unanswered until the 44th Parliament dissolved. The Library of Parliament now marks it as historical information the government is no longer required to answer."),
    ("2026-07", "Sixty years, still a visitor centre", "The Shag Harbour UFO Incident Society keeps the interpretive centre on Highway 3 open, and the case still draws an annual gathering. The first caller, Laurie Wickens, died in 2026 at 76."),
    ("2026", "The United States releases, Canada does not", "The US Department of War releases declassified UAP records in tranches under PURSUE, starting 8 May 2026; the sixth tranche followed on 18 September 2026. No Canadian equivalent has followed, and the Sky Canada Project's first recommendation - name a department to hold the file - is still unimplemented.", True),
]

# ------------------------------------------------------------------ 4. media
MEDIA = [
    {"id": "cbc-shag-2017-history", "kind": "cbc", "src": "https://www.cbc.ca/player/play/video/1.4315042?autoplay=0",
     "title": "The history of the Shag Harbour UFO incident", "publisher": "CBC News", "date": "30 September 2017",
     "len": "3:27", "pos": "On 4 Oct. 1967, multiple witnesses reported bright lights that then disappeared into the ocean. Witnesses suspected a plane crash; nothing was ever found."},
    {"id": "cbc-shag-2017-archive", "kind": "cbc", "src": "https://www.cbc.ca/player/play/video/1.4125558?autoplay=0",
     "title": "The Shag Harbour UFO mystery", "publisher": "CBC (from the archives, Rob Gordon)", "date": "20 May 2017",
     "len": "2:02", "pos": "A period news report on the 1967 incident and the search that followed it."},
    {"id": "cbc-shag-2001", "kind": "cbc", "src": "https://www.cbc.ca/player/play/video/1.3593065?autoplay=0",
     "title": "The 1967 Shag Harbour UFO incident revisited", "publisher": "CBC, Canada Now (archives)", "date": "4 June 2001",
     "len": "1:50", "pos": "Coverage from the year Canada Post commemorated the event with a stamp - which is how the file entered the national memory."},
    {"id": "cbc-shag-2010a", "kind": "cbc", "src": "https://www.cbc.ca/player/play/video/1.1784248?autoplay=0",
     "title": "Shag Harbour UFO mystery", "publisher": "CBC News", "date": "3 August 2010", "len": "2:40",
     "pos": "Retrospective on the case and the controversy around it."},
    {"id": "cbc-shag-2010b", "kind": "cbc", "src": "https://www.cbc.ca/player/play/video/1.1784194?autoplay=0",
     "title": "Shag Harbour Mystery", "publisher": "CBC News", "date": "3 August 2010", "len": "1:50",
     "pos": "Short retrospective segment."},
    {"id": "cbc-falcon-1983", "kind": "cbc", "src": "https://www.cbc.ca/player/play/video/1.3589960?autoplay=0",
     "title": "The Falcon Lake incident: Canada's famous UFO encounter in 1967", "publisher": "CBC, Take 30 (archives)", "date": "aired 21 February 1983",
     "len": "3:28", "pos": "Manitoba UFO researcher Edward Barker describes Stefan Michalak's sighting, sixteen years after the fact, on a national talk show."},
    {"id": "cbc-nb-drone", "kind": "cbc", "src": "https://www.cbc.ca/player/play/video/1.2817983?autoplay=0",
     "title": "Drone encounters", "publisher": "CBC News", "date": "June 2012", "len": "2:31",
     "pos": "The conventional explanation, broadcast alongside the Saint John sighting it explained."},
    {"id": "cbc-nb-fredericton", "kind": "cbc", "src": "https://www.cbc.ca/player/play/video/1.6933942?autoplay=0",
     "title": "Are aliens walking around New Brunswick's capital city?", "publisher": "CBC News, Fredericton", "date": "July 2023",
     "len": "2:15", "pos": "A regional UAP story in the week the US Congress held its first UAP hearing - a useful record of how the cycle is actually driven."},
    {"id": "yt-shag-full", "kind": "yt", "src": "https://www.youtube.com/embed/mPbDa5D7IUE",
     "title": "The Shag Harbour UFO Incident - Full Documentary", "publisher": "Ocean Digital Entertainment", "date": "11 September 2015",
     "len": "long form", "pos": "Canadian documentary on the incident, drawing on the Coast Guard, RCMP and Armed Forces investigations. Includes researcher Chris Styles, who was a witness that night."},
    {"id": "yt-shag-4k", "kind": "yt", "src": "https://www.youtube.com/embed/AffaetLkx2U",
     "title": "Canada's famous officially investigated UFO incident | Shag Harbour", "publisher": "Exploring with Wade", "date": "2019",
     "len": "long form", "pos": "Retrospective video essay on the file and what officials did and did not conclude."},
    {"id": "yt-falcon-full", "kind": "yt", "src": "https://www.youtube.com/embed/Hx968LHEXiY",
     "title": "The Falcon Lake Incident | Full Documentary", "publisher": "Mediatime Network", "date": "3 March 2024",
     "len": "long form", "pos": "Documentary treatment of the Michalak encounter and the investigations it triggered."},
    {"id": "yt-canada-crash", "kind": "yt", "src": "https://www.youtube.com/embed/XHm7KMRMTTE",
     "title": "The Canadian UFO crash that hasn't been debunked", "publisher": "PaytonMoreland", "date": "2024",
     "len": "long form", "pos": "Makes the \"crash scenario\" argument for Shag Harbour. Included as an example of advocacy framing, not as evidence."},
]

# LAC Discover podcast episodes (mp3 resolved at build time when reachable)
PODCASTS = [
    {"id": "lac-053", "title": "UFOs at LAC: The Falcon Lake incident, part 1", "len": "1:02:17", "size": "58 MB",
     "published": "15 May 2019",
     "url": "https://www.canada.ca/en/library-archives/collection/engage-learn/podcasts/discover/episode-053.html"},
    {"id": "lac-054", "title": "UFOs at LAC: The Falcon Lake incident, part 2", "len": "59:22", "size": "54 MB",
     "published": "29 May 2019",
     "url": "https://www.canada.ca/en/library-archives/collection/engage-learn/podcasts/discover/episode-054.html"},
]

# ------------------------------------------------------- 5. open-data endpoints
ENDPOINTS = [
    {"name": "Open Government Data Catalogue (CKAN API)", "org": "Government of Canada",
     "url": "https://open.canada.ca/data/api/3/action/package_search?q=UFO",
     "note": "Live JSON. Every dataset on open.canada.ca is queryable. Swap the q= term.",
     "examples": ["?q=UFO", "?q=%22unidentified%20aerial%20phenomena%22", "?q=CADORS"]},
    {"name": "Open Government search page", "org": "Government of Canada",
     "url": "https://open.canada.ca/data/en/dataset?q=UFO",
     "note": "Same catalogue, human-readable."},
    {"name": "Library and Archives Canada - Canada's UFOs", "org": "Library and Archives Canada",
     "url": "https://www.canada.ca/en/library-archives/collection/research-help/science-technology/ufos.html",
     "note": "Scope page: four origin departments, 1947 to the early 1980s, about 9,500 digitized documents, and the searchable fields."},
    {"name": "LAC UFO database - browse by department", "org": "Library and Archives Canada",
     "url": "https://www.collectionscanada.gc.ca/databases/ufo/001057-110.01-e.php?q7=National+Research+Council&interval=50&sk=0",
     "note": "The live index. The q7 term is the record group; sk pages through results."},
    {"name": "LAC UFO database - browse by province", "org": "Library and Archives Canada",
     "url": "https://www.collectionscanada.gc.ca/databases/ufo/001057-110.01-e.php?q4=NB&sk=0",
     "note": "q4 filters by province or territory. NB, NS, NL, PE all return records."},
    {"name": "LAC research guide - 1967 Shag Harbour sighting", "org": "Library and Archives Canada",
     "url": "https://recherche-research.bac-lac.gc.ca/eng/public/list/43130",
     "note": "Curated path to the Shag Harbour material, including RG 77 volume and microfilm references."},
    {"name": "Sky Canada Project - report page", "org": "Office of the Chief Science Advisor",
     "url": "https://science.gc.ca/site/science/en/office-chief-science-advisor/sky-canada-project",
     "note": "Landing page for the June 2025 federal report on UAP reporting in Canada."},
    {"name": "Sky Canada Project - report in full text (HTML)", "org": "Office of the Chief Science Advisor",
     "url": "https://science.gc.ca/site/science/en/office-chief-science-advisor/sky-canada-project/management-public-reporting-unidentified-aerial-phenomena-canada",
     "note": "The whole report as HTML, including all fourteen recommendations, the five named gaps and the CSA's message. The easiest of the three to cite from."},
    {"name": "Sky Canada Project - full report (59 pp, PDF)", "org": "Office of the Chief Science Advisor",
     "url": "https://www.science.gc.ca/site/science/sites/default/files/documents/sky-canada-report.pdf",
     "note": "ISBN 978-0-660-78645-2. Fourteen recommendations, the history of federal reporting, and the 2023-2024 consultation."},
    {"name": "Government of Canada Publications catalogue entry", "org": "Public Services and Procurement",
     "url": "https://publications.gc.ca/site/eng/9.954480/publication.html",
     "note": "Bibliographic record with MARC formats."},
    {"name": "House of Commons - Written Question 3227 (Yukon object, 2023)", "org": "Parliament of Canada",
     "url": "https://www.ourcommons.ca/written-questions/44-1/q-3227",
     "note": "Tabled 28 November 2024 by MP Larry Maguire. Asks how many unidentified objects were tracked since 1 January 2023. No answer on file at time of writing."},
    {"name": "House of Commons - Written Question 1320 (five-year breakdown, 2026)", "org": "Parliament of Canada",
     "url": "https://www.ourcommons.ca/written-questions/45-1/q-1320",
     "note": "Asked 15 June 2026 for UAP incidents in Canada by month with location, summary and cause."},
    {"name": "House of Commons - all written questions on UFOs", "org": "Parliament of Canada",
     "url": "https://www.ourcommons.ca/written-questions/questions?parlsession=44-1&text=topic%3A%22Unidentified+flying+object%22&view=list",
     "note": "Searchable index of the parliamentary paper trail."},
    {"name": "LAC Discover podcast (Falcon Lake, two parts)", "org": "Library and Archives Canada",
     "url": "https://www.canada.ca/en/library-archives/collection/engage-learn/podcasts/discover/episode-053.html",
     "note": "Interviews with Stan Michalak, Chris Rutkowski and Palmiro Campagna, drawn from the archived files."},
    {"name": "Internet Archive - CanadaUFO collection", "org": "Internet Archive",
     "url": "https://archive.org/details/CanadaUFO",
     "note": "An 8,000-page mirror of the declassified Canadian file, filed under original government file numbers. Useful for download; provenance is LAC to NetContents to a 2021 scan."},    {"name": "The 2025 Canadian UFO Survey (Ufology Research)", "org": "Ufology Research",
     "url": "https://img1.wsimg.com/blobby/go/c23c8b29-268f-4742-a45e-2dba156b0e52/Final%20-%20The%202025%20Canadian%20UFO%20Survey.pdf",
     "note": "The successor to the Canadian UFO Survey after ufologyresearch.ca went offline. 26 pages: 1,052 Canadian reports in 2025, and a five-way split of conclusions."},
    {"name": "CTV News - 17 UAP-like pilot reports in 2023", "org": "CTV News",
     "url": "https://www.ctvnews.ca/sci-tech/multiple-flights-reported-strange-lights-in-the-sky-over-quebec-during-one-day-in-2023-1.6742406",
     "note": "Daniel Otis, 26 January 2024. The CADORS pilot-report count that the Sky Canada Project report cites: \"at least 17\" from 2023, with 11 more from 2022."},
    {"name": "Transport Canada - high-altitude object incidents", "org": "Transport Canada",
     "url": "https://tc.canada.ca/en/binder/4-high-altitude-object-incidents",
     "note": "The civil aviation guidance page for objects encountered at altitude - the closest thing Canada has to a UAP reporting procedure."},
    {"name": "Transport Canada - CADORS Manual TP 4044", "org": "Transport Canada",
     "url": "https://tc.canada.ca/en/aviation/aviation-publications/civil-aviation-daily-occurrence-reporting-system-cadors-manual-tp-4044",
     "note": "What CADORS collects, who files, and how occurrence reports are handled."},
    {"name": "NUFORC - Canadian report index by province", "org": "National UFO Reporting Center (US)",
     "url": "https://nuforc.org/subndx/?id=lNB",
     "note": "A civilian US reporting centre's index of Canadian cases. Blocks non-browser clients; NB shows 229 entries, NS 257, NL 63, PE 28, MB 270, ON 2,732, QC 476, AB 779."},
    {"name": "Shag Harbour UFO Incident Society - visitor centre", "org": "Shag Harbour UFO Incident Society",
     "url": "https://www.shagharbourincident.ca/visit.html",
     "note": "The interpretive centre on Highway 3, and a live annual gathering. Sixty years on, the case is still generating visitors."},
    {"name": "CBC Terms of Use", "org": "CBC / Radio-Canada",
     "url": "https://cbc.radio-canada.ca/en/vision/governance/terms-of-use-digital-services",
     "note": "The rightsholder's own terms for the news footage linked on the media page."},

]


# Ufology Research, The Canadian UFO Survey. The 2024 edition is the successor to the
# retired Canadian UFO Survey series; ufologyresearch.ca no longer resolves, so the
# current edition is served from the publisher's document host.
# Ufology Research's Canadian UFO Survey. This file is the single source for
# every survey figure on the site: index.html renders the cards from it, and
# llms.txt advertises it. It used to be a three-row stub that still repeated the
# "largest edition yet" claim the prose had already been corrected on.
#
# The record is 1,982 reports in 2012; 1,052 in 2025 is the biggest year since
# 2020 and the fifth highest of the series. Any note that implies otherwise is
# wrong.
SURVEY = [
    {"year": "2012", "reports": 1982, "note": "The record for the survey's history."},
    {"year": "2019", "reports": 849},
    {"year": "2020", "reports": 1243},
    {"year": "2021", "reports": 722},
    {"year": "2022", "reports": 768},
    {"year": "2023", "reports": 570, "note": "The figure the Sky Canada Project report cites."},
    {"year": "2024", "reports": 1008, "unexplained_pct": 3.77, "explained_pct": 14,
     "note": "Fewer than four per cent unexplained."},
    {"year": "2025", "reports": 1052, "unexplained_pct": 3.42, "explained_pct": 16.83,
     "probable_pct": 33.46, "insufficient_pct": 46.29,
     "long_run_unexplained_pct": 10.22,
     "nocturnal_pct": 50.24,
     "top_shape": "point source of light",
     "top_shape_pct": 52,
     "disc_reports": 52,
     "avg_duration_min": 47,
     "prev_avg_duration_min": {"2024": 36, "2023": 16, "2022": 13},
     "by_province": {"ON": 307, "QC": 210, "BC": 131},
     "note": ("One report every eight hours, the biggest year since 2020 and the fifth highest "
              "on record. 36 of the 1,052 were unexplained, against a 10.22% average over the "
              "preceding 35 years. The survey's own caveat: a report of 'unknown' does not imply "
              "alien visitation.")},
]

# The series runs since 1989 and totals more than 24,000 reports.
SURVEY_META = {
    "publisher": "Ufology Research",
    "series_url": "https://img1.wsing.com/blobby/go/c23c8b29-268f-4742-a45e-2dba156b0e52/final%20-%20The%202025%20Canadian%20UFO%20Survey.pdf",
    "since": 1989,
    "catalogued_total": 24000,
    "prior_years": [2019, 2020, 2021, 2022, 2023, 2024],
}

if __name__ == "__main__":
    build_geometry()
    w("cases.json", CASES)
    # The fourth tuple element marks the single live entry; the renderer used
    # to infer it from the year, which lit up every 2026 row at once.
    w("timeline.json", [({"year": y, "title": ti, "body": b} if len(row) == 3
                         else {"year": y, "title": ti, "body": b, "now": True})
                        for row in TIMELINE for y, ti, b in [row[:3]]])
    w("media.json", MEDIA)
    w("podcasts.json", PODCASTS)
    w("endpoints.json", ENDPOINTS)
    w("survey.json", {"meta": SURVEY_META, "years": SURVEY})
    print("done")
