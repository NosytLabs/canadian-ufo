/* AURORA — shared behaviour: nav, accordions, data renderers */
(function () {
  "use strict";

  var A = window.Aurora;
  var $ = A.$, $$ = A.$$, ready = A.ready, fetchJSON = A.fetchJSON, esc = A.esc;
  var narrow = A.narrow, singleColumn = A.singleColumn;

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

    // FAQ accordions: all open by default for crawlers, first one closed on narrow screens
    $$(".qa details").forEach(function (d, i) {
      if (!singleColumn()) d.open = true;
      else d.open = i === 0;
    });
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
      var pag = $("#doc-pager");
      if (pag) {
        if (pages <= 1) { pag.innerHTML = ""; return; }
        var h = '<button class="chip" data-p="' + (page - 1) + '"' + (page === 0 ? " disabled" : "") + ">Prev</button>";
        for (var i = 0; i < pages; i++) {
          if (pages > 9 && Math.abs(i - page) > 1 && i !== 0 && i !== pages - 1) {
            if (Math.abs(i - page) === 2) h += '<span class="chip">…</span>';
            continue;
          }
          h += '<button class="chip' + (i === page ? " chip-a" : "") + '" data-p="' + i + '">' + (i + 1) + "</button>";
        }
        h += '<button class="chip" data-p="' + (page + 1) + '"' + (page === pages - 1 ? " disabled" : "") + ">Next</button>";
        pag.innerHTML = h;
        $$("#doc-pager button").forEach(function (b) {
          b.addEventListener("click", function () { page = parseInt(b.dataset.p, 10); draw(); host.scrollIntoView({ block: "nearest" }); });
        });
      }
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
            '<p style="color:var(--muted);margin:10px 0 0;max-width:72ch">' + esc(r.blurb) + "</p></details>";
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
    fetchJSON("data/lac.json").then(function (r) { rows = r; wire(); })
      .catch(function (e) { body.innerHTML = '<div class="error-note">Could not load the index: ' + e.message + "</div>"; });

    function grpOf(r) { return r.record_group; }
    function dateVal(r) {
      var m = /(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(r.doc_date || "");
      if (!m) return -1;
      return Date.UTC(+m[3], +m[1] - 1, +m[2]);
    }

    function matches(r) {
      if (grp !== "all" && grpOf(r) !== grp) return false;
      if (!q) return true;
      return [r.doc_title, r.record_group, r.doc_date, r.sighting_date, r.location, r.rid]
        .join(" ").toLowerCase().indexOf(q) >= 0;
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

      var pag = $("#arc-pager");
      if (pag) {
        if (pages <= 1) { pag.innerHTML = ""; return; }
        var h = '<button class="chip" data-p="' + (page - 1) + '"' + (page === 0 ? " disabled" : "") + ">Prev</button>";
        for (var i = 0; i < pages; i++) {
          if (pages > 10 && Math.abs(i - page) > 1 && i !== 0 && i !== pages - 1) {
            if (Math.abs(i - page) === 2) h += '<span class="chip">…</span>';
            continue;
          }
          h += '<button class="chip' + (i === page ? " chip-a" : "") + '" data-p="' + i + '">' + (i + 1) + "</button>";
        }
        h += '<button class="chip" data-p="' + (page + 1) + '"' + (page === pages - 1 ? " disabled" : "") + ">Next</button>";
        pag.innerHTML = h;
        $$("#arc-pager button").forEach(function (b) {
          b.addEventListener("click", function () { page = parseInt(b.dataset.p, 10); draw(); });
        });
      }
    }

    function wire() {
      var groups = {};
      rows.forEach(function (r) { groups[r.record_group] = 1; });
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
  function renderCases() {
    var host = $("#case-grid");
    if (!host) return;
    fetchJSON("data/cases.json").then(function (cases) {
      var order = { primary: 0, reported: 1, partial: 2 };
      var sorted = cases.slice().sort(function (a, b) {
        var d = (order[a.conf] || 0) - (order[b.conf] || 0);
        if (d) return d;
        if (a.date === b.date) return a.slug < b.slug ? -1 : a.slug > b.slug ? 1 : 0;
        return a.date < b.date ? 1 : -1;  // newest first
      });
      var confLabel = {
        primary: ["chip-a", "Archival or official record"],
        reported: ["chip", "Mainstream reporting"],
        partial: ["chip-amb", "Thin sourcing"]
      };
      host.innerHTML = sorted.map(function (c) {
        var cl = confLabel[c.conf] || confLabel.partial;
        return '<article class="card" data-case-card="' + esc(c.slug) + '" id="' + esc(c.slug) + '">' +
          '<div class="chips" style="margin-bottom:12px"><span class="chip ' + cl[0] + '">' + cl[1] + "</span>" +
            '<span class="chip">' + esc(c.display) + "</span>" +
            (c.prov ? '<span class="chip">' + esc(c.prov) + "</span>" : "") +
            (c.tag ? '<span class="chip">' + esc(c.tag) + "</span>" : "") + "</div>" +
          "<h3>" + esc(c.title) + "</h3><p>" + esc(c.summary) + "</p>" +
          '<div class="meta"><a class="btn" href="case-' + esc(c.slug) + '.html">Open case file</a></div></article>';
      }).join("");
    }).catch(function (e) {
      host.innerHTML = '<div class="error-note">Could not load case files: ' + e.message + "</div>";
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
            '<p class="meta" style="color:var(--muted);font-size:12.5px">' + esc(m.publisher) + " &middot; " + esc(m.date) + (m.len && m.len !== "long form" ? " &middot; " + esc(m.len) : "") + "</p>" +
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

  /* ----------------------------------------------------------- endpoints */
  function renderEndpoints() {
    var host = $("#ep-list");
    if (!host) return;
    fetchJSON("data/endpoints.json").then(function (eps) {
      host.innerHTML = eps.map(function (e) {
        return "<li><span class=\"bullet\"></span><div>" +
          "<a href=\"" + esc(e.url) + "\" target=\"_blank\" rel=\"noopener\">" + esc(e.name) + "</a>" +
          ' <span class="chip">' + esc(e.org) + "</span>" +
          '<div class="desc">' + esc(e.note) + "</div>" +
          "<div class=\"desc\"><code>" + esc(e.url) + "</code></div>" +
          "</div></li>";
      }).join("");
    }).catch(function (e) {
      host.innerHTML = '<li><div class="error-note">Could not load endpoints: ' + e.message + "</div></li>";
    });
  }

  /* --------------------------------------------------------- CKAN search */
  function wireCkan() {
    var form = $("#ckan-form");
    if (!form) return;
    var input = $("#ckan-q");
    var out = $("#ckan-out");
    var go = function () {
      var q = (input.value || "UFO").trim();
      out.innerHTML = '<p class="spinner">Querying open.canada.ca…</p>';
      var url = "https://open.canada.ca/data/api/3/action/package_search?rows=6&q=" + encodeURIComponent(q);
      fetch(url).then(function (r) {
        if (!r.ok) throw new Error("open.canada.ca → " + r.status);
        return r.json();
      }).then(function (j) {
        var res = (j.result && j.result.results) || [];
        if (!res.length) {
          out.innerHTML = '<p style="color:var(--muted)">Nothing in the open catalogue matched “' + esc(q) +
            '”. A full-text miss is not proof that no such dataset exists, so this is a starting point rather than a result — try a broader term.</p>';
          return;
        }
        out.innerHTML = '<p style="color:var(--muted);margin:0 0 12px">' +
          ((j.result && j.result.count) || res.length) + " datasets in the Government of Canada open catalogue</p>" +
          '<ul class="linklist">' + res.map(function (d) {
            return '<li><span class="bullet"></span><div><a href="' + esc(d.name) + '" target="_blank" rel="noopener">' +
              esc(d.title || d.name) + '</a><div class="desc">' + esc((d.notes || "").replace(/<[^>]+>/g, "").slice(0, 220)) +
              "</div></div></li>";
          }).join("") + "</ul>";
      }).catch(function (e) {
        out.innerHTML = '<p style="color:var(--muted)">That live query failed (' + esc(e.message) +
          "). The endpoint is still worth trying directly: open.canada.ca CKAN API.</p>";
      });
    };
    form.addEventListener("submit", function (e) { e.preventDefault(); go(); });
    // Intentionally not run on load: a page view should not query a
    // third-party API the visitor did not ask about.
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
    renderDocs(); renderArchive(); renderCases(); renderMedia();
    renderEndpoints(); wireCkan(); renderTimeline();
  });
})();
