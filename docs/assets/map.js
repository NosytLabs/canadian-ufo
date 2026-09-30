/* AURORA - map (MapLibre GL JS, vendored)

   The basemap is OpenFreeMap's dark style: a real vector map, no API key, no
   signup and no key that can expire. The previous version pulled OpenStreetMap
   raster tiles and inverted them with a CSS filter, which is how you get muddy
   labels and a map that looks like a bug.

   Province outlines come from Natural Resources Canada's CanVec, built into
   data/canada.json. Markers come from data/cases.json, coloured by sourcing
   grade. Nothing here needs a key, and nothing needs a server.
*/
(function () {
  "use strict";

  var STYLE_URL = "https://tiles.openfreemap.org/styles/dark";
  var STYLE_FALLBACK = {
    version: 8,
    sources: {
      ofm: { type: "vector", url: "https://tiles.openfreemap.org/planet" }
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#0a0e17" } },
      { id: "water", type: "fill", source: "ofm", "source-layer": "water",
        paint: { "fill-color": "#0b1220" } },
      { id: "waterline", type: "line", source: "ofm", "source-layer": "water",
        paint: { "line-color": "#16283c", "line-width": 1 } }
    ]
  };

  /* The credit line is written from canada.json, not typed into the markup.
     It was the same sentence in index.html and map.html, both of which had to be
     edited when the boundary source changed -- and one of them still said
     CARTO, for a basemap that had been replaced with OpenFreeMap weeks earlier.
     The licence and the source URL ride along in the same file for anyone who
     wants them. */
  function credit(geo) {
    var note = document.getElementById("map-note");
    if (!note) return;
    var boundary = geo && geo.credit ? geo.credit : "boundaries";
    var basemap = geo && geo.basemap ? geo.basemap : "basemap";
    note.textContent = "Boundaries: " + boundary + " \u00b7 basemap: " + basemap;
  }

  var A = window.Aurora;
  var ready = A.ready, fetchJSON = A.fetchJSON, esc = A.esc;
  // The confidence scale lives in core.js so the map legend, the case cards and
  // the map dots cannot disagree about what a colour means. The colours
  // themselves are base.css tokens -- nothing here names one.
  var CONF = A.CONF;
  // cases.json's `conf` is a three-value enum; anything else is a data error and
  // gets the weakest grade rather than an undefined class.
  function confKey(k) { return A.CONF[k] ? k : "partial"; }

  /* MapLibre needs a literal colour string in a paint expression; it will not
     resolve a CSS custom property. So the tokens are read back off the
     document here, once. This is the only bridge between the stylesheet and the
     map, and it is why the layer definitions below build a `match` on the
     grade instead of reading a `color` property off each feature. */
  var CONF_COLOR = (function () {
    var s = getComputedStyle(document.documentElement);
    function tok(name, fallback) {
      var v = s.getPropertyValue(name);
      v = (v || "").trim();
      return v || fallback;
    }
    return {
      primary: tok("--conf-primary", "#5fd4e8"),
      reported: tok("--conf-reported", "#8fa6f7"),
      partial: tok("--conf-partial", "#f59e0b")
    };
  })();
  function confColorExpr() {
    return ["match", ["get", "grade"],
            "primary", CONF_COLOR.primary,
            "reported", CONF_COLOR.reported,
            CONF_COLOR.partial];
  }

  function webgl() {
    try {
      var c = document.createElement("canvas");
      return !!(window.WebGLRenderingContext &&
                (c.getContext("webgl2") || c.getContext("webgl")));
    } catch (e) {
      return false;
    }
  }

  function fail(msg) {
    var n = document.getElementById("map-note");
    if (n) n.innerHTML = '<div class="error-note">' + msg + "</div>";
  }

  ready(function () {
    var el = document.getElementById("map");
    if (!el) return;
    if (typeof maplibregl === "undefined") return fail("The map library did not load.");
    if (!webgl()) {
      // MapLibre needs WebGL. Say so rather than showing an empty grey box;
      // the case table below carries the same information without a map.
      return fail("This browser has no WebGL, so the interactive map cannot draw. " +
                  "The case table below has the same locations in text.");
    }

    // A MapLibre instance is a WebGL context plus a vector-tile download. On
    // the overview page the map sits below the fold, so booting it on load
    // spends a megabyte and a context on a visitor who may never scroll. Wait
    // until the container is close, then boot. map.html puts the map at the
    // top, so the observer fires immediately there and nothing is lost.
    var booted = false;
    function boot() {
      if (booted) return;
      booted = true;
      if (io) io.disconnect();
      draw();
    }
    var io = null;
    if ("IntersectionObserver" in window) {
      io = new IntersectionObserver(function (entries) {
        if (entries.some(function (e) { return e.isIntersecting; })) boot();
      }, { rootMargin: "700px 0px" });
      io.observe(el);
    } else {
      boot();
    }

    function draw() {
    Promise.all([fetchJSON("data/canada.json"), fetchJSON("data/cases.json")])
      .then(function (res) {
        var geo = res[0], cases = res[1];
        credit(geo);
        var map = new maplibregl.Map({
          container: el,
          center: [-100, 57],
          zoom: 2.4,
          minZoom: 1.4,
          maxZoom: 11,
          style: STYLE_URL,
          attributionControl: false,
          renderWorldCopies: false
        });
        // No maxBounds. MapLibre shrinks the zoom until the viewport fits
        // inside the bounds, so any box tighter than the fitted one silently
        // zooms the map out and lands Canada in the middle of the Atlantic.
        // renderWorldCopies:false already stops you panning off the world edge.
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
        map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

        // A keyless style can still be briefly unreachable. A background-only
        // map is a worse map but a legible page; without this the whole section
        // renders as a blank rectangle.
        var styleOK = false;
        map.on("style.load", function () { styleOK = true; });
        map.on("error", function (e) {
          if (styleOK) return;
          map.setStyle(STYLE_FALLBACK);
          styleOK = true;
        });

        map.on("load", function () {
          map.addSource("prov", { type: "geojson", data: geo, promoteId: undefined });
          map.addLayer({
            id: "prov-fill", type: "fill", source: "prov",
            paint: {
              "fill-color": ["match", ["get", "type_en"], "Territory", "#123044", "#141c31"],
              "fill-opacity": 0.42
            }
          });
          map.addLayer({
            id: "prov-line", type: "line", source: "prov",
            paint: {
              "line-color": ["match", ["get", "type_en"], "Territory", "#4d7f92", "#4a5573"],
              "line-width": ["interpolate", ["linear"], ["zoom"], 2, 0.7, 6, 1.6],
              "line-dasharray": [2, 2.5]
            }
          });

          map.addSource("cases", {
            type: "geojson",
            data: {
              type: "FeatureCollection",
              features: cases.map(function (c) {
                var cfg = CONF[c.conf] || CONF.partial;
                return {
                  type: "Feature",
                  geometry: { type: "Point", coordinates: [c.lon, c.lat] },
                  properties: {
                    slug: c.slug, title: c.title, prov: c.prov || "",
                    region: c.region || "", display: c.display || "",
                    summary: c.summary || "", grade: c.conf, label: cfg.label
                  }
                };
              })
            }
          });
          map.addLayer({
            id: "case-halo", type: "circle", source: "cases",
            paint: {
              "circle-radius": ["interpolate", ["linear"], ["zoom"], 2, 11, 8, 20],
              "circle-color": confColorExpr(),
              "circle-opacity": 0.14,
              "circle-blur": 0.7
            }
          });
          map.addLayer({
            id: "case-dot", type: "circle", source: "cases",
            paint: {
              "circle-radius": ["interpolate", ["linear"], ["zoom"], 2, 4.5, 8, 8],
              "circle-color": confColorExpr(),
              "circle-stroke-color": "#04060c",
              "circle-stroke-width": 1.6
            }
          });
          // No label layer of our own. The basemap already labels provinces and
          // territories, and a second set of abbreviations over the top reads as
          // a mistake. Hovering a boundary still names it.

          // Each of these is guarded separately. They were one unguarded run of
          // four calls, so a single throw inside fit() -- which is only wrong on
          // one side of a breakpoint -- silently took buildList() and legend()
          // with it and left an empty panel with no error anywhere on the page.
          // The map is not worth losing the rest of the panel over.
          [
            ["fit", fit],
            ["case list", buildList],
            ["legend", legend],
            ["deep link", fromHash]
          ].forEach(function (step) {
            try { step[1](); } catch (e) { mapWarn("the " + step[0], e); }
          });
          // fit() ran on the "load" event, which can beat the container's first
          // real measurement. Re-run it once the frame is on screen.
          requestAnimationFrame(function () { requestAnimationFrame(function () {
            try { fit(); } catch (e) { mapWarn("the map framing", e); }
          }); });
          setTimeout(function () {
            try { fit(); } catch (e) { mapWarn("the map framing", e); }
          }, 300);
        });

        /* Show a failure in the panel rather than only in the console. A map that
           cannot frame itself is a small problem; a map that silently eats the
           case list is a large one, and the reader has no way to tell which
           happened. */
        function mapWarn(what, e) {
          if (window.console && console.warn) console.warn("AURORA map: " + what, e);
          var host = document.getElementById("map-warn");
          if (!host) return;
          var p = document.createElement("p");
          p.className = "error-note";
          p.textContent = "The map could not finish " + what +
            " (" + (e && e.message ? e.message : String(e)) +
            "). The case list beside it is unaffected — use that, or open the case files directly.";
          host.appendChild(p);
        }

        function fit() {
          // Frame the cases, not the country. Canada runs to 83 degrees north
          // and no case in this index is above the Yukon at 60.7, so fitting
          // the whole territory leaves every marker in the bottom eighth of the
          // map and fills the rest with empty Arctic Ocean. The country's full
          // outline is still drawn underneath for context.
          var b = caseBounds();
          // MapLibre measures its container once and caches it. Fitting before
          // that measurement lands picks a zoom for a box of the wrong shape.
          map.resize();
          // One code path, both widths. There used to be a narrow branch that
          // called jumpTo with a fixed centre and zoom, on the theory that a
          // tall narrow container cannot show the spread without zooming too far
          // out. It zoomed to 3, which in a 430px container frames about 45
          // degrees of longitude -- two of the eighteen cases were on screen and
          // the other sixteen were off it to the west. fitBounds picks the zoom
          // from the actual container, and maxZoom only stops it zooming *in*
          // too far on a wide screen, which is the case that needed a cap.
          var centre = [(b.west + b.east) / 2, (b.south + b.north) / 2];
          // MapLibre will take a [lat, lng] pair and throw "Invalid LngLat
          // latitude value" from inside whatever called it. Say which value is
          // wrong instead, because the thrown message names neither. This line
          // is the only place a centre is built by hand.
          if (Math.abs(centre[1]) > 90 || Math.abs(centre[0]) > 180) {
            throw new Error("map.js: centre is " + JSON.stringify(centre) +
              " -- that is not [lng, lat]");
          }
          map.fitBounds([[b.west, b.south], [b.east, b.north]],
                        { padding: A.narrow() ? 24 : 40, maxZoom: 6, duration: 0 });
        }

        function caseBounds() {
          var w = 180, e = -180, s = 90, n = -90;
          cases.forEach(function (c) {
            if (c.lon < w) w = c.lon;
            if (c.lon > e) e = c.lon;
            if (c.lat < s) s = c.lat;
            if (c.lat > n) n = c.lat;
          });
          var padLon = Math.max((e - w) * 0.12, 3);
          var padLat = Math.max((n - s) * 0.22, 2);
          return { west: w - padLon, east: e + padLon, south: s - padLat, north: n + padLat };
        }

        // Re-fit on resize, debounced. Only while the user has not moved the
        // map themselves -- yanking the view back after someone has panned to
        // Nunavut is worse than a slightly loose frame.
        var userMoved = false;
        map.on("dragstart", function () { userMoved = true; });
        var fitTimer = null;
        window.addEventListener("resize", function () {
          clearTimeout(fitTimer);
          fitTimer = setTimeout(function () { if (!userMoved) fit(); }, 180);
        });

        function go(slug) {
          if (location.pathname.indexOf("map.html") === -1) {
            location.href = "case-" + slug + ".html";
          } else {
            select(slug, true);
          }
        }

        function select(slug, fromList) {
          var c = cases.filter(function (x) { return x.slug === slug; })[0];
          if (!c) return;
          if (!fromList) {
            map.flyTo({ center: [c.lon, c.lat], zoom: Math.max(map.getZoom(), 5) });
            var b = document.querySelector('#map-list button[data-slug="' + slug + '"]');
            if (b && b.scrollIntoView) b.scrollIntoView({ block: "nearest" });
          }
          var list = document.getElementById("map-list");
          if (list) {
            // aria-current is what base.css styles. An is-active class was
            // toggled here too and had no rule anywhere.
            list.querySelectorAll("button").forEach(function (x) {
              x.setAttribute("aria-current", String(x.dataset.slug === slug));
            });
          }
          if (history.replaceState) history.replaceState(null, "", "#" + slug);
        }

        function buildList() {
          var list = document.getElementById("map-list");
          if (!list) return;
          cases.slice().sort(function (a, b) { return a.date < b.date ? -1 : 1; })
            .forEach(function (c) {
              var li = document.createElement("li");
              var b = document.createElement("button");
              b.type = "button";
              b.dataset.slug = c.slug;
              b.setAttribute("aria-current", "false");
              b.innerHTML = '<span class="yr">' + esc(c.date.slice(0, 4)) + "</span>" +
                '<span class="nm"><b>' + esc(c.title) + "</b>" +
                (c.prov ? ' <span class="pv">' + esc(c.prov) + "</span>" : "") +
                '<span class="dot conf-' + confKey(c.conf) + '"></span></span>';
              b.addEventListener("click", function () {
                go(c.slug);
                map.flyTo({ center: [c.lon, c.lat], zoom: Math.max(map.getZoom(), 5) });
              });
              li.appendChild(b);
              list.appendChild(li);
            });
        }

        function legend() {
          var legend = document.getElementById("map-legend");
          if (!legend) return;
          Object.keys(CONF).forEach(function (k) {
            var li = document.createElement("li");
            li.innerHTML = '<span class="swatch conf-' + k + '"></span>' + CONF[k].label;
            legend.appendChild(li);
          });
        }

        function popupHtml(p) {
          return "<h4>" + esc(p.title) + (p.prov ? ", " + esc(p.prov) : "") + "</h4>" +
            '<p class="pp">' + esc(p.display) + " &middot; " + esc(p.region) + "</p>" +
            "<p>" + esc(p.summary) + "</p>" +
            '<p class="pp conf-' + confKey(p.grade) + '"><span class="label">' +
              esc(p.label) + "</span></p>";
        }

        // Deep link. Every case page's "view on map" chip links to
        // map.html#<slug>; without this the fragment was ignored and the map
        // loaded with no case selected.
        function fromHash() {
          var slug = decodeURIComponent((location.hash || "").slice(1));
          if (!slug || !cases.some(function (c) { return c.slug === slug; })) return;
          select(slug, false);
        }
        window.addEventListener("hashchange", fromHash);

        map.on("click", "case-dot", function (e) {
          var f = e.features && e.features[0];
          if (!f) return;
          new maplibregl.Popup({ maxWidth: "300px", closeButton: true })
            .setLngLat(e.lngLat)
            .setHTML(popupHtml(f.properties))
            .addTo(map);
          select(f.properties.slug, true);
        });
        map.on("click", "prov-line", function (e) {
          var f = e.features && e.features[0];
          if (!f) return;
          new maplibregl.Popup({ closeButton: true, maxWidth: "240px" })
            .setLngLat(e.lngLat)
            .setHTML("<h4>" + esc(f.properties.name) + "</h4>" +
                     '<p class="pp">' + esc(f.properties.type_en) + "</p>")
            .addTo(map);
        });
        map.on("mousemove", "prov-fill", function (e) {
          var f = e.features && e.features[0];
          map.getCanvas().style.cursor = f ? "help" : "";
        });
        for (var layer of ["case-dot", "prov-line"]) {
          map.on("mouseenter", layer, function () { map.getCanvas().style.cursor = "pointer"; });
          map.on("mouseleave", layer, function () { map.getCanvas().style.cursor = ""; });
        }

        // Keyboard: the markers are in a canvas, so the list beside the map is
        // the only way to reach a case without a mouse. Selecting there moves
        // the map, which is what the list is for.
        var first = document.querySelector("#map-list button");
        if (first) first.setAttribute("tabindex", "0");
      })
      .catch(function (e) {
        fail("Map data could not load: " + e.message +
             " The case list below carries the same information.");
      });
    }
  });
})();
