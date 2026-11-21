/* ==========================================================================
   饮冰室 · admin-comments.js
   评论管理页：列出全部评论，支持逐条删除与整篇清空。
   令牌只存在 localStorage，通过 x-admin-token 请求头发给接口。
   ========================================================================== */

(function () {
  "use strict";

  var listEl = document.getElementById("admin-list");
  if (!listEl) return;

  var tokenInput = document.getElementById("admin-token");
  var saveBtn = document.getElementById("admin-save");
  var refreshBtn = document.getElementById("admin-refresh");
  var statusEl = document.getElementById("admin-status");
  var STORAGE_KEY = "muzetr.admin.token";
  var API = "/api/comments";

  function status(text, kind) {
    if (!statusEl) return;
    statusEl.textContent = text || "";
    statusEl.className = "admin-status" + (kind ? " is-" + kind : "");
  }

  function token() {
    return (tokenInput && tokenInput.value.trim()) || localStorage.getItem(STORAGE_KEY) || "";
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function when(stamp) {
    var date = new Date(stamp);
    if (isNaN(date.getTime())) return "";
    var pad = function (n) { return n < 10 ? "0" + n : "" + n; };
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate()) +
      " " + pad(date.getHours()) + ":" + pad(date.getMinutes());
  }

  function request(method, body) {
    var url = method === "GET" ? API + "?admin=1" : API;
    var headers = { "x-admin-token": token() };
    if (body) headers["content-type"] = "application/json";
    return fetch(url, { method: method, headers: headers, body: body ? JSON.stringify(body) : undefined })
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (data) {
          return { ok: response.ok, status: response.status, data: data };
        });
      });
  }

  function render(comments) {
    listEl.innerHTML = "";
    if (!comments.length) {
      listEl.appendChild(el("p", "admin-empty", "还没有任何评论。"));
      return;
    }

    var groups = {};
    comments.forEach(function (item) {
      var page = item.page || "(未知页面)";
      (groups[page] = groups[page] || []).push(item);
    });

    Object.keys(groups).sort().forEach(function (page) {
      var items = groups[page].sort(function (a, b) { return (a.createdAt || 0) - (b.createdAt || 0); });
      var section = el("section", "admin-group");

      var head = el("div", "admin-group-head");
      head.appendChild(el("span", "admin-group-path", page));
      head.appendChild(el("span", "admin-group-count", items.length + " 条"));
      var link = el("a", "admin-group-link", "打开文章 ↗");
      link.href = page;
      link.target = "_blank";
      link.rel = "noopener";
      head.appendChild(link);
      var purge = el("button", "admin-btn admin-btn-danger", "清空这篇");
      purge.type = "button";
      purge.addEventListener("click", function () {
        if (!window.confirm("确定清空「" + page + "」的 " + items.length + " 条评论？这个操作不能撤销。")) return;
        request("POST", { action: "purge", path: page }).then(function (res) {
          status(res.ok ? "已清空 " + (res.data.removed || 0) + " 条" : "清空失败", res.ok ? "ok" : "error");
          load();
        });
      });
      head.appendChild(purge);
      section.appendChild(head);

      items.forEach(function (item) {
        var row = el("article", "admin-comment");
        var meta = el("div", "admin-comment-head");
        meta.appendChild(el("strong", "admin-comment-name", item.name || "无名"));
        meta.appendChild(el("time", "admin-comment-time", when(item.createdAt)));
        if (item.image) {
          var tag = el("span", "admin-comment-tag", "带图");
          meta.appendChild(tag);
        }
        var del = el("button", "admin-btn admin-btn-danger", "删除");
        del.type = "button";
        del.addEventListener("click", function () {
          if (!window.confirm("删除这条评论？")) return;
          request("POST", { action: "delete", path: page, id: item.id }).then(function (res) {
            status(res.ok ? "已删除" : "删除失败", res.ok ? "ok" : "error");
            load();
          });
        });
        meta.appendChild(del);
        row.appendChild(meta);

        if (item.body) row.appendChild(el("p", "admin-comment-body", item.body));
        if (item.image) {
          var img = document.createElement("img");
          img.className = "admin-comment-image";
          img.src = item.image;
          img.alt = "评论图片";
          img.loading = "lazy";
          row.appendChild(img);
        }
        section.appendChild(row);
      });

      listEl.appendChild(section);
    });
  }

  function load() {
    if (!token()) {
      status("还没有令牌", "error");
      return;
    }
    status("读取中…");
    request("GET", null).then(function (res) {
      if (res.status === 403) {
        status("令牌不对，或还没保存", "error");
        return;
      }
      if (!res.ok) {
        status("读取失败", "error");
        return;
      }
      status("共 " + (res.data.total || 0) + " 条", "ok");
      render(res.data.comments || []);
    }).catch(function () {
      status("网络错误", "error");
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener("click", function () {
      var value = (tokenInput.value || "").trim();
      if (!value) {
        status("先粘贴令牌", "error");
        return;
      }
      localStorage.setItem(STORAGE_KEY, value);
      status("已保存", "ok");
      load();
    });
  }
  if (refreshBtn) refreshBtn.addEventListener("click", load);

  var saved = localStorage.getItem(STORAGE_KEY);
  if (saved && tokenInput) {
    tokenInput.value = saved;
    load();
  }
})();
