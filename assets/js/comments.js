/* ==========================================================================
   饮冰室 · comments.js
   支持两种评论来源，由 site.config.json 的 features.comments.provider 决定：
   - "netlify"：本站自己的接口（Netlify Functions + Netlify Blobs），昵称/正文/图片
   - "giscus" ：GitHub Discussions（评论者需要 GitHub 账号）
   ========================================================================== */

(function () {
  "use strict";

  var host = document.getElementById("comments");
  if (!host) return;

  var configEl = document.getElementById("comments-config");
  var config = {};
  if (configEl) {
    try { config = JSON.parse(configEl.textContent); } catch (error) { return; }
  }

  var provider = host.getAttribute("data-provider") || "";
  var body = document.getElementById("comments-body");
  if (!body) return;

  /* ---------- 公共小工具 ---------- */

  function formatTime(stamp) {
    var date = new Date(stamp);
    if (isNaN(date.getTime())) return "";
    var pad = function (n) { return n < 10 ? "0" + n : "" + n; };
    return date.getFullYear() + "年" + (date.getMonth() + 1) + "月" + date.getDate() + "日 " +
      pad(date.getHours()) + ":" + pad(date.getMinutes());
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  /* ---------- 本站接口（Netlify Functions） ---------- */

  function mountNative(options) {
    var base = (options.apiBase || "/api").replace(/\/+$/, "");
    var pagePath = window.location.pathname;
    var form = document.getElementById("comment-form");
    var status = document.getElementById("comment-status");
    var fileInput = document.getElementById("comment-image");
    var submit = form ? form.querySelector('button[type="submit"]') : null;
    var countEl = document.querySelector("[data-count]");

    function say(message, kind) {
      if (!status) return;
      status.textContent = message || "";
      status.className = "comment-status" + (kind ? " is-" + kind : "");
    }

    function renderList(comments) {
      body.innerHTML = "";
      if (countEl) countEl.textContent = comments.length ? comments.length + " 条" : "";

      if (!comments.length) {
        body.appendChild(el("p", "comments-empty", "还没有人说话。第一个位置留给你。"));
        return;
      }

      var list = el("ul", "comment-list");
      comments.forEach(function (item) {
        var li = el("li", "comment-item");
        var head = el("div", "comment-head");
        head.appendChild(el("strong", "comment-name", item.name || "无名"));
        head.appendChild(el("time", "comment-time", formatTime(item.createdAt)));
        li.appendChild(head);
        if (item.body) {
          var text = el("p", "comment-text", item.body);
          li.appendChild(text);
        }
        if (item.image) {
          var figure = el("figure", "comment-image");
          var img = document.createElement("img");
          img.src = item.image;
          img.alt = "评论图片";
          img.loading = "lazy";
          figure.appendChild(img);
          li.appendChild(figure);
        }
        list.appendChild(li);
      });
      body.appendChild(list);
    }

    function load() {
      fetch(base + "/comments?path=" + encodeURIComponent(pagePath), {
        headers: { accept: "application/json" },
      })
        .then(function (response) { return response.ok ? response.json() : { comments: [] }; })
        .then(function (data) { renderList(data.comments || []); })
        .catch(function () {
          body.innerHTML = "";
          body.appendChild(el("p", "comments-empty", "评论加载失败，晚点再试。"));
        });
    }

    function readImage(file) {
      return new Promise(function (resolve, reject) {
        if (!file) return resolve(null);
        if (file.size > 2 * 1024 * 1024) return reject(new Error("图片超过 2 MB"));
        var reader = new FileReader();
        reader.onload = function () { resolve(reader.result); };
        reader.onerror = function () { reject(new Error("图片读取失败")); };
        reader.readAsDataURL(file);
      });
    }

    if (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        var name = form.name.value.trim();
        var text = form.body.value.trim();
        var file = fileInput && fileInput.files ? fileInput.files[0] : null;
        if (!name) return say("先写个昵称。", "error");
        if (!text && !file) return say("写点内容，或者选一张图片。", "error");

        say("正在发布…");
        if (submit) submit.disabled = true;

        readImage(file)
          .then(function (dataUrl) {
            return fetch(base + "/comments", {
              method: "POST",
              headers: { "content-type": "application/json" },
              body: JSON.stringify({ path: pagePath, name: name, body: text, image: dataUrl }),
            });
          })
          .then(function (response) { return response.json().catch(function () { return {}; }); })
          .then(function (result) {
            if (result && result.ok) {
              say("发布成功。", "ok");
              form.reset();
              load();
            } else {
              var messages = {
                "too-short": "内容太短了。",
                "rate-limited": "今天发得有点多，明天再来。",
                "image-too-large": "图片超过 2 MB，换一张小一点的。",
                "unsupported-image": "只支持 JPG / PNG / WEBP / GIF。",
              };
              say(messages[result.error] || "发布失败，晚点再试。", "error");
            }
          })
          .catch(function (error) {
            say(error && error.message ? error.message : "发布失败，检查一下网络。", "error");
          })
          .then(function () {
            if (submit) submit.disabled = false;
          });
      });
    }

    load();
  }

  /* ---------- giscus ---------- */

  function themeName() {
    return document.documentElement.getAttribute("data-theme") === "night" ? "dark_dimmed" : "light";
  }

  function syncTheme() {
    var frame = document.querySelector("iframe.giscus-frame");
    if (!frame || !frame.contentWindow) return;
    frame.contentWindow.postMessage(
      { giscus: { setConfig: { theme: themeName() } } },
      "https://giscus.app"
    );
  }

  function mountGiscus(options) {
    var missing = ["repo", "repoId", "category", "categoryId"].filter(function (key) {
      return !options[key];
    });
    if (missing.length) {
      body.innerHTML =
        '<p class="comments-hint">评论区还没配置好：缺 <code>' +
        missing.join("</code>、<code>") +
        "</code>。填进 site.config.json 的 features.giscus。</p>";
      return;
    }

    body.innerHTML = "";
    var script = document.createElement("script");
    script.src = "https://giscus.app/client.js";
    script.async = true;
    script.crossOrigin = "anonymous";
    script.setAttribute("data-repo", options.repo);
    script.setAttribute("data-repo-id", options.repoId);
    script.setAttribute("data-category", options.category);
    script.setAttribute("data-category-id", options.categoryId);
    script.setAttribute("data-mapping", options.mapping || "pathname");
    script.setAttribute("data-strict", "0");
    script.setAttribute("data-reactions-enabled", "1");
    script.setAttribute("data-emit-metadata", "0");
    script.setAttribute("data-input-position", "top");
    script.setAttribute("data-theme", themeName());
    script.setAttribute("data-lang", "zh-CN");
    script.setAttribute("data-loading", "lazy");
    body.appendChild(script);

    var themeButton = document.getElementById("theme-toggle");
    if (themeButton) themeButton.addEventListener("click", function () { window.setTimeout(syncTheme, 120); });
    window.addEventListener("message", function (event) {
      if (event.origin !== "https://giscus.app") return;
      if (event.data && event.data.giscus) syncTheme();
    });
  }

  if (provider === "netlify") {
    mountNative(config);
  } else if (provider === "giscus") {
    mountGiscus(config.giscus || {});
  }
})();
