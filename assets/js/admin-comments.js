/* ==========================================================================
   饮冰室 · admin-comments.js
   评论管理：列出全部评论（含待审核），支持通过 / 回复 / 删除 / 清空。
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

  function getToken() {
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
    var headers = { "x-admin-token": getToken() };
    if (body) headers["content-type"] = "application/json";
    return fetch(url, { method: method, headers: headers, body: body ? JSON.stringify(body) : undefined })
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (data) {
          return { ok: response.ok, status: response.status, data: data };
        });
      });
  }

  function act(payload, successText) {
    return request("POST", payload).then(function (res) {
      status(res.ok ? successText : "操作失败", res.ok ? "ok" : "error");
      load();
    });
  }

  function button(label, className, onClick) {
    var node = el("button", "admin-btn" + (className ? " " + className : ""), label);
    node.type = "button";
    node.addEventListener("click", onClick);
    return node;
  }

  function replyForm(page, item, container) {
    var wrap = el("div", "admin-reply-form");
    var area = document.createElement("textarea");
    area.rows = 3;
    area.placeholder = "以「屋主」身份回复…";
    wrap.appendChild(area);

    var bar = el("div", "admin-reply-bar");
    bar.appendChild(button("发送", "", function () {
      var text = (area.value || "").trim();
      if (!text) return;
      act({ action: "reply", path: page, parentId: item.id, body: text }, "已回复");
    }));
    bar.appendChild(button("取消", "admin-btn-ghost", function () { wrap.remove(); }));
    wrap.appendChild(bar);
    container.appendChild(wrap);
    area.focus();
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

    var pendingTotal = comments.filter(function (item) { return (item.status || "approved") !== "approved"; }).length;
    status("共 " + comments.length + " 条" + (pendingTotal ? "，其中 " + pendingTotal + " 条待审核" : ""), "ok");

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
      head.appendChild(button("清空这篇", "admin-btn-danger", function () {
        if (!window.confirm("确定清空「" + page + "」的 " + items.length + " 条评论？不能撤销。")) return;
        act({ action: "purge", path: page }, "已清空");
      }));
      section.appendChild(head);

      items.forEach(function (item) {
        var approved = (item.status || "approved") === "approved";
        var row = el("article", "admin-comment" + (approved ? "" : " is-pending"));

        var meta = el("div", "admin-comment-head");
        meta.appendChild(el("strong", "admin-comment-name", item.name || "无名"));
        if (item.role === "owner") meta.appendChild(el("span", "admin-comment-owner", "屋主"));
        meta.appendChild(el("time", "admin-comment-time", when(item.createdAt)));
        meta.appendChild(el("span", "admin-badge" + (approved ? " is-live" : " is-pending"), approved ? "已发布" : "待审核"));
        if (item.parent) meta.appendChild(el("span", "admin-badge", "回复"));
        if (item.image) meta.appendChild(el("span", "admin-badge", "带图"));

        if (!approved) {
          meta.appendChild(button("通过", "admin-btn-primary", function () {
            act({ action: "approve", path: page, id: item.id }, "已通过");
          }));
        }
        meta.appendChild(button("回复", "admin-btn-ghost", function () {
          if (!row.querySelector(".admin-reply-form")) replyForm(page, item, row);
        }));
        meta.appendChild(button("删除", "admin-btn-danger", function () {
          if (!window.confirm("删除这条评论？")) return;
          act({ action: "delete", id: item.id }, "已删除");
        }));
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
    if (!getToken()) {
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
