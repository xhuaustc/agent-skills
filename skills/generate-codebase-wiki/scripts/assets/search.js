/**
 * Client-side full-text search for the wiki.
 *
 * Expected globals (injected by build_wiki.py):
 *   window.__wikiSearchIndex  – Array<{title, url, text}>
 *   window.__wikiBasePrefix   – String, e.g. "../" for subdirectory pages
 */
(function () {
  var searchIndex = window.__wikiSearchIndex || [];
  var basePrefix = window.__wikiBasePrefix || "";
  var input = document.getElementById("wiki-search");
  var results = document.getElementById("search-results");
  if (!input || !results) return;

  input.addEventListener("input", function () {
    var q = this.value.trim().toLowerCase();
    if (q.length < 2) {
      results.className = "search-results";
      results.innerHTML = "";
      return;
    }

    var matches = [];
    for (var i = 0; i < searchIndex.length; i++) {
      var page = searchIndex[i];
      var titleMatch = page.title.toLowerCase().indexOf(q) !== -1;
      var textMatch = page.text.toLowerCase().indexOf(q) !== -1;
      if (titleMatch || textMatch) {
        var snippet = "";
        if (textMatch) {
          var idx = page.text.toLowerCase().indexOf(q);
          var start = Math.max(0, idx - 40);
          var end = Math.min(page.text.length, idx + q.length + 60);
          snippet =
            (start > 0 ? "..." : "") +
            page.text.substring(start, end) +
            (end < page.text.length ? "..." : "");
        }
        matches.push({
          title: page.title,
          url: basePrefix + page.url,
          snippet: snippet,
          titleMatch: titleMatch,
        });
      }
    }

    matches.sort(function (a, b) {
      return (b.titleMatch ? 1 : 0) - (a.titleMatch ? 1 : 0);
    });

    if (matches.length === 0) {
      results.innerHTML =
        '<div class="search-no-results">No results found</div>';
    } else {
      var html = "";
      for (var j = 0; j < Math.min(matches.length, 10); j++) {
        var m = matches[j];
        html += '<a class="search-result-item" href="' + m.url + '">';
        html += '<div class="search-result-title">' + m.title + "</div>";
        if (m.snippet)
          html +=
            '<div class="search-result-snippet">' + m.snippet + "</div>";
        html += "</a>";
      }
      results.innerHTML = html;
    }
    results.className = "search-results visible";
  });

  document.addEventListener("click", function (e) {
    if (!results.contains(e.target) && e.target !== input) {
      results.className = "search-results";
    }
  });

  input.addEventListener("focus", function () {
    if (this.value.trim().length >= 2)
      results.className = "search-results visible";
  });
})();
