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

  /* Match on a data attribute without interpolating the value into a selector
   * string, where a quote in the value would break out of it. */
  function findBy(root, attr, val) {
    var sel = root.querySelectorAll("[data-" + attr + "]");
    for (var i = 0; i < sel.length; i++) if (sel[i].dataset[attr] === val) return sel[i];
    return null;
  }

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  /* base.css switches the hero to one column and the nav to a drawer at
   * max-width 940px and 760px. These used to be hardcoded as innerWidth
   * literals in JS at 900 and 760, so between 761-940px the FAQ collapsed
   * while the layout was still two columns. Ask the stylesheet instead. */
  var NARROW = "(max-width: 760px)", WIDE = "(min-width: 761px)", SINGLE = "(max-width: 940px)";
  function narrow() { return window.matchMedia(NARROW).matches; }
  function singleColumn() { return window.matchMedia(SINGLE).matches; }

  return { ready: ready, fetchJSON: fetchJSON, esc: esc, findBy: findBy,
           $: $, $$: $$, narrow: narrow, singleColumn: singleColumn };
})();
