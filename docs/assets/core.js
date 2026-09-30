/* AURORA — shared helpers.
 *
 * Loaded before aurora.js and map.js. These three functions used to be
 * copy-pasted into both files, which is how map.js ended up with no esc() at
 * all and index.html ended up fetching data/cases.json twice.
 */
window.Aurora = (function () {
  "use strict";

  // Marks the document as script-enabled. base.css uses it to hide the
  // "Loading ..." placeholders when JS is off, where they would otherwise sit
  // next to a <noscript> note explaining that nothing is coming.
  document.documentElement.className += " js";

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  var cache = Object.create(null);

  /* fetchJSON is memoised by URL. index.html needs cases.json for both the
   * case cards and the map; without the cache that is two downloads and two
   * JSON parses of the same file. */
  function fetchJSON(url) {
    if (cache[url]) return cache[url];
    cache[url] = fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + " → " + r.status);
      return r.json();
    }).catch(function (e) {
      // Do not memoise a failure: a later retry should be able to succeed.
      delete cache[url];
      throw e;
    });
    return cache[url];
  }

  /* Every value that reaches innerHTML has to go through this. map.js used to
   * interpolate cases.json straight into markup with no escaping at all. */
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  /* base.css switches the nav to a drawer at max-width 760px. This used to be
   * hardcoded as an innerWidth literal in JS at 900, so between 761-900px the
   * FAQ collapsed while the layout was still two columns -- hence asking the
   * stylesheet. There is a second breakpoint at 940px for the hero; it is not
   * used from JS and is not encoded here. */
  var NARROW = "(max-width: 760px)";
  function narrow() { return window.matchMedia(NARROW).matches; }

  /* The sourcing-confidence scale.
   *
   * It used to be defined three times -- here, in map.js, and in aurora.js --
   * and generate_pages.py had a fourth copy for the case-page chips. The copies
   * had already drifted: one said "Mainstream reporting, named sources" and
   * another "Mainstream reporting WITH named sources", both of which ship.
   * map.html's hero once called the wrong colour "mainstream reporting" too.
   *
   * The build now reads the labels below out of this file rather than keeping a
   * fifth copy, so there are two: this, and the colours in base.css as .conf-*.
   * Nothing here sets a colour. */
  var CONF = {
    primary:  { label: "Archival or official record", short: "Archival or official", chip: "chip-a" },
    reported: { label: "Mainstream reporting, named sources", short: "Mainstream reporting", chip: "chip" },
    partial:  { label: "Thin sourcing \u2014 verify before citing", short: "Thin sourcing", chip: "chip-amb" }
  };
  function conf(key) { return CONF[key] || CONF.partial; }

  return { ready: ready, fetchJSON: fetchJSON, esc: esc,
           $: $, $$: $$, narrow: narrow, CONF: CONF, conf: conf };
})();
