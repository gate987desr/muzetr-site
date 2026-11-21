/* ==========================================================================
   饮冰室 · site.js
   Display settings, reading aids, search index, command palette, filters,
   local guestbook. No dependencies.
   ========================================================================== */

(function () {
  "use strict";

  var root = document.documentElement;
  var KEYS = {
    theme: "icing.theme",
    size: "icing.size",
    face: "icing.face",
    guestbook: "icing.guestbook"
  };

  function $(selector, scope) { return (scope || document).querySelector(selector); }
  function $$(selector, scope) {
    return Array.prototype.slice.call((scope || document).querySelectorAll(selector));
  }
  function read(key, fallback) {
    try {
      var value = localStorage.getItem(key);
      return value === null ? fallback : value;
    } catch (error) { return fallback; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, value); } catch (error) {}
  }
  function debounce(fn, wait) {
    var timer = null;
    return function () {
      var args = arguments, self = this;
      window.clearTimeout(timer);
      timer = window.setTimeout(function () { fn.apply(self, args); }, wait);
    };
  }
  function escapeHTML(value) {
    return String(value === undefined || value === null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function stamp(iso) {
    var date = iso ? new Date(iso) : new Date();
    if (isNaN(date.getTime())) date = new Date();
    var pad = function (n) { return n < 10 ? "0" + n : "" + n; };
    return date.getFullYear() + "." + pad(date.getMonth() + 1) + "." + pad(date.getDate());
  }

  /* ---------- 1. display settings -------------------------------------- */

  function syncSettings() {
    var theme = root.getAttribute("data-theme");
    var size = root.getAttribute("data-size");
    var face = root.getAttribute("data-face");
    $$("[data-set-theme]").forEach(function (button) {
      button.classList.toggle("is-current", button.getAttribute("data-set-theme") === theme);
    });
    $$("[data-set-size]").forEach(function (button) {
      button.classList.toggle("is-current", button.getAttribute("data-set-size") === size);
    });
    $$("[data-set-face]").forEach(function (button) {
      button.classList.toggle("is-current", button.getAttribute("data-set-face") === face);
    });
  }

  function setTheme(theme) {
    root.setAttribute("data-theme", theme);
    save(KEYS.theme, theme);
    syncSettings();
  }

  var themeToggle = $("#theme-toggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      setTheme(root.getAttribute("data-theme") === "night" ? "paper" : "night");
    });
  }

  $$("[data-set-theme]").forEach(function (button) {
    button.addEventListener("click", function () { setTheme(button.getAttribute("data-set-theme")); });
  });
  $$("[data-set-size]").forEach(function (button) {
    button.addEventListener("click", function () {
      var size = button.getAttribute("data-set-size");
      root.setAttribute("data-size", size);
      save(KEYS.size, size);
      syncSettings();
    });
  });
  $$("[data-set-face]").forEach(function (button) {
    button.addEventListener("click", function () {
      var face = button.getAttribute("data-set-face");
      root.setAttribute("data-face", face);
      save(KEYS.face, face);
      syncSettings();
    });
  });
  syncSettings();

  document.addEventListener("click", function (event) {
    var settings = $(".settings");
    if (settings && settings.open && !settings.contains(event.target)) settings.open = false;
  });

  /* ---------- 2. today ------------------------------------------------- */

  function romanYear(value) {
    var table = [
      [1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"],
      [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"]
    ];
    var out = "";
    var rest = value;
    table.forEach(function (pair) {
      while (rest >= pair[0]) { out += pair[1]; rest -= pair[0]; }
    });
    return out;
  }

  var todayEl = $("[data-today]");
  if (todayEl) {
    var now = new Date();
    var weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
    var months = ["Ian", "Feb", "Mar", "Apr", "Mai", "Iun", "Iul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    todayEl.textContent = now.getFullYear() + "年" + (now.getMonth() + 1) + "月" + now.getDate() + "日";
    var weekEl = $("[data-today-week]");
    if (weekEl) {
      weekEl.textContent = weekdays[now.getDay()] + " · " + now.getDate() + " " +
        months[now.getMonth()] + " " + romanYear(now.getFullYear());
    }
  }

  /* ---------- 3. reading progress + table of contents ------------------ */

  var progressBar = $("#reading-progress");
  var tocLinks = $$(".toc-item a");
  var tocTargets = tocLinks.map(function (link) {
    var id = (link.getAttribute("href") || "").replace(/^#/, "");
    return id ? document.getElementById(id) : null;
  }).filter(Boolean);

  var onScroll = function () {
    var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    var max = document.documentElement.scrollHeight - window.innerHeight;
    var percent = max > 0 ? Math.min(100, Math.max(0, (scrollTop / max) * 100)) : 0;

    if (progressBar) progressBar.style.width = percent.toFixed(2) + "%";
    var valueEl = $("#toc-progress-value");
    if (valueEl) valueEl.textContent = String(Math.round(percent));

    if (tocTargets.length) {
      var current = tocTargets[0];
      for (var i = 0; i < tocTargets.length; i += 1) {
        if (tocTargets[i].getBoundingClientRect().top <= 140) current = tocTargets[i];
      }
      tocLinks.forEach(function (link) {
        link.classList.toggle("is-current", current && link.getAttribute("href") === "#" + current.id);
      });
    }
  };

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  onScroll();

  /* ---------- 4. code copy --------------------------------------------- */

  $$(".code-block").forEach(function (block) {
    var head = $(".code-head", block);
    var code = $("code", block);
    if (!head || !code) return;
    var button = document.createElement("button");
    button.type = "button";
    button.className = "code-copy";
    button.textContent = "复制";
    button.addEventListener("click", function () {
      var text = code.innerText || code.textContent || "";
      var done = function () {
        button.textContent = "已复制";
        window.setTimeout(function () { button.textContent = "复制"; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, done);
      } else {
        var area = document.createElement("textarea");
        area.value = text;
        document.body.appendChild(area);
        area.select();
        try { document.execCommand("copy"); } catch (error) {}
        document.body.removeChild(area);
        done();
      }
    });
    head.appendChild(button);
  });

  /* ---------- 5. search index ------------------------------------------ */

  var indexPromise = null;
  function loadIndex() {
    if (!indexPromise) {
      indexPromise = fetch("/assets/data/search.json", { cache: "force-cache" })
        .then(function (response) { return response.ok ? response.json() : []; })
        .catch(function () { return []; });
    }
    return indexPromise;
  }

  var KIND_LABELS = {
    post: "文章", note: "碎碎念", collection: "收藏",
    project: "作品", page: "页面"
  };

  function scoreEntry(entry, query) {
    var title = (entry.title || "").toLowerCase();
    var summary = (entry.summary || "").toLowerCase();
    var body = (entry.body || "").toLowerCase();
    var tags = (entry.tags || []).join(" ").toLowerCase();
    var score = 0;
    if (title === query) score += 220;
    if (title.indexOf(query) >= 0) score += 110;
    if (tags.indexOf(query) >= 0) score += 48;
    if (summary.indexOf(query) >= 0) score += 36;
    if (body.indexOf(query) >= 0) score += 12;
    return score;
  }

  function search(index, query, kind) {
    var needle = (query || "").trim().toLowerCase();
    if (!needle) return [];
    var results = [];
    index.forEach(function (entry) {
      if (kind && kind !== "*" && entry.kind !== kind) return;
      var score = scoreEntry(entry, needle);
      if (score > 0) results.push({ entry: entry, score: score });
    });
    results.sort(function (a, b) { return b.score - a.score; });
    return results;
  }

  function highlight(text, query) {
    var safe = escapeHTML(text);
    if (!query) return safe;
    var pattern = new RegExp("(" + query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
    return safe.replace(pattern, "<mark>$1</mark>");
  }

  function snippet(text, query) {
    var body = text || "";
    var at = body.toLowerCase().indexOf(query.toLowerCase());
    if (at < 0) return body.slice(0, 96) + (body.length > 96 ? "…" : "");
    var start = Math.max(0, at - 34);
    var end = Math.min(body.length, at + query.length + 70);
    return (start > 0 ? "…" : "") + body.slice(start, end) + (end < body.length ? "…" : "");
  }

  /* ---------- 6. command palette --------------------------------------- */

  var palette = $("#palette");
  var paletteInput = $("#palette-input");
  var paletteResults = $("#palette-results");
  var paletteActive = 0;
  var paletteRows = [];

  function renderPalette(results, query) {
    if (!paletteResults) return;
    paletteActive = 0;
    paletteRows = results;
    if (!results.length) {
      paletteResults.innerHTML = '<li class="palette-empty">' +
        (query ? "没有找到「" + escapeHTML(query) + "」。" : "敲两个字试试。") + "</li>";
      return;
    }
    paletteResults.innerHTML = results.map(function (result, index) {
      var entry = result.entry || result;
      return '<li class="palette-item' + (index === 0 ? " is-active" : "") + '">' +
        '<a href="' + escapeHTML(entry.url) + '">' +
        '<span class="palette-kind">' + escapeHTML(KIND_LABELS[entry.kind] || "页面") + "</span>" +
        '<span class="palette-title">' + highlight(entry.title || entry.url, query) + "</span>" +
        "</a></li>";
    }).join("");
  }

  function setPaletteActive(next) {
    var items = $$(".palette-item", paletteResults);
    if (!items.length) return;
    paletteActive = (next + items.length) % items.length;
    items.forEach(function (item, index) { item.classList.toggle("is-active", index === paletteActive); });
    var active = items[paletteActive];
    if (active && active.scrollIntoView) active.scrollIntoView({ block: "nearest" });
  }

  function openPalette() {
    if (!palette) return;
    palette.hidden = false;
    document.body.style.overflow = "hidden";
    if (paletteInput) {
      paletteInput.value = "";
      paletteInput.focus();
    }
    loadIndex().then(function (index) {
      var recent = index.filter(function (entry) { return entry.kind === "post"; }).slice(0, 7);
      renderPalette(recent.map(function (entry) { return { entry: entry, score: 0 }; }), "");
    });
  }

  function closePalette() {
    if (!palette) return;
    palette.hidden = true;
    document.body.style.overflow = "";
  }

  var paletteButton = $("#search-open");
  if (paletteButton) paletteButton.addEventListener("click", openPalette);

  if (palette && (window.location.hash === "#search" ||
      new URLSearchParams(window.location.search).has("palette"))) {
    openPalette();
  }

  if (palette) {
    palette.addEventListener("click", function (event) {
      if (event.target === palette) closePalette();
    });
  }

  if (paletteInput) {
    paletteInput.addEventListener("input", function () {
      var query = paletteInput.value;
      if (!query.trim()) {
        loadIndex().then(function (index) {
          var recent = index.filter(function (entry) { return entry.kind === "post"; }).slice(0, 7);
          renderPalette(recent.map(function (entry) { return { entry: entry, score: 0 }; }), "");
        });
        return;
      }
      loadIndex().then(function (index) {
        var results = search(index, query, "*").slice(0, 9);
        renderPalette(results, query.trim());
      });
    });
  }

  document.addEventListener("keydown", function (event) {
    var tag = (event.target.tagName || "").toLowerCase();
    var typing = tag === "input" || tag === "textarea" || event.target.isContentEditable;

    if ((event.ctrlKey || event.metaKey) && String(event.key).toLowerCase() === "k") {
      event.preventDefault();
      if (palette && palette.hidden) openPalette(); else closePalette();
      return;
    }

    if (!palette || palette.hidden) {
      if (!typing && event.key === "/") {
        event.preventDefault();
        openPalette();
      }
      return;
    }

    if (event.key === "Escape") { event.preventDefault(); closePalette(); return; }
    if (event.key === "ArrowDown") { event.preventDefault(); setPaletteActive(paletteActive + 1); return; }
    if (event.key === "ArrowUp") { event.preventDefault(); setPaletteActive(paletteActive - 1); return; }
    if (event.key === "Enter") {
      var link = document.querySelectorAll(".palette-item a")[paletteActive];
      if (link) { event.preventDefault(); window.location.href = link.getAttribute("href"); }
    }
  });

  /* ---------- 7. search page ------------------------------------------- */

  var searchInput = $("#search-input");
  if (searchInput) {
    var searchResults = $("#search-results");
    var searchHint = $("#search-hint");
    var searchKind = "*";

    var runSearch = function () {
      var query = searchInput.value.trim();
      if (!query) {
        searchResults.innerHTML = "";
        searchHint.hidden = false;
        return;
      }
      searchHint.hidden = true;
      loadIndex().then(function (index) {
        var results = search(index, query, searchKind).slice(0, 40);
        if (!results.length) {
          searchResults.innerHTML = '<li class="search-empty">没有找到「' + escapeHTML(query) + "」。换个词试试，或者翻翻<a href=\"/archive/\">归档</a>。</li>";
          return;
        }
        searchResults.innerHTML = results.map(function (result) {
          var entry = result.entry;
          return '<li class="search-result"><a href="' + escapeHTML(entry.url) + '">' +
            '<span class="search-result-head"><span class="search-kind">' + escapeHTML(KIND_LABELS[entry.kind] || "页面") + "</span>" +
            (entry.date ? "<span>" + escapeHTML(entry.date) + "</span>" : "") + "</span>" +
            '<span class="search-result-title">' + highlight(entry.title, query) + "</span>" +
            '<span class="search-result-snippet">' + highlight(snippet(entry.summary || entry.body, query), query) + "</span>" +
            "</a></li>";
        }).join("");
      });
    };

    searchInput.addEventListener("input", debounce(runSearch, 130));
    $$("[data-search-kinds] .chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        $$("[data-search-kinds] .chip").forEach(function (other) { other.classList.remove("is-active"); });
        chip.classList.add("is-active");
        searchKind = chip.getAttribute("data-kind") || "*";
        runSearch();
      });
    });
    var params = new URLSearchParams(window.location.search);
    if (params.get("q")) { searchInput.value = params.get("q"); runSearch(); }
    searchInput.focus();
  }

  /* ---------- 8. note tag filters -------------------------------------- */

  var noteFilterButtons = $$("[data-note-filter]");
  if (noteFilterButtons.length) {
    noteFilterButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        noteFilterButtons.forEach(function (other) { other.classList.remove("is-active"); });
        button.classList.add("is-active");
        var tag = button.getAttribute("data-note-filter");
        $$(".note").forEach(function (note) {
          var tags = (note.getAttribute("data-tags") || "").trim().split(/\s+/);
          var visible = tag === "*" || tags.indexOf(tag) >= 0;
          note.classList.toggle("is-hidden", !visible);
        });
        $$(".note-month").forEach(function (section) {
          var visible = $$(".note:not(.is-hidden)", section).length;
          section.hidden = visible === 0;
        });
      });
    });
  }

  /* ---------- 9. collection filters ------------------------------------ */

  var shelf = $("[data-shelf]");
  if (shelf) {
    var filters = { type: "*", status: "*" };
    var emptyNote = $("[data-shelf-empty]");
    var applyShelf = function () {
      var shown = 0;
      $$(".shelf-card", shelf).forEach(function (card) {
        var type = card.getAttribute("data-type");
        var status = card.getAttribute("data-status");
        var visible = (filters.type === "*" || type === filters.type) &&
          (filters.status === "*" || status === filters.status);
        card.classList.toggle("is-hidden", !visible);
        if (visible) shown += 1;
      });
      if (emptyNote) emptyNote.hidden = shown > 0;
    };
    $$("[data-collection-type] .chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        $$("[data-collection-type] .chip").forEach(function (other) { other.classList.remove("is-active"); });
        chip.classList.add("is-active");
        filters.type = chip.getAttribute("data-value") || "*";
        applyShelf();
      });
    });
    $$("[data-collection-status] .chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        $$("[data-collection-status] .chip").forEach(function (other) { other.classList.remove("is-active"); });
        chip.classList.add("is-active");
        filters.status = chip.getAttribute("data-value") || "*";
        applyShelf();
      });
    });
  }

  /* ---------- 10. local guestbook -------------------------------------- */

  var gbForm = $("#gb-form");
  if (gbForm) {
    var gbList = $("#gb-list");
    var gbEmpty = $("#gb-empty");
    var gbCount = $("#gb-count");
    var gbText = $("#gb-text");
    var gbName = $("#gb-name");
    var stored = [];
    try { stored = JSON.parse(read(KEYS.guestbook, "[]")) || []; } catch (error) { stored = []; }

    var countMessages = function () { return $$(".gb-item", gbList).length; };
    var toggleEmpty = function () { if (gbEmpty) gbEmpty.hidden = countMessages() > 0; };

    var buildItem = function (item, isNew) {
      var li = document.createElement("li");
      li.className = "gb-item" + (isNew ? " is-new" : "");
      var head = document.createElement("p");
      head.className = "gb-head";
      var name = document.createElement("strong");
      name.textContent = item.name || "无名";
      var time = document.createElement("time");
      time.textContent = item.date || stamp();
      head.appendChild(name);
      head.appendChild(time);
      var text = document.createElement("p");
      text.className = "gb-text";
      text.textContent = item.text || "";
      li.appendChild(head);
      li.appendChild(text);
      return li;
    };

    stored.slice(-40).reverse().forEach(function (item) {
      gbList.insertBefore(buildItem(item, false), gbList.firstChild);
    });
    toggleEmpty();

    if (gbText && gbCount) {
      gbText.addEventListener("input", function () {
        gbCount.textContent = gbText.value.length + " / 280";
      });
    }

    gbForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var name = (gbName.value || "").trim();
      var text = (gbText.value || "").trim();
      if (!name || !text) return;
      var item = { name: name.slice(0, 24), text: text.slice(0, 280), date: stamp() };
      stored.push(item);
      stored = stored.slice(-60);
      save(KEYS.guestbook, JSON.stringify(stored));
      gbList.insertBefore(buildItem(item, true), gbList.firstChild);
      gbForm.reset();
      if (gbCount) gbCount.textContent = "0 / 280";
      toggleEmpty();
    });
  }

  /* ---------- 11. external links --------------------------------------- */

  $$('a[href^="http"]').forEach(function (link) {
    if (link.hostname && link.hostname !== window.location.hostname) {
      link.setAttribute("rel", "noopener noreferrer");
      if (!link.getAttribute("target")) link.setAttribute("target", "_blank");
    }
  });
})();
