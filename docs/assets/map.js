/* AURORA — map (Leaflet, vendored) */
(function () {
  "use strict";

  // Keyless OSM tiles. The dark look comes from a CSS filter on the tile pane
  // (see base.css), which also means no API key can expire and break the map.
  var TILES = [
    { name: "OpenStreetMap", url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      sub: "", max: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }
  ];

  var CONF = {
    primary:  { label: "Archival or official record", color: "#22d3ee", r: 8 },
    reported: { label: "Mainstream reporting, named sources", color: "#4ade80", r: 7 },
    partial:  { label: "Thin sourcing — verify before citing", color: "#f59e0b", r: 6 }
  };

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

  ready(function () {
    var el = document.getElementById("map");
    if (!el || typeof L === "undefined") return;

    Promise.all([fetchJSON("data/canada.json"), fetchJSON("data/cases.json")])
      .then(function (res) {
        var geo = res[0], cases = res[1];
        var map = L.map(el, {
          center: [57, -100],
          zoom: 2.6,
          zoomSnap: 0.25,
          minZoom: 2,
          maxZoom: 11,
          zoomControl: false,
          attributionControl: true,
          worldCopyJump: true,
          maxBounds: [[8, -160], [86, -20]],
          maxBoundsViscosity: 0.8
        });
        L.control.zoom({ position: "topright" }).addTo(map);

        TILES.forEach(function (t) {
          L.tileLayer(t.url, {
            maxZoom: t.max,
            attribution: t.attribution,
            crossOrigin: true
          }).addTo(map);
        });

        function styleFor(provName) {
          var isTerr = /nunavut|northwest|yukon|quebec|newfoundland|labrador/i.test(provName || "");
          return {
            color: isTerr ? "rgba(103,232,249,0.72)" : "rgba(186,205,232,0.62)",
            weight: isTerr ? 1.1 : 1,
            opacity: 1,
            fillColor: isTerr ? "rgba(34,211,238,0.07)" : "rgba(129,140,248,0.08)",
            fillOpacity: 1,
            dashArray: isTerr ? "3 4" : null,
            lineJoin: "round"
          };
        }

        var provinces = L.geoJSON(geo, {
          style: function (f) { return styleFor(f.properties.name); },
          onEachFeature: function (f, layer) {
            var p = f.properties;
            if (p && p.name) {
              layer.bindTooltip(p.name + (p.abbr ? " (" + p.abbr + ")" : ""), { sticky: true, className: "prov-tip" });
            }
          }
        }).addTo(map);

        function halo(lat, lng, color) {
          return L.circleMarker([lat, lng], {
            radius: 16, color: color, weight: 1, opacity: 0.3, fillOpacity: 0.06, interactive: false
          }).addTo(map);
        }

        window.__auroraMap = map;
        var markers = [];
        cases.forEach(function (c) {
          var cfg = CONF[c.conf] || CONF.partial;
          halo(c.lat, c.lon, cfg.color);
          var m = L.circleMarker([c.lat, c.lon], {
            radius: cfg.r, color: "#04060c", weight: 2, fillColor: cfg.color, fillOpacity: 0.95
          }).addTo(map);
          m.caseSlug = c.slug;
          m.conf = c.conf;
          var html = '<h4>' + c.title + (c.prov ? ", " + c.prov : "") + '</h4>' +
            '<p class="pp">' + c.display + " &middot; " + (c.region || "") + "</p>" +
            "<p>" + c.summary + "</p>" +
            '<p class="pp" style="margin:0"><span style="color:' + cfg.color + '">' + cfg.label + "</span></p>";
          m.bindPopup(html, { maxWidth: 320 });
          m.on("click", function () { go(c.slug); });
          m.on("keypress", function () { go(c.slug); });
          markers.push(m);
        });

        // side list, kept in sync with markers
        var list = document.getElementById("map-list");
        if (list) {
          cases.slice().sort(function (a, b) { return a.date < b.date ? -1 : 1; })
            .forEach(function (c) {
              var li = document.createElement("li");
              var b = document.createElement("button");
              b.type = "button";
              b.setAttribute("aria-selected", "false");
              b.dataset.slug = c.slug;
              b.innerHTML = '<span class="yr">' + c.date.slice(0, 4) + '</span><span>' +
                c.title + (c.prov ? " <span style='color:var(--faint)'>" + c.prov + "</span>" : "") + "</span>";
              b.addEventListener("click", function () { go(c.slug); });
              li.appendChild(b);
              list.appendChild(li);
            });
        }

        function go(slug) {
          if (location.pathname.indexOf("map.html") === -1) {
            location.href = "case-" + slug + ".html";
            return;
          }
          select(slug, true);
        }

        function select(slug, fromList) {
          var c = cases.filter(function (x) { return x.slug === slug; })[0];
          if (!c) return;
          if (!fromList) {
            map.setView([c.lat, c.lon], Math.max(map.getZoom(), 5), { animate: true });
            var b = list && list.querySelector('button[data-slug="' + slug + '"]');
            if (b && b.scrollIntoView) b.scrollIntoView({ block: "nearest" });
          }
          if (list) {
            list.querySelectorAll("button").forEach(function (x) {
              x.setAttribute("aria-selected", String(x.dataset.slug === slug));
            });
          }
          var target = markers.filter(function (m) { return m.caseSlug === slug; })[0];
          if (target) setTimeout(function () { target.openPopup(); }, 320);
          // reflect the choice in the URL without a jump
          if (history.replaceState) {
            history.replaceState(null, "", "#" + slug);
          }
          var card = document.querySelector('[data-case-card="' + slug + '"]');
          if (card && !fromList) {
            card.scrollIntoView({ block: "center", behavior: "smooth" });
            card.classList.add("is-open");
          }
          var jump = document.getElementById("open-" + slug);
          if (jump) jump.click();
        }

        // fitBounds last, and never call setMaxBounds afterwards: it re-fits the
        // view to the padded bounds and zooms the whole of Canada out of frame.
        // Leaflet caches the container size, so a fitBounds issued in the same
        // tick as init picks a zoom for a zero-height box. Redo it after a frame.
        var bounds = provinces.getBounds();
        function fit() {
          map.invalidateSize();
          if (window.matchMedia("(min-width: 761px)").matches) {
            map.fitBounds(bounds, { padding: [18, 18], maxZoom: 5 });
          } else {
            map.setView(bounds.getCenter(), 3);
          }
        }
        // A frame callback is not guaranteed to run (headless capture, virtual
        // clocks, some embedded webviews), so drive the fit from a timer too.
        requestAnimationFrame(function () { requestAnimationFrame(fit); });
        setTimeout(fit, 250);
        window.addEventListener("resize", function () { clearTimeout(window.__auroraFitT); window.__auroraFitT = setTimeout(fit, 180); });
        // no setMaxBounds here: it re-fits the view to the padded bounds and
        // zooms Canada out of frame. The generous maxBounds in the map options
        // is enough to keep the user from panning into the Pacific.

        var legend = document.getElementById("map-legend");
        if (legend) {
          Object.keys(CONF).forEach(function (k) {
            var li = document.createElement("li");
            li.innerHTML = '<span class="swatch" style="background:' + CONF[k].color + '"></span>' + CONF[k].label;
            legend.appendChild(li);
          });
        }
      })
      .catch(function (e) {
        var n = document.getElementById("map-note");
        if (n) n.innerHTML = '<div class="error-note">Map data could not load: ' + e.message +
          ". The case list below carries the same information." + "</div>";
      });
  });
})();
