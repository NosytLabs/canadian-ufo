/* AURORA — shared behaviour: nav, accordions, data renderers */
(function () {
  "use strict";

  var A = window.Aurora;
  var $ = A.$, $$ = A.$$, ready = A.ready, fetchJSON = A.fetchJSON, esc = A.esc;
  var narrow = A.narrow;

  /* ------------------------------------------------------------- chrome */
  ready(function () {
    var t = $(".nav-toggle");
    var nav = $("#nav");
    if (t && nav) {
      t.addEventListener("click", function () {
        var open = nav.classList.toggle("open");
        t.setAttribute("aria-expanded", String(open));
        t.textContent = open ? "\u2715" : "\u2630";
      });
      nav.addEventListener("click", function (e) {
        if (e.target.tagName === "A" && narrow()) {
          nav.classList.remove("open");
          t.setAttribute("aria-expanded", "false");
          t.textContent = "\u2630";
        }
      });
    }

    // FAQ accordions. One open at a time: six answers expanded at once is a
    // wall of text that pushed the page past a thousand pixels on its own, and
    // a closed <details> is still in the DOM for crawlers and screen readers.
    // The state is re-applied on a breakpoint change, so crossing it never
    // leaves every answer collapsed until a reload.
    var faqs = $$(".qa details");
    function setFaqState() {
      faqs.forEach(function (d, i) { d.open = i === 0; });
    }
    var faqMQ = window.matchMedia("(max-width: 940px)");
    setFaqState();
    if (faqMQ.addEventListener) faqMQ.addEventListener("change", setFaqState);
    else if (faqMQ.addListener) faqMQ.addListener(setFaqState);
  });

  /* ------------------------------------------------------------ releases */
  function renderDocs() {
    var host = $("#doc-grid");
    if (!host) return;
    var docs = [], releases = [];
    fetchJSON("data/releases.json").then(function (d) {
      docs = d.documents || [];
      releases = d.releases || [];
      wire();
    }).catch(function (e) {
      host.innerHTML = '<div class="error-note">Could not load the release index: ' + e.message + "</div>";
    });

    var q = "", rel = "all", prov = "all", page = 0, PER = 12;

    // Counts over the set this filter actually applies to -- the release
    // documents -- not over the much larger archival index. Note it is `docs`,
    // not `releases`: releases are the five tranche descriptors and carry no
    // source, so counting those yields zero for every group.
    function releaseCounts(docs) {
      var out = { DND: 0, TRANSPORT: 0, NRC: 0, RCMP: 0 };
      docs.forEach(function (d) { var p = docProvince(d); if (p) out[p] += 1; });
      return out;
    }

    // One document can name more than one body. NRC and RCMP are checked first
    // because they are unambiguous, then Transport (which the Coast Guard rows
    // share), then National Defence, which is the most frequent label and the
    // one the ATIP volumes genuinely came from.
    function docProvince(d) {
      var s = d.source || "";
      if (s.indexOf("National Research Council") >= 0) return "NRC";
      if (s.indexOf("Mounted Police") >= 0) return "RCMP";
      if (s.indexOf("Transport") >= 0 || s.indexOf("Coast Guard") >= 0) return "TRANSPORT";
      if (s.indexOf("National Defence") >= 0) return "DND";
      return null;
    }

    function matches(d) {
      if (rel !== "all" && d.release !== rel) return false;
      if (prov !== "all" && docProvince(d) !== prov) return false;
      if (!q) return true;
      var hay = [d.id, d.title, d.subtitle, d.source, d.date, d.location, d.type].join(" ").toLowerCase();
      return hay.indexOf(q) >= 0;
    }

    function card(d) {
      var href = esc(d.file || d.external || "#");
      var media = d.thumb
        ? '<img src="' + esc(d.thumb) + '" alt="First page of ' + esc(d.title) + '" loading="lazy">'
        : '<span class="ph">' + esc(d.type) + "</span>";
      var title = esc(d.title) + " (opens the public mirror)";
      return '<a class="doc" href="' + href + '" target="_blank" rel="noopener" title="' + title + '">' +
        '<span class="doc-thumb">' + media + "</span>" +
        '<span class="doc-body">' +
          '<span class="doc-id">' + esc(d.id) + "</span>" +
          "<h3>" + esc(d.title) + "</h3>" +
          "<p>" + esc(d.subtitle || "") + "</p>" +
          '<span class="doc-foot">' +
            '<span class="chip">' + esc(d.date) + "</span>" +
            (d.pages ? '<span class="chip">' + Number(d.pages).toLocaleString("en-CA") + " pp</span>" : "") +
            '<span class="chip chip-a">' + esc(d.type) + "</span>" +
            '<span class="chip">Release ' + esc(d.release) + "</span>" +

          "</span>" +
        "</span></a>";
    }

    function draw() {
      var list = docs.filter(matches);
      var pages = Math.max(1, Math.ceil(list.length / PER));
      page = Math.min(page, pages - 1);
      var slice = list.slice(page * PER, page * PER + PER);
      var note = $("#doc-count");
      if (note) note.textContent = list.length + " of " + docs.length + " records";
      host.innerHTML = slice.length
        ? slice.map(card).join("")
        : '<div class="error-note">No records match those filters.</div>';
      pager($("#doc-pager"), page, pages, function (p) {
        page = p; draw(); host.scrollIntoView({ block: "nearest" });
      });
    }

    function wire() {
      var input = $("#doc-search");
      if (input) {
        var t;
        input.addEventListener("input", function () {
          clearTimeout(t);
          t = setTimeout(function () { q = input.value.trim().toLowerCase(); page = 0; draw(); }, 130);
        });
      }
      $$("#doc-rel-filters button").forEach(function (b) {
        b.addEventListener("click", function () {
          rel = b.dataset.rel; page = 0;
          $$("#doc-rel-filters button").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
          draw();
        });
      });
      var psel = $("#doc-prov");
      if (psel && docs.length) {
        var counts = releaseCounts(docs);
        var provs = [["DND", "National Defence"], ["TRANSPORT", "Transport"],
                     ["NRC", "National Research Council"], ["RCMP", "RCMP"]];
        // Hide a group with no documents rather than offering a filter that
        // can only ever return nothing.
        psel.insertAdjacentHTML("beforeend", provs.filter(function (p) {
          return counts[p[0]] > 0;
        }).map(function (p) {
          return '<option value="' + p[0] + '">' + p[1] + " (" + counts[p[0]] + ")</option>";
        }).join(""));
        psel.addEventListener("change", function () { prov = psel.value; page = 0; draw(); });
      }
      var relBody = $("#rel-body");
      if (relBody && releases.length) {
        relBody.innerHTML = releases.map(function (r) {
          var n = docs.filter(function (d) { return d.release === r.n; }).length;
          return '<details open><summary><span class="doc-id">Release ' + esc(r.n) + " &middot; " + esc(r.date) +
            "</span><br>" + esc(r.title) + ' <span class="chip">' + n + (n === 1 ? " record" : " records") + "</span></summary>" +
            '<p class="prose-note">' + esc(r.blurb) + "</p></details>";
        }).join("");
      }
      draw();
    }
  }

  /* --------------------------------------------------------- LAC archive */
  function renderArchive() {
    var body = $("#arc-body");
    if (!body) return;
    var rows = [], q = "", grp = "all", sortKey = "doc_date", sortDir = 1, page = 0, PER = 25;
    fetchJSON("data/lac.json").then(function (r) {
      // Precompute the search haystack once. Building it inside matches() meant
      // six field joins and a toLowerCase for each of 1,510 rows on every
      // keystroke of the search box.
      r.forEach(function (x) {
        x._hay = [x.doc_title, x.record_group, x.doc_date, x.sighting_date, x.location, x.rid]
          .join(" ").toLowerCase();
      });
      rows = r;
      wire();
    }).catch(function (e) {
      body.innerHTML = '<div class="error-note">Could not load the index: ' + e.message + "</div>";
    });

    function grpOf(r) { return r.record_group; }
    function dateVal(r) {
      var m = /(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(r.doc_date || "");
      if (!m) return -1;
      return Date.UTC(+m[3], +m[1] - 1, +m[2]);
    }

    function matches(r) {
      if (grp !== "all" && grpOf(r) !== grp) return false;
      if (!q) return true;
      return r._hay.indexOf(q) >= 0;
    }

    function draw() {
      var list = rows.filter(matches);
      list.sort(function (a, b) {
        var x, y;
        if (sortKey === "doc_date") { x = dateVal(a); y = dateVal(b); }
        else if (sortKey === "record_group") { return sortDir * String(a.record_group || "").localeCompare(String(b.record_group || "")); }
        else { x = a[sortKey] || ""; y = b[sortKey] || ""; return sortDir * String(x).localeCompare(String(y)); }
        return sortDir * (x - y);
      });
      var pages = Math.max(1, Math.ceil(list.length / PER));
      page = Math.min(page, pages - 1);
      var slice = list.slice(page * PER, page * PER + PER);
      var note = $("#arc-count");
      if (note) note.textContent = "Showing " + (slice.length ? page * PER + 1 : 0) + "-" +
        Math.min((page + 1) * PER, list.length) + " of " + list.length + " indexed descriptions";
      body.innerHTML = slice.map(function (r) {
        var loc = /^\[/.test(r.location) ? '<span class="none">not cited</span>' : esc(r.location);
        var sd = /^\[/.test(r.sighting_date) ? '<span class="none">not cited</span>' : esc(r.sighting_date);
        var dd = /^\[/.test(r.doc_date) ? '<span class="none">not cited</span>' : esc(r.doc_date);
        return "<tr>" +
          '<td><span class="rid">' + esc(r.rid) + "</span></td>" +
          "<td>" + esc(r.doc_title) + "</td>" +
          "<td>" + esc(r.record_group) + '</td><td>' + dd + "</td><td>" + sd + "</td><td>" + loc + "</td>" +
          '<td><a href="' + esc(r.url) + '" target="_blank" rel="noopener">open record</a></td></tr>';
      }).join("") || '<tr><td colspan="7" class="none">Nothing matches that search.</td></tr>';

      pager($("#arc-pager"), page, pages, function (p) { page = p; draw(); });
    }

    function wire() {
      var sel = $("#arc-group");
      if (sel) {
        var tally = Object.create(null);
        rows.forEach(function (r) {
          if (r.record_group) tally[r.record_group] = (tally[r.record_group] || 0) + 1;
        });
        sel.insertAdjacentHTML("beforeend", Object.keys(tally).sort().map(function (g) {
          return '<option value="' + esc(g) + '">' + esc(g) + " (" + tally[g] + ")</option>";
        }).join(""));
        sel.addEventListener("change", function () { grp = sel.value; page = 0; draw(); });
      }
      var input = $("#arc-search");
      if (input) {
        var t;
        input.addEventListener("input", function () {
          clearTimeout(t);
          t = setTimeout(function () { q = input.value.trim().toLowerCase(); page = 0; draw(); }, 130);
        });
      }
      $$("#arc-table th button").forEach(function (b) {
        b.addEventListener("click", function () {
          var k = b.dataset.sort;
          sortDir = (k === sortKey) ? -sortDir : 1;
          sortKey = k;
          $$("#arc-table th button").forEach(function (x) { x.removeAttribute("aria-sort"); });
          b.setAttribute("aria-sort", sortDir > 0 ? "ascending" : "descending");
          draw();
        });
      });
      draw();
    }
  }

  /* --------------------------------------------------------------- cases */
  // The chip wording used to be a second table here, and it had already drifted
  // from map.js's: the map said "Mainstream reporting, named sources" and this
  // said "Mainstream reporting". Both now read Aurora.CONF in core.js.
  // One card, two call sites: the full index and the five-case teaser on the
  // overview page. Keeping a single renderer is the point — the teaser used to
  // be a hand-typed second copy that drifted.
  function caseCard(c) {
    var cl = Aurora.conf(c.conf);
    return '<article class="card conf-' + (Aurora.CONF[c.conf] ? c.conf : "partial") +
      '" data-case-card="' + esc(c.slug) + '" id="' + esc(c.slug) + '">' +
      '<div class="chips card-chips"><span class="chip ' + cl.chip + '">' + cl.short + "</span>" +
        '<span class="chip">' + esc(c.display) + "</span>" +
        (c.prov ? '<span class="chip">' + esc(c.prov) + "</span>" : "") +
        (c.tag ? '<span class="chip">' + esc(c.tag) + "</span>" : "") + "</div>" +
      "<h3>" + esc(c.title) + "</h3><p>" + esc(c.summary) + "</p>" +
      '<div class="meta"><a class="btn" href="case-' + esc(c.slug) + '.html">Open case file</a></div></article>';
  }

  function sortCases(cases) {
    var order = { primary: 0, reported: 1, partial: 2 };
    return cases.slice().sort(function (a, b) {
      var d = (order[a.conf] || 0) - (order[b.conf] || 0);
      if (d) return d;
      if (a.date === b.date) return a.slug < b.slug ? -1 : a.slug > b.slug ? 1 : 0;
      return a.date < b.date ? 1 : -1;  // newest first
    });
  }

  function renderCases() {
    var host = $("#case-grid");
    if (!host) return;
    fetchJSON("data/cases.json").then(function (cases) {
      host.innerHTML = sortCases(cases).map(caseCard).join("");
    }).catch(function (e) {
      host.innerHTML = '<div class="error-note">Could not load case files: ' + e.message + "</div>";
    });
  }

  /* The overview page shows the archival-grade cases only. The other thirteen
     are one click away, and repeating all eighteen made the front page a
     second copy of case.html. */
  function renderFeaturedCases() {
    var host = $("#case-featured");
    if (!host) return;
    fetchJSON("data/cases.json").then(function (cases) {
      var best = sortCases(cases).filter(function (c) { return c.conf === "primary"; });
      host.innerHTML = best.map(caseCard).join("");
    }).catch(function (e) {
      host.innerHTML = '<div class="error-note">Could not load case files: ' + e.message + "</div>";
    });
  }

  /* --------------------------------------------------------- release teaser
     A row per tranche, not a card grid. Five cards in a three-up grid leaves
     one card stranded on its own row, and the blurb lengths are uneven enough
     that the cards came out mostly empty. Rows also read as the index they
     are. The per-tranche date is deliberately not shown here: every entry
     carries the same one, because it is the date AURORA indexed them, not the
     date the material was released. releases.html keeps it. */
  function renderTranches() {
    var host = $("#tranche-grid");
    if (!host) return;
    fetchJSON("data/releases.json").then(function (r) {
      host.innerHTML = '<ol class="tranches">' + r.releases.map(function (t) {
        return '<li class="tranche">' +
          '<div class="tranche-n">' + esc(t.n) + "</div>" +
          '<div class="tranche-body"><h3>' + esc(t.title) + "</h3>" +
            "<p>" + esc(t.blurb) + "</p></div>" +
          '<a class="btn tranche-go" href="releases.html#tranches">Open<span class="sr-only"> tranche ' +
            esc(t.n) + ", " + esc(t.title) + "</span> &rarr;</a></li>";
      }).join("") + "</ol>";
    }).catch(function (e) {
      host.innerHTML = '<div class="error-note">Could not load the release index: ' + e.message + "</div>";
    });
  }

  /* --------------------------------------------------------------- media */
  function renderMedia() {
    var host = $("#media-grid");
    if (!host) return;
    fetchJSON("data/media.json")
      .then(function (media) {
        return fetchJSON("data/cases.json").then(
          function (cases) { return { media: media, cases: cases }; },
          // media.json is enough to render the grid; a missing cases.json
          // should only cost the "linked case" chips.
          function () { return { media: media, cases: [] }; });
      })
      .then(function (res) {
        var media = res.media, cases = res.cases;
        var byId = {};
        cases.forEach(function (c) { (c.media || []).forEach(function (m) { (byId[m] = byId[m] || []).push(c); }); });
        // Every embed is click-to-load. Building the <iframe> up front would
        // fire a request to YouTube and CBC on page load for each card, which
        // this site has no reason to do.
        host.innerHTML = media.map(function (m) {
          var label = m.kind === "yt" ? "YouTube &middot; click to load" : "CBC player &middot; click to load";
          var frame = '<span class="pb" aria-hidden="true"></span><span class="pm">' + label + "</span>" +
            '<a class="poster-link" href="' + esc(m.src) + '" target="_blank" rel="noopener" aria-label="Play: ' + esc(m.title) + '"></a>';
          var linked = (byId[m.id] || []).map(function (c) {
            return '<span class="chip chip-a">' + esc(c.title) + "</span>";
          }).join("");
          return '<article class="card" id="' + esc(m.id) + '">' +
            '<div class="card-media poster">' + frame + "</div>" +
            "<h3>" + esc(m.title) + "</h3>" +
            '<p class="card-sub">' + esc(m.publisher) + " &middot; " + esc(m.date) + (m.len && m.len !== "long form" ? " &middot; " + esc(m.len) : "") + "</p>" +
            "<p>" + esc(m.pos) + "</p>" +
            (linked ? '<div class="chips meta">' + linked + "</div>" : "") + "</article>";
        }).join("");
        // Swap the poster for the real player only on an explicit click.
        $$(".card-media.poster", host).forEach(function (box) {
          var a = box.querySelector("a");
          if (!a) return;
          a.addEventListener("click", function (e) {
            e.preventDefault();
            var src = a.getAttribute("href") + (a.getAttribute("href").indexOf("?") === -1 ? "?" : "&") +
              "autoplay=1&rel=0&modestbranding=1";
            var ifr = document.createElement("iframe");
            ifr.src = src;
            ifr.title = a.getAttribute("aria-label") || "video";
            ifr.allow = "autoplay; encrypted-media; picture-in-picture";
            ifr.setAttribute("allowfullscreen", "");
            box.innerHTML = "";
            box.appendChild(ifr);
          });
        });
      })
      .catch(function (e) {
        host.innerHTML = '<div class="error-note">Could not load the media index: ' + e.message + "</div>";
      });
  }

  /* ---------------------------------------------------------- podcasts */
  // media.html's two podcast cards were hand-typed into the markup while
  // data/podcasts.json -- which data.html and llms.txt both advertise as the
  // machine-readable source -- carried nothing but two titles and two URLs. The
  // prose lived in one place and the data in another; now the data is the source
  // and this renders it.
  function renderPodcasts() {
    var host = $("#podcast-grid");
    if (!host) return;
    fetchJSON("data/podcasts.json")
      .then(function (rows) {
        host.innerHTML = rows.map(function (p) {
          return '<article class="card">' +
            "<h3>" + esc(p.title) + "</h3>" +
            '<p class="card-sub">Published ' + esc(p.published) + " &middot; " +
              esc(p.len) + " &middot; " + esc(p.size) + " MP3</p>" +
            "<p>" + esc(p.note) + "</p>" +
            '<div class="chips card-chips"><span class="chip chip-a">' + esc(p.org) + "</span>" +
              (p.case ? '<span class="chip"><a href="case-' + esc(p.case) + '.html">Case file</a></span>' : "") +
            "</div>" +
            '<div class="meta"><a class="btn btn-primary" href="' + esc(p.url) +
              '" target="_blank" rel="noopener">Listen or download</a></div></article>';
        }).join("");
      })
      .catch(function (e) {
        host.innerHTML = '<div class="error-note">Could not load the podcast list: ' + e.message + "</div>";
      });
  }

  /* ----------------------------------------------------------- endpoints */
  function renderEndpoints() {
    var host = $("#ep-list");
    if (!host) return;
    // Not every URL here answers an automated request. Two canada.ca paths
    // stall scripted clients while serving the same page to a browser, and
    // NUFORC 403s anything that is not a person. Saying so on the list beats
    // a claim that everything returned 200.
    var CAVEAT = {
      "www.canada.ca": "Serves browsers, stalls scripts. Open it in a tab.",
      "nuforc.org": "Blocks non-browser clients. Open it in a tab."
    };
    function caveatFor(url) {
      var m = /:\/\/([^/]+)/.exec(url || "");
      return m ? CAVEAT[m[1]] : null;
    }
    fetchJSON("data/endpoints.json").then(function (eps) {
      host.innerHTML = eps.map(function (e) {
        var cav = caveatFor(e.url);
        return "<li><span class=\"bullet\"></span><div>" +
          "<a href=\"" + esc(e.url) + "\" target=\"_blank\" rel=\"noopener\">" + esc(e.name) + "</a>" +
          ' <span class="chip">' + esc(e.org) + "</span>" +
          (cav ? ' <span class="chip chip-amb">' + esc(cav) + "</span>" : "") +
          '<div class="desc">' + esc(e.note) + "</div>" +
          "<div class=\"desc\"><code>" + esc(e.url) + "</code></div>" +
          (e.examples && e.examples.length
            ? '<div class="desc">Try: ' + e.examples.map(function (x) {
                return "<code>" + esc(x) + "</code>";
              }).join(" ") + "</div>"
            : "") +
          "</div></li>";
      }).join("");
    }).catch(function (e) {
      host.innerHTML = '<li><div class="error-note">Could not load endpoints: ' + e.message + "</div></li>";
    });
  }

  /* --------------------------------------------------------- CKAN search */
  /* Two things about this call that are not obvious from the code.
   *
   * 1. open.canada.ca sends `Access-Control-Allow-Origin:
   *    https://nosytlabs.github.io` and no other origin. The query therefore
   *    works on the deployed site and CANNOT work on localhost -- the browser
   *    blocks it and fetch rejects with "Failed to fetch", which is not a bug in
   *    this file. Verified: an Origin of http://127.0.0.1 gets no ACAO header
   *    at all, while https://nosytlabs.github.io gets exactly that. If the site
   *    ever moves to a custom domain this feature dies silently, and the fix is
   *    to get the new origin added to open.canada.ca's allowlist.
   *
   * 2. The catalogue's own identifier is a UUID and the API returns no page URL
   *    anywhere: on a live result `url` is null, `gc_catalogue_number` is an
   *    empty string and `program_page_url` is a pair of empty strings. This used
   *    to link straight to `d.name`, so every result rendered as a dead relative
   *    link to a UUID. The portal's dataset page is /data/en/dataset/<uuid>,
   *    which does resolve and lands on the dataset the API described.
   *
   * Also worth knowing when reading the results: this catalogue returns nothing
   * for UFO, UAP, "unidentified aerial" or CADORS. "aerial phenomenon" returns
   * one dataset, about coastal dynamics. That is the site's own thesis, and it
   * is checkable from the reader's own browser, which is the point of the form.
   */
  var CATALOGUE = "https://open.canada.ca/data/en/dataset/";
  function datasetUrl(d) {
    var id = d && (d.name || d.id);
    if (!id || !/^[0-9a-f-]{36}$/i.test(id)) return null;
    return CATALOGUE + id;
  }

  function wireCkan() {
    var form = $("#ckan-form");
    if (!form) return;
    var input = $("#ckan-q");
    var out = $("#ckan-out");
    // Two queries can be in flight at once and the slower one to *resolve* wins,
    // not the one submitted last, so a fast early reply can overwrite a slow
    // later one. Tag each request and ignore a reply that is no longer the
    // current one.
    var current = 0;
    var go = function () {
      var q = (input.value || "").trim() || "aerial phenomenon";
      var mine = ++current;
      out.innerHTML = '<p class="spinner">Querying open.canada.ca…</p>';
      var url = "https://open.canada.ca/data/api/3/action/package_search?rows=6&q=" + encodeURIComponent(q);
      fetch(url).then(function (r) {
        if (!r.ok) throw new Error("open.canada.ca → " + r.status);
        return r.json();
      }).then(function (j) {
        if (mine !== current) return;
        if (j.success !== true) throw new Error("the API answered success:false");
        var res = (j.result && j.result.results) || [];
        if (!res.length) {
          // Worth saying plainly: this is the site's own thesis, checkable.
          // Searches for UFO, UAP, unidentified aerial and CADORS all return
          // nothing from this catalogue, and "aerial phenomenon" returns one.
          out.innerHTML = '<p class="note">Nothing in the open catalogue matched “' + esc(q) +
            '”. That is not an outage. Searches for UFO, UAP, unidentified aerial phenomena and CADORS ' +
            'all return zero datasets from this catalogue, and the Sky Canada Project recommends naming ' +
            'a department responsible for UAP data precisely because there is none to find.</p>';
          return;
        }
        out.innerHTML = '<p class="search-note">' +
          ((j.result && j.result.count) || res.length) + " datasets in the Government of Canada open catalogue</p>" +
          '<ul class="linklist">' + res.map(function (d) {
            var href = datasetUrl(d);
            var title = esc(d.title || d.name);
            return '<li><span class="bullet"></span><div>' +
              (href ? '<a href="' + esc(href) + '" target="_blank" rel="noopener">' + title + "</a>"
                    : "<b>" + title + "</b>") +
              '<div class="desc">' + esc((d.notes || "").replace(/<[^>]+>/g, "").slice(0, 220)) +
              "</div></div></li>";
          }).join("") + "</ul>";
      }).catch(function (e) {
        if (mine !== current) return;
        if (window.console && console.warn) console.warn("AURORA CKAN search", e);
        out.innerHTML = '<p class="note">That live query did not come back (' + esc(e.message) +
          "). The endpoint is worth trying directly: <code>open.canada.ca/data/api/3/action/package_search</code>.";
      });
    };
    form.addEventListener("submit", function (e) { e.preventDefault(); go(); });
    // Intentionally not run on load: a page view should not query a
    // third-party API the visitor did not ask about.
  }

  /* ------------------------------------------------------ survey series */
  /* The counts, percentages, run times and provincial splits all come from
     data/survey.json. They used to be typed into index.html as well, which is
     how the JSON kept saying "the largest edition yet" after the prose had
     already been corrected.

     Three things in here are still prose rather than data, and are marked as
     such below: the "about 5%" derived from disc_reports, the 35-year baseline,
     and the one card that quotes the CADORS ratio instead of a report count.
     If any of them moves, it moves here. */
  function renderSurvey() {
    var cards = $("#survey-cards"), stats = $("#survey-stats");
    if (!cards) return;
    fetchJSON("data/survey.json").then(function (d) {
      var years = d.years || [], meta = d.meta || {};
      var cur = years[years.length - 1] || {};
      var peak = years.reduce(function (a, y) { return !a || y.reports > a.reports ? y : a; }, null);
      var prior = years[years.length - 2] || {};
      var third = years[years.length - 3] || {};
      var fmt = function (n) { return Number(n).toLocaleString("en-CA"); };
      var unexplainedCount = cur.unexplained_pct
        ? Math.round(cur.reports * cur.unexplained_pct / 100) : null;

      cards.innerHTML = [
        ["Reports, " + cur.year, fmt(cur.reports),
         "Roughly one every eight hours, up from " + fmt(prior.reports) + " in " + prior.year +
         " and " + fmt(third.reports) + " in " + third.year + ". The biggest year since 2020" +
         (peak ? " \u2014 and the record is " + fmt(peak.reports) + " in " + peak.year + "." : ".")],
        ["Left unexplained", cur.unexplained_pct + "%",
         fmt(unexplainedCount) + " of " + fmt(cur.reports) + " reports. Averaged over the survey's " +
         "preceding " + (cur.long_run_years || 35) + " years the unexplained share is " +
         cur.long_run_unexplained_pct +
         "%, so this is among the lowest readings it has ever posted."],
        ["Insufficient evidence", cur.insufficient_pct + "%",
         "The largest single bucket. " + cur.probable_pct + "% came back probable and " +
         cur.explained_pct + "% explained. The survey is explicit that a report of \u201cunknown\u201d " +
         "does not imply alien visitation."],
        ["Pilot-reported, all of CADORS", "0.08%",
         "The Sky Canada Project report's figure for the share of everything pilots file to Transport " +
         "Canada's CADORS database that could be considered UAPs. It is a ratio, not a count: the report " +
         "gives no number of UAP incidents in CADORS."]
      ].map(function (c) {
        return '<article class="card"><div class="readout-label">' + esc(c[0]) + "</div>" +
          '<div class="figure readout-num">' + esc(c[1]) + "</div>" +
          '<p class="figure-cap">' + c[2] + "</p></article>";
      }).join("");

      var prov = cur.by_province || {};
      stats.innerHTML = [
        [cur.nocturnal_pct + "%", "were nocturnal lights \u2014 the single largest category of description, above anything conventionally called a disc or a craft."],
        [String(cur.disc_reports), "reports described a \u201cdisc\u201d, about 5% of the year. The most common single shape was a " + esc(cur.top_shape) + ", at " + cur.top_shape_pct + "%."],
        [cur.avg_duration_min + " min", "average reported duration, up from " + (cur.prev_avg_duration_min || {})["2024"] + " minutes in 2024 and " + (cur.prev_avg_duration_min || {})["2023"] + " in 2023."],
        [[prov.ON, prov.QC, prov.BC].join(" / "), "reports from Ontario, Quebec and British Columbia \u2014 the three provinces that account for most of the Canadian total."]
      ].map(function (s) {
        return '<div class="stat"><b>' + s[0] + "</b><span>" + s[1] + "</span></div>";
      }).join("");

      // the series itself, for anyone who wants the numbers rather than the story
      if (meta.series_url) {
        var foot = document.createElement("p");
        foot.className = "prose";
        foot.style.marginTop = "18px";
        foot.innerHTML = "The full " + esc(cur.year) + " edition is a " +
          '<a href="' + esc(meta.series_url) + '" target="_blank" rel="noopener">PDF from Ufology Research</a>' +
          ". The series has run since " + esc(meta.since) + " and has catalogued more than " +
          fmt(meta.catalogued_total) + " reports.";
        cards.parentNode.insertBefore(foot, stats);
      }
    }).catch(function (e) {
      cards.innerHTML = '<div class="error-note">Could not load the survey series: ' + e.message +
        ". The figures are in <code>data/survey.json</code>.</div>";
    });
  }

  /* ------------------------------------------------------------ paging */
  /* One pager for both long lists. There were two copies of this, identical
     except for the element id and whether it scrolls the list back into view --
     and one of them elided at pages > 9 while the other did not, so the release
     list and the archive list started collapsing their page numbers at different
     lengths. One threshold now.
     window: how many page numbers either side of the current one to show. */
  function pager(el, page, pages, onPick) {
    if (!el) return;
    if (pages <= 1) { el.innerHTML = ""; return; }
    var h = '<button class="chip" data-p="' + (page - 1) + '"' +
            (page === 0 ? " disabled" : "") + ">Prev</button>";
    for (var i = 0; i < pages; i++) {
      if (pages > 9 && Math.abs(i - page) > 1 && i !== 0 && i !== pages - 1) {
        if (Math.abs(i - page) === 2) h += '<span class="chip">\u2026</span>';
        continue;
      }
      h += '<button class="chip' + (i === page ? " chip-a" : "") + '" data-p="' + i + '">' +
           (i + 1) + "</button>";
    }
    h += '<button class="chip" data-p="' + (page + 1) + '"' +
         (page === pages - 1 ? " disabled" : "") + ">Next</button>";
    el.innerHTML = h;
    $$("button", el).forEach(function (b) {
      b.addEventListener("click", function () { onPick(parseInt(b.dataset.p, 10)); });
    });
  }

  /* ------------------------------------------------------------ timeline */
  function renderTimeline() {
    var host = $("#tl");
    if (!host) return;
    fetchJSON("data/timeline.json").then(function (rows) {
      host.innerHTML = rows.map(function (r) {
        var isNow = r.now === true;
        return '<li class="' + (isNow ? "now" : "") + '"><span class="yr">' + esc(r.year) + "</span>" +
          "<h3>" + esc(r.title) + "</h3><p>" + esc(r.body) + "</p></li>";
      }).join("");
    }).catch(function (e) {
      host.innerHTML = '<li><p class="error-note">Could not load the timeline: ' + e.message + "</p></li>";
    });
  }

  ready(function () {
    renderDocs(); renderArchive(); renderCases(); renderFeaturedCases();
    renderTranches(); renderMedia(); renderPodcasts();
    renderEndpoints(); wireCkan(); renderTimeline(); renderSurvey();
  });
})();
