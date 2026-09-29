/* AURORA — shared behaviour: nav, clock, reveals, data renderers */
(function () {
  "use strict";

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  function fetchJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + " → " + r.status);
      return r.json();
    });
  }

  // Flag the document before first paint so the CSS can safely hide .reveal
  // elements; without JS they stay visible.
  document.documentElement.className += " js";

  var esc = function (s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  };

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
        if (e.target.tagName === "A" && window.innerWidth <= 760) {
          nav.classList.remove("open");
          t.setAttribute("aria-expanded", "false");
          t.textContent = "\u2630";
        }
      });
    }

    // Ottawa clock + date
    var clock = $("[data-clock]");
    if (clock) {
      var tick = function () {
        var now = new Date();
        clock.textContent = new Intl.DateTimeFormat("en-CA", {
          timeZone: "America/Toronto", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false
        }).format(now);
        var d = $("[data-date]");
        if (d) {
          d.textContent = new Intl.DateTimeFormat("en-CA", {
            timeZone: "America/Toronto", year: "numeric", month: "long", day: "numeric"
          }).format(now);
        }
      };
      tick();
      setInterval(tick, 1000);
    }

    observeReveals()

    // FAQ accordions: all open by default for crawlers, first one closed on narrow screens
    $$(".qa details").forEach(function (d, i) {
      if (window.innerWidth > 900) d.open = true;
      else d.open = i === 0;
    });
  });

  /* ------------------------------------------------------------- reveals */
  var revealObserver = null;
  function observeReveals(root) {
    if (!("IntersectionObserver" in window)) {
      $$(".reveal", root).forEach(function (el) { el.classList.add("in"); });
      return;
    }
    if (!revealObserver) {
      revealObserver = new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          if (e.isIntersecting) { e.target.classList.add("in"); revealObserver.unobserve(e.target); }
        });
      }, { rootMargin: "0px 0px -6% 0px", threshold: 0.04 });
    }
    $$(".reveal", root).forEach(function (el) { revealObserver.observe(el); });
  }
  // Safety net: nothing may stay invisible because an observer did not fire
  // (print, headless capture, odd viewports, an error above).
  setTimeout(function () {
    $$(".reveal").forEach(function (el) { el.classList.add("in"); });
  }, 2200);

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

    function byProvince() {
      // LAC index: one entry per record group with a count
      return fetchJSON("data/lac.json").then(function (recs) {
        var out = {};
        recs.forEach(function (r) { out[r.abbr] = (out[r.abbr] || 0) + 1; });
        return out;
      }).catch(function () { return null; });
    }

    function docProvince(d) {
      if (d.source.indexOf("National Defence") >= 0) return "DND";
      if (d.source.indexOf("Transport") >= 0 || d.source.indexOf("Coast Guard") >= 0) return "TRANSPORT";
      if (d.source.indexOf("National Research Council") >= 0) return "NRC";
      if (d.source.indexOf("Mounted Police") >= 0) return "RCMP";
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
      var href = d.file || d.external || "#";
      var media = d.thumb
        ? '<img src="' + d.thumb + '" alt="First page of ' + esc(d.title) + '" loading="lazy">'
        : '<span class="ph">' + esc(d.type) + "</span>";
      var title = esc(d.title) + (d.local ? " (opens the public mirror; a local copy is in the archive)" : "");
      return '<a class="doc" href="' + href + '" target="_blank" rel="noopener" title="' + title + '">' +
        '<span class="doc-thumb">' + media + "</span>" +
        '<span class="doc-body">' +
          '<span class="doc-id">' + esc(d.id) + "</span>" +
          "<h3>" + esc(d.title) + "</h3>" +
          "<p>" + esc(d.subtitle || "") + "</p>" +
          '<span class="doc-foot">' +
            '<span class="chip">' + esc(d.date) + "</span>" +
            (d.pages ? '<span class="chip">' + d.pages.toLocaleString("en-CA") + " pp</span>" : "") +
            '<span class="chip chip-a">' + esc(d.type) + "</span>" +
            '<span class="chip">Release ' + esc(d.release) + "</span>" +
            (d.local ? '<span class="chip chip-amb" title="Only resolves when the full local archive is served from the repository root">local copy</span>' : "") +
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
      byProvince().then(function (counts) {
        if (!psel || !counts) return;
        var provs = [["DND", "National Defence"], ["TRANSPORT", "Transport"], ["NRC", "National Research Council"], ["RCMP", "RCMP"]];
        psel.insertAdjacentHTML("beforeend", provs.map(function (p) {
          return '<option value="' + p[0] + '">' + p[1] + " (" + (counts[p[0]] || 0) + " indexed)</option>";
        }).join(""));
        psel.addEventListener("change", function () { prov = psel.value; page = 0; draw(); });
      });
      var relBody = $("#rel-body");
      if (relBody && releases.length) {
        relBody.innerHTML = releases.map(function (r) {
          var n = docs.filter(function (d) { return d.release === r.n; }).length;
          return '<details class="reveal" open><summary><span class="doc-id">Release ' + esc(r.n) + " &middot; " + esc(r.date) +
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
        else if (sortKey === "record_group") { x = a.record_group; y = b.record_group; return sortDir * x.localeCompare(y); }
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
        sel.insertAdjacentHTML("beforeend", Object.keys(groups).sort().map(function (g) {
          var n = rows.filter(function (r) { return r.record_group === g; }).length;
          return '<option value="' + esc(g) + '">' + esc(g) + " (" + n + ")</option>";
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
        return (order[a.conf] - order[b.conf]) || (a.date < b.date ? 1 : -1);
      });
      var confLabel = {
        primary: ["chip-a", "Archival or official record"],
        reported: ["chip", "Mainstream reporting"],
        partial: ["chip-amb", "Thin sourcing"]
      };
      host.innerHTML = sorted.map(function (c) {
        var cl = confLabel[c.conf] || confLabel.partial;
        return '<article class="card reveal" data-case-card="' + esc(c.slug) + '" id="' + esc(c.slug) + '">' +
          '<div class="chips" style="margin-bottom:12px"><span class="chip ' + cl[0] + '">' + cl[1] + "</span>" +
            '<span class="chip">' + esc(c.display) + "</span>" +
            (c.prov ? '<span class="chip">' + esc(c.prov) + "</span>" : "") +
            (c.tag ? '<span class="chip">' + esc(c.tag) + "</span>" : "") + "</div>" +
          "<h3>" + esc(c.title) + "</h3><p>" + esc(c.summary) + "</p>" +
          '<div class="meta"><a class="btn" href="case-' + esc(c.slug) + '.html">Open case file</a></div></article>';
      }).join("");
      var io = ("IntersectionObserver" in window) ? new IntersectionObserver(function (es) {
        es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
      }, { threshold: 0.06 }) : null;
      $$(".reveal", host).forEach(function (el) { io ? io.observe(el) : el.classList.add("in"); });
    }).catch(function (e) {
      host.innerHTML = '<div class="error-note">Could not load case files: ' + e.message + "</div>";
    });
  }

  /* --------------------------------------------------------------- media */
  function renderMedia() {
    var host = $("#media-grid");
    if (!host) return;
    Promise.all([fetchJSON("data/media.json"), fetchJSON("data/cases.json")])
      .then(function (res) {
        var media = res[0], cases = res[1];
        var byId = {};
        cases.forEach(function (c) { (c.media || []).forEach(function (m) { (byId[m] = byId[m] || []).push(c); }); });
        host.innerHTML = media.map(function (m) {
          var frame = m.kind === "yt"
            ? '<iframe src="' + m.src + '?rel=0&amp;modestbranding=1" title="' + esc(m.title) +
              '" loading="lazy" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
            : '<div class="poster"><span class="pb" aria-hidden="true"></span><span class="pm">CBC player &middot; click to load</span></div>' +
              '<a href="' + m.src + '" target="_blank" rel="noopener" style="position:absolute;inset:0" aria-label="Play: ' + esc(m.title) + '"></a>';
          var linked = (byId[m.id] || []).map(function (c) {
            return '<span class="chip chip-a">' + esc(c.title) + "</span>";
          }).join("");
          return '<article class="card reveal" id="' + esc(m.id) + '">' +
            '<div class="card-media' + (m.kind === "yt" ? "" : " poster") + '">' + frame + "</div>" +
            "<h3>" + esc(m.title) + "</h3>" +
            '<p class="meta" style="color:var(--muted);font-size:12.5px">' + esc(m.publisher) + " &middot; " + esc(m.date) + (m.len && m.len !== "long form" ? " &middot; " + esc(m.len) : "") + "</p>" +
            "<p>" + esc(m.pos) + "</p>" +
            (linked ? '<div class="chips meta">' + linked + "</div>" : "") + "</article>";
        }).join("");
        // CBC: swap poster for the real player on click
        $$(".card-media.poster", host).forEach(function (p) {
          var a = p.querySelector("a");
          if (!a) return;
          a.addEventListener("click", function (e) {
            e.preventDefault();
            var ifr = document.createElement("iframe");
            ifr.src = a.getAttribute("href");
            ifr.title = a.getAttribute("aria-label") || "video";
            ifr.allow = "autoplay; encrypted-media; picture-in-picture";
            ifr.setAttribute("allowfullscreen", "");
            p.innerHTML = "";
            p.appendChild(ifr);
          });
        });
        observeReveals(host);
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
      fetch(url).then(function (r) { return r.json(); }).then(function (j) {
        var res = (j.result && j.result.results) || [];
        if (!res.length) { out.innerHTML = '<p style="color:var(--muted)">No published datasets matched “' + esc(q) + '”. That is itself a finding: the catalogue has no UAP dataset.</p>'; return; }
        out.innerHTML = '<p style="color:var(--muted);margin:0 0 12px">' +
          ((j.result && j.result.count) || res.length) + " datasets in the Government of Canada open catalogue</p>" +
          '<ul class="linklist">' + res.map(function (d) {
            return '<li><span class="bullet"></span><div><a href="' + esc(d.name) + '" target="_blank" rel="noopener">' +
              esc(d.title || d.name) + '</a><div class="desc">' + esc((d.notes || "").replace(/<[^>]+>/g, "").slice(0, 220)) +
              "</div></div></li>";
          }).join("") + "</ul>";
      }).catch(function (e) {
        out.innerHTML = '<p style="color:var(--muted)">Live query failed (' + esc(e.message) +
          "). The endpoint is still worth trying from a browser: open.canada.ca CKAN API.</p>";
      });
    };
    form.addEventListener("submit", function (e) { e.preventDefault(); go(); });
    go();
  }

  /* ------------------------------------------------------------ timeline */
  function renderTimeline() {
    var host = $("#tl");
    if (!host) return;
    fetchJSON("data/timeline.json").then(function (rows) {
      host.innerHTML = rows.map(function (r) {
        var isNow = /2026/.test(r.year);
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
