#!/usr/bin/env python3
"""饮冰室 · static site builder.

No third-party dependencies: `python build.py` turns the Markdown/JSON in
`content/` into a complete static site in `public/`.

    python build.py            # build everything
    python build.py --clean    # wipe public/ first
    python serve.py            # preview at http://127.0.0.1:8000
"""

from __future__ import annotations

import base64
import glob
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import shutil
import sys
import urllib.parse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.markdown import render as render_markdown  # noqa: E402
from lib.markdown import render_inline, split_front_matter  # noqa: E402
from lib.template import TemplateEngine  # noqa: E402
from lib.console import setup as setup_console  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(ROOT, "content")
ASSETS_DIR = os.path.join(ROOT, "assets")
TEMPLATES_DIR = os.path.join(ROOT, "templates")

ROMAN = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
    (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def roman(number):
    if number <= 0:
        return "—"
    out = []
    for value, glyph in ROMAN:
        while number >= value:
            out.append(glyph)
            number -= value
    return "".join(out)


def fmt_date(iso, style="cn"):
    """YYYY-MM-DD -> 2026年10月12日 / 2026.10.12 / 12 Oct 2026."""
    try:
        day = datetime.strptime(iso[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return iso or ""
    if style == "dot":
        return "%04d.%02d.%02d" % (day.year, day.month, day.day)
    if style == "latin":
        months = ["Ian", "Feb", "Mar", "Apr", "Mai", "Iun", "Iul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return "%d %s %s" % (day.day, months[day.month - 1], roman(day.year))
    return "%d年%d月%d日" % (day.year, day.month, day.day)


def slugify(text):
    plain = re.sub(r"[`*_~\[\]()]", "", text or "")
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", plain).strip("-").lower()
    return slug or "item"


def read_json(name, default):
    path = os.path.join(CONTENT_DIR, name)
    if not os.path.isfile(path):
        print("  ! missing content/%s — using empty default" % name)
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def b64(raw):
    return base64.b64encode(raw).decode("ascii")


# --------------------------------------------------------------------------
# light-weight password protection for locked essays
# --------------------------------------------------------------------------

def _keystream(key, nonce, length):
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        counter += 1
    return bytes(out[:length])


def encrypt_text(plaintext, password, iterations=150000):
    """PBKDF2-SHA256 key + HMAC-CTR keystream, mirrored in assets/js/unlock.js."""
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)
    data = plaintext.encode("utf-8")
    stream = _keystream(key, nonce, len(data))
    cipher = bytes(lhs ^ rhs for lhs, rhs in zip(data, stream))
    tag = hmac.new(key, nonce + cipher, hashlib.sha256).digest()[:16]
    return {
        "v": 1,
        "iter": iterations,
        "salt": b64(salt),
        "nonce": b64(nonce),
        "ct": b64(cipher),
        "tag": b64(tag),
        "len": len(data),
    }


# --------------------------------------------------------------------------
# site
# --------------------------------------------------------------------------

class Site:
    def __init__(self, config):
        self.config = config
        self.site = config
        self.engine = TemplateEngine(TEMPLATES_DIR)
        self.out_dir = os.path.join(ROOT, config.get("build", {}).get("out", "public"))
        self.base_url = config["baseUrl"].rstrip("/")
        self.host = re.sub(r"^https?://", "", self.base_url)
        self.features = config.get("features", {})
        self.sections = config.get("sections", {})
        self.build_stamp = datetime.now()
        self.posts = []
        self.warnings = []

    # -- loading -------------------------------------------------------
    def load(self):
        self.posts = self._load_posts()
        self.notes = read_json("notes.json", [])
        self.collection = read_json("collection.json", [])
        self.projects = read_json("projects.json", [])
        self.friends = read_json("friends.json", [])
        self.about = read_json("about.json", {})
        self.guestbook = read_json("guestbook.json", [])

        for index, note in enumerate(self.notes):
            note["text_html"] = render_inline(html.escape(note.get("text", ""), quote=False), self.host)
            note["date_cn"] = fmt_date(note.get("date", ""))
            note["year"] = (note.get("date") or "0000")[:4]
            note["month"] = (note.get("date") or "00-00")[5:7]
            note["tags"] = note.get("tags", []) or []
            note["id"] = "n-%d" % (index + 1)
            note["anchor"] = note["id"]

        labels = {"anime": "番剧", "film": "电影", "book": "书"}
        for item in self.collection:
            item["type_label"] = labels.get(item.get("type"), "其他")
            item["score_text"] = ("%.1f" % item["score"]) if item.get("score") else "—"
            item["anchor"] = "c-" + slugify(item.get("title", ""))
            year = item.get("year")
            if isinstance(year, int) and year < 0:
                item["year_text"] = "先秦"
            elif year:
                item["year_text"] = str(year)
            else:
                item["year_text"] = "年份不详"

        for item in self.projects:
            item["anchor"] = "p-" + slugify(item.get("title", ""))
            item["status_slug"] = slugify(item.get("status", "")) or "unknown"
            item["year"] = str(item.get("year", ""))

        self.tags = {}
        self.categories = {}
        for post in self.posts:
            for tag in post["tags"]:
                self.tags.setdefault(tag, []).append(post)
            self.categories.setdefault(post["category"], []).append(post)
        for bucket in self.tags.values():
            bucket.sort(key=lambda item: item["date"], reverse=True)
        for bucket in self.categories.values():
            bucket.sort(key=lambda item: item["date"], reverse=True)

        self.stats = {
            "posts": len(self.posts),
            "notes": len(self.notes),
            "collection": len(self.collection),
            "projects": len(self.projects),
            "friends": len(self.friends),
            "tags": len(self.tags),
            "words": sum(post["words"] for post in self.posts) + sum(len(note.get("text", "")) for note in self.notes),
            "updated": max([post["date"] for post in self.posts], default=""),
        }

    def _load_posts(self):
        posts = []
        pattern = os.path.join(CONTENT_DIR, "posts", "*.md")
        for path in sorted(glob.glob(pattern)):
            if os.path.basename(path).startswith(("_", ".")):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                meta, body = split_front_matter(handle.read())
            stem = os.path.splitext(os.path.basename(path))[0]
            slug = meta.get("slug") or stem
            title = meta.get("title") or stem
            body_text = body.strip()
            locked = bool(meta.get("locked"))
            rendered_html = ""
            toc, words, minutes, plain = [], 0, 1, ""
            if locked:
                if not meta.get("password"):
                    self.warnings.append("locked post %s has no password" % slug)
                parsed = render_markdown(body_text, self.host)
                payload = encrypt_text(parsed["html"], str(meta.get("password") or "changeme"))
                toc = []
                minutes = parsed["minutes"]
                words = parsed["words"]
            else:
                parsed = render_markdown(body_text, self.host)
                rendered_html = parsed["html"]
                toc = parsed["toc"]
                words = parsed["words"]
                minutes = parsed["minutes"]
                plain = parsed["text"]
                payload = None

            summary = meta.get("summary") or (plain[:80] if plain else "")
            post = {
                "slug": slug,
                "title": title,
                "title_en": meta.get("title_en", ""),
                "date": str(meta.get("date") or ""),
                "date_cn": fmt_date(str(meta.get("date") or "")),
                "date_dot": fmt_date(str(meta.get("date") or ""), "dot"),
                "date_latin": fmt_date(str(meta.get("date") or ""), "latin"),
                "year": str(meta.get("date") or "0000")[:4],
                "month": str(meta.get("date") or "0000-00")[5:7],
                "category": meta.get("category") or "札记",
                "category_slug": slugify(meta.get("category") or "札记"),
                "tags": meta.get("tags") or [],
                "summary": summary,
                "featured": bool(meta.get("featured")),
                "locked": locked,
                "password_hint": meta.get("password_hint", ""),
                "payload": payload,
                "cover": meta.get("cover", ""),
                "html": rendered_html,
                "toc": toc,
                "has_toc": bool(toc),
                "words": words,
                "minutes": minutes,
                "text": plain,
                "url": "/posts/%s/" % slug,
            }
            post["tag_links"] = [
                {"label": tag, "url": "/tags/%s/" % slugify(tag), "slug": slugify(tag)}
                for tag in post["tags"]
            ]
            post["payload_json"] = json.dumps(payload, ensure_ascii=False) if payload else ""
            post["mailto_subject"] = urllib.parse.quote("关于《%s》的留言" % post["title"])
            post["jsonld"] = json.dumps(
                {
                    "@context": "https://schema.org",
                    "@type": "BlogPosting",
                    "headline": post["title"],
                    "description": post["summary"],
                    "datePublished": post["date"],
                    "dateModified": post["date"],
                    "author": {"@type": "Person", "name": self.config["author"]["name"]},
                    "publisher": {"@type": "Organization", "name": self.config["title"]},
                    "mainEntityOfPage": self.base_url + post["url"],
                    "image": self.base_url + "/assets/img/og/%s.png" % slug,
                    "inLanguage": "zh-CN",
                    "wordCount": post["words"],
                    "articleSection": post["category"],
                    "keywords": ", ".join(post["tags"]),
                },
                ensure_ascii=False,
            )
            posts.append(post)

        posts.sort(key=lambda item: (item["date"], item["title"]), reverse=True)
        for index, post in enumerate(posts):
            post["index"] = index + 1
            post["number"] = roman(index + 1)
            newer = posts[index - 1] if index > 0 else None
            older = posts[index + 1] if index + 1 < len(posts) else None
            post["newer"] = newer
            post["older"] = older
            related = [other for other in posts if other["slug"] != post["slug"]]
            related.sort(
                key=lambda other: (
                    -len(set(other["tags"]) & set(post["tags"])),
                    other["category"] != post["category"],
                    other["date"],
                )
            )
            post["related"] = related[:3]
        return posts

    # -- context -------------------------------------------------------
    def nav_context(self, path):
        items = []
        for item in self.config.get("nav", []):
            url = item["url"]
            active = path == url or (url != "/" and path.startswith(url))
            items.append(dict(item, active=active))
        return items

    def base_context(self, title, description, path, section="", body_class="", **extra):
        if title:
            full_title = "%s · %s" % (title, self.config["title"])
        else:
            full_title = "%s · %s" % (self.config["title"], self.config.get("titleEn", ""))
        canonical = self.base_url + path
        comments = self.features.get("comments") or {}
        provider = comments.get("provider") or ""
        comments_enabled = bool(provider) and bool(comments.get("enabled", True))
        if provider == "giscus":
            comments_enabled = comments_enabled and bool((self.features.get("giscus") or {}).get("repo"))
        context = {
            "site": self.config,
            "nav": self.nav_context(path),
            "stats": self.stats,
            "year": self.build_stamp.year,
            "build": {
                "date": self.build_stamp.strftime("%Y-%m-%d"),
                "time": self.build_stamp.strftime("%H:%M"),
                "stamp": self.build_stamp.strftime("%Y%m%d%H%M"),
            },
            "page": {
                "title": full_title,
                "heading": title,
                "description": description or self.config.get("description", ""),
                "url": path,
                "canonical": canonical,
                "section": section,
                "bodyClass": body_class,
                "type": "website",
                "ogImage": self.base_url + "/assets/img/og-default.png",
                "date": self.build_stamp.strftime("%Y-%m-%d"),
            },
            "sections": self.sections,
            "features": self.features,
            "comments_enabled": comments_enabled,
            "comments_native": provider in ("netlify", "api"),
            "comments_giscus": provider == "giscus",
            "comments_config": json.dumps(
                {
                    "apiBase": comments.get("apiBase", "/api"),
                    "giscus": self.features.get("giscus", {}),
                },
                ensure_ascii=False,
            ),
        }
        context.update(extra)
        return context

    # -- rendering -----------------------------------------------------
    def render(self, template, context, out_rel):
        view = self.engine.render(template, context)
        document = self.engine.render("base.html", dict(context, view=view))
        write_text(os.path.join(self.out_dir, out_rel), document)
        return document

    def page(self, template, title, description, path, out_rel=None, section="", body_class="", **extra):
        context = self.base_context(title, description, path, section=section, body_class=body_class, **extra)
        out_rel = out_rel or (path.strip("/") + "/index.html" if path.strip("/") else "index.html")
        return self.render(template, context, out_rel)

    # -- chunks --------------------------------------------------------
    def post_card(self, post, variant="row", numeral=None):
        context = self.base_context(post["title"], post["summary"], post["url"])
        context.update({"post": post, "variant": variant, "numeral": numeral or post["number"]})
        return self.engine.render("partials/post-card.html", context)

    def build(self):
        self.load()
        if os.path.isdir(self.out_dir):
            shutil.rmtree(self.out_dir)
        os.makedirs(self.out_dir, exist_ok=True)

        self._copy_assets()
        self._build_og_images()
        self._build_home()
        self._build_posts()
        self._build_taxonomy()
        self._build_archive()
        self._build_notes()
        self._build_collection()
        self._build_projects()
        self._build_friends()
        self._build_about()
        self._build_locked()
        self._build_guestbook()
        self._build_admin()
        self._build_search_page()
        self._build_404()
        self._build_feeds()
        self._build_manifest()
        print("\n饮冰室 · build complete → %s" % self.out_dir)

    def _copy_assets(self):
        target = os.path.join(self.out_dir, "assets")
        if os.path.isdir(ASSETS_DIR):
            shutil.copytree(ASSETS_DIR, target, dirs_exist_ok=True)
        write_text(os.path.join(self.out_dir, ".nojekyll"), "")

    # -- pages ---------------------------------------------------------
    def _build_home(self):
        featured = [post for post in self.posts if post["featured"]][:2]
        if len(featured) < 2:
            featured = self.posts[:2]
        latest = self.posts[:6]
        notes = self.notes[:4]
        top_collection = sorted(
            [item for item in self.collection if item.get("score")],
            key=lambda item: item.get("score") or 0,
            reverse=True,
        )[:4]
        featured_projects = [item for item in self.projects if item.get("featured")][:3] or self.projects[:3]

        cards = "".join(self.post_card(post, "plate") for post in featured)
        rows = "".join(self.post_card(post, "row") for post in latest)
        note_items = "".join(
            self.engine.render(
                "partials/note-line.html",
                dict(self.base_context("", "", "/notes/"), note=note),
            )
            for note in notes
        )

        context_extra = {
            "featured_html": cards,
            "latest_html": rows,
            "notes_html": note_items,
            "top_collection": top_collection,
            "featured_projects": featured_projects,
            "today": self._today(),
            "epigraph": {
                "text": self.config.get("motto", ""),
                "note": self.config.get("mottoSource", ""),
            },
        }
        self.page(
            "home.html",
            "",
            self.config.get("description", ""),
            "/",
            out_rel="index.html",
            section="home",
            body_class="page-home",
            **context_extra
        )

    def _today(self):
        day = self.build_stamp
        return {
            "cn": "%d年%d月%d日" % (day.year, day.month, day.day),
            "weekday": WEEKDAYS[day.weekday()],
            "latin": fmt_date(day.strftime("%Y-%m-%d"), "latin"),
            "iso": day.strftime("%Y-%m-%d"),
        }

    def _build_posts(self):
        section = self.sections.get("posts", {})
        groups, current_year = [], None
        for post in self.posts:
            if post["year"] != current_year:
                current_year = post["year"]
                groups.append({"year": current_year, "posts": []})
            groups[-1]["posts"].append(post)

        for group in groups:
            group["html"] = "".join(self.post_card(post, "row") for post in group["posts"])
            group["count"] = len(group["posts"])

        self.page(
            "posts.html",
            section.get("title", "文章"),
            "全部文章，按年月排布。",
            "/posts/",
            section="posts",
            body_class="page-posts",
            groups=groups,
            posts=self.posts,
            epigraph={"text": section.get("epigraph", ""), "note": section.get("epigraphNote", "")},
        )

        for post in self.posts:
            self._build_post(post)

    def _build_post(self, post):
        toc_html = self.engine.render(
            "partials/toc.html",
            dict(self.base_context("", "", post["url"]), post=post),
        )
        context = self.base_context(
            post["title"],
            post["summary"],
            post["url"],
            section="posts",
            body_class="page-post",
        )
        context.update(
            {
                "post": post,
                "toc_html": toc_html,
                "content_html": post["html"],
                "epigraph": None,
            }
        )
        context["page"]["type"] = "article"
        og_file = os.path.join(self.out_dir, "assets", "img", "og", "%s.png" % post["slug"])
        if os.path.isfile(og_file):
            context["page"]["ogImage"] = self.base_url + "/assets/img/og/%s.png" % post["slug"]
        view = self.engine.render("post.html", context)
        document = self.engine.render("base.html", dict(context, view=view))
        write_text(os.path.join(self.out_dir, "posts", post["slug"], "index.html"), document)

    def _build_taxonomy(self):
        tag_list = [
            {"label": tag, "slug": slugify(tag), "count": len(items), "posts": items}
            for tag, items in sorted(self.tags.items(), key=lambda pair: (-len(pair[1]), pair[0]))
        ]
        self.page(
            "tags.html",
            "标签",
            "全部标签，按文章数量排列。",
            "/tags/",
            section="tags",
            body_class="page-tags",
            tag_list=tag_list,
            epigraph={"text": self.sections.get("tags", {}).get("epigraph", ""), "note": self.sections.get("tags", {}).get("epigraphNote", "")},
        )

        for entry in tag_list:
            items = entry["posts"]
            self.page(
                "tag.html",
                entry["label"],
                "标签「%s」下的 %d 篇文章。" % (entry["label"], len(items)),
                "/tags/%s/" % entry["slug"],
                section="tags",
                body_class="page-tag",
                tag=entry,
                posts=items,
                html="".join(self.post_card(post, "row") for post in items),
            )

        category_list = [
            {"label": name, "slug": slugify(name), "count": len(items), "posts": items}
            for name, items in sorted(self.categories.items(), key=lambda pair: -len(pair[1]))
        ]
        self.page(
            "categories.html",
            "分类",
            "按栏目归档的全部文章。",
            "/categories/",
            section="posts",
            body_class="page-categories",
            category_list=category_list,
        )
        for entry in category_list:
            self.page(
                "tag.html",
                entry["label"],
                "分类「%s」下的 %d 篇文章。" % (entry["label"], entry["count"]),
                "/categories/%s/" % entry["slug"],
                section="posts",
                body_class="page-tag",
                tag=entry,
                posts=entry["posts"],
                html="".join(self.post_card(post, "row") for post in entry["posts"]),
            )

    def _build_archive(self):
        counts = {}
        for post in self.posts:
            counts[post["year"]] = counts.get(post["year"], 0) + 1
        years = [
            {"year": year, "count": count, "posts": [post for post in self.posts if post["year"] == year]}
            for year, count in sorted(counts.items(), reverse=True)
        ]
        for year in years:
            year["rows"] = "".join(
                '<li class="archive-row"><a href="%s"><span class="archive-date">%s</span>'
                '<span class="archive-title">%s</span><span class="archive-cat">%s</span></a></li>'
                % (post["url"], post["date_dot"][5:], post["title"], post["category"])
                for post in year["posts"]
            )
        self.page(
            "archive.html",
            "归档",
            "按年份排好的全部文章。",
            "/archive/",
            section="posts",
            body_class="page-archive",
            years=years,
            total=len(self.posts),
            epigraph={"text": self.sections.get("archive", {}).get("epigraph", ""), "note": self.sections.get("archive", {}).get("epigraphNote", "")},
        )

    def _build_notes(self):
        month_groups, key = [], None
        for note in self.notes:
            stamp = "%s.%s" % (note["year"], note["month"])
            if stamp != key:
                key = stamp
                month_groups.append({"stamp": stamp, "notes": []})
            month_groups[-1]["notes"].append(note)

        for group in month_groups:
            group["html"] = "".join(
                self.engine.render(
                    "partials/note-line.html",
                    dict(self.base_context("", "", "/notes/"), note=note),
                )
                for note in group["notes"]
            )
            group["count"] = len(group["notes"])

        all_tags = sorted({tag for note in self.notes for tag in note.get("tags", [])})
        self.page(
            "notes.html",
            "碎碎念",
            "比文章轻一点的记录：一句话、一个念头、一小段今天的心情。",
            "/notes/",
            section="notes",
            body_class="page-notes",
            month_groups=month_groups,
            note_tags=[{"label": tag, "count": sum(1 for note in self.notes if tag in note.get("tags", []))} for tag in all_tags],
            total=len(self.notes),
            epigraph={"text": self.sections.get("notes", {}).get("epigraph", ""), "note": self.sections.get("notes", {}).get("epigraphNote", "")},
        )

    def _build_collection(self):
        labels = {"anime": "番剧", "film": "电影", "book": "书"}
        counts = {key: sum(1 for item in self.collection if item.get("type") == key) for key in labels}
        for item in self.collection:
            item["type_label"] = labels.get(item.get("type"), "其他")
            item["score_text"] = ("%.1f" % item["score"]) if item.get("score") else "—"
        ordered = sorted(
            self.collection,
            key=lambda item: (labels.get(item.get("type"), "z"), -(item.get("score") or 0), item.get("year") or 0),
        )
        self.page(
            "collection.html",
            "收藏",
            "书、影、番的一张清单。",
            "/collection/",
            section="collection",
            body_class="page-collection",
            items=ordered,
            labels=labels,
            counts=counts,
            total=len(self.collection),
            epigraph={"text": self.sections.get("collection", {}).get("epigraph", ""), "note": self.sections.get("collection", {}).get("epigraphNote", "")},
        )

    def _build_projects(self):
        self.page(
            "projects.html",
            "作品",
            "做出来的一些东西：工具、实验、小玩意。",
            "/projects/",
            section="projects",
            body_class="page-projects",
            items=self.projects,
            total=len(self.projects),
            epigraph={"text": self.sections.get("projects", {}).get("epigraph", ""), "note": self.sections.get("projects", {}).get("epigraphNote", "")},
        )

    def _build_friends(self):
        self.page(
            "friends.html",
            "友链",
            "常去的一些地方。",
            "/friends/",
            section="friends",
            body_class="page-friends",
            items=self.friends,
            total=len(self.friends),
            epigraph={"text": self.sections.get("friends", {}).get("epigraph", ""), "note": self.sections.get("friends", {}).get("epigraphNote", "")},
        )

    def _build_about(self):
        about = dict(self.about)
        timeline = about.get("timeline", [])
        years = {}
        for entry in timeline:
            years.setdefault(entry.get("year", ""), []).append(entry)
        about["timeline_groups"] = [
            {"year": year, "entries": entries} for year, entries in sorted(years.items(), reverse=True)
        ]
        self.page(
            "about.html",
            "关于",
            "这间屋子的主人，和这间屋子是怎么来的。",
            "/about/",
            section="about",
            body_class="page-about",
            about=about,
            epigraph={"text": self.sections.get("about", {}).get("epigraph", ""), "note": self.sections.get("about", {}).get("epigraphNote", "")},
        )

    def _build_locked(self):
        locked = [post for post in self.posts if post["locked"]]
        self.page(
            "locked.html",
            "私密",
            "需要口令才能读的文章。",
            "/locked/",
            section="locked",
            body_class="page-locked",
            posts=locked,
            total=len(locked),
            html="".join(self.post_card(post, "row") for post in locked),
            epigraph={"text": self.sections.get("locked", {}).get("epigraph", ""), "note": self.sections.get("locked", {}).get("epigraphNote", "")},
        )

    def _build_guestbook(self):
        self.page(
            "guestbook.html",
            "留言",
            "在门楣上写几个字。",
            "/guestbook/",
            section="guestbook",
            body_class="page-guestbook",
            seed=self.guestbook,
            total=len(self.guestbook),
            epigraph={"text": self.sections.get("guestbook", {}).get("epigraph", ""), "note": self.sections.get("guestbook", {}).get("epigraphNote", "")},
        )

    def _build_search_page(self):
        self.page(
            "search.html",
            "检索",
            "在整间屋子里找一句话。",
            "/search/",
            section="search",
            body_class="page-search",
            total=len(self.posts) + len(self.notes) + len(self.collection) + len(self.projects),
        )

    def _build_admin(self):
        context = self.base_context(
            "评论管理",
            "屋主专用：管理文章评论。",
            "/admin/comments/",
            section="admin",
            body_class="page-admin",
        )
        context["page"]["noindex"] = True
        context["page"]["adminScript"] = True
        view = self.engine.render("admin-comments.html", context)
        document = self.engine.render("base.html", dict(context, view=view))
        write_text(os.path.join(self.out_dir, "admin", "comments", "index.html"), document)

    def _build_404(self):
        context = self.base_context("未找到", "这一页不在屋子里。", "/404.html", section="404", body_class="page-404")
        view = self.engine.render("404.html", context)
        document = self.engine.render("base.html", dict(context, view=view))
        write_text(os.path.join(self.out_dir, "404.html"), document)

    def _build_feeds(self):
        self._write_search_index()
        self._write_rss()
        self._write_sitemap()
        self._write_robots()

    def _write_search_index(self):
        entries = []
        for post in self.posts:
            entries.append(
                {
                    "kind": "post",
                    "title": post["title"],
                    "url": post["url"],
                    "date": post["date"],
                    "tags": post["tags"],
                    "summary": post["summary"],
                    "body": "" if post["locked"] else post["text"][:2400],
                    "locked": post["locked"],
                }
            )
        for note in self.notes:
            entries.append(
                {
                    "kind": "note",
                    "title": note.get("date_cn", ""),
                    "url": "/notes/#" + note["id"],
                    "date": note.get("date", ""),
                    "tags": note.get("tags", []),
                    "summary": note.get("text", ""),
                    "body": note.get("text", ""),
                }
            )
        for item in self.collection:
            entries.append(
                {
                    "kind": "collection",
                    "title": item.get("title", ""),
                    "url": "/collection/#" + item["anchor"],
                    "date": "",
                    "tags": item.get("tags", []),
                    "summary": item.get("note", ""),
                    "body": "%s %s" % (item.get("title", ""), item.get("note", "")),
                }
            )
        for item in self.projects:
            entries.append(
                {
                    "kind": "project",
                    "title": item.get("title", ""),
                    "url": "/projects/#" + item["anchor"],
                    "date": "",
                    "tags": item.get("stack", []),
                    "summary": item.get("summary", ""),
                    "body": "%s %s %s" % (item.get("title", ""), item.get("subtitle", ""), item.get("summary", "")),
                }
            )
        pages = [
            ("文章", "/posts/", "全部文章"),
            ("碎碎念", "/notes/", "短记录"),
            ("收藏", "/collection/", "书影音"),
            ("作品", "/projects/", "项目"),
            ("友链", "/friends/", "常去的地方"),
            ("关于", "/about/", "关于这里"),
            ("私密", "/locked/", "需要口令的文章"),
            ("留言", "/guestbook/", "留言板"),
            ("归档", "/archive/", "按年份"),
            ("标签", "/tags/", "全部标签"),
        ]
        for label, url, summary in pages:
            entries.append({"kind": "page", "title": label, "url": url, "date": "", "tags": [], "summary": summary, "body": summary})
        write_text(
            os.path.join(self.out_dir, "assets", "data", "search.json"),
            json.dumps(entries, ensure_ascii=False, separators=(",", ":")),
        )

    def _write_rss(self):
        items = []
        for post in self.posts[:20]:
            description = post["summary"] if post["locked"] else post["html"][:4000]
            items.append(
                """    <item>
      <title>%s</title>
      <link>%s</link>
      <guid isPermaLink="true">%s</guid>
      <pubDate>%s</pubDate>
      <category>%s</category>
      <description>%s</description>
    </item>"""
                % (
                    html.escape(post["title"]),
                    self.base_url + post["url"],
                    self.base_url + post["url"],
                    self._rfc822(post["date"]),
                    html.escape(post["category"]),
                    html.escape(description),
                )
            )
        feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>%s</title>
    <link>%s</link>
    <description>%s</description>
    <language>zh-CN</language>
    <lastBuildDate>%s</lastBuildDate>
    <atom:link href="%s/feed.xml" rel="self" type="application/rss+xml"/>
%s
  </channel>
</rss>
""" % (
            html.escape(self.config["title"]),
            self.base_url,
            html.escape(self.config.get("description", "")),
            self._rfc822(self.build_stamp.strftime("%Y-%m-%d")),
            self.base_url,
            "\n".join(items),
        )
        write_text(os.path.join(self.out_dir, "feed.xml"), feed)
        write_text(os.path.join(self.out_dir, "rss.xml"), feed)

    def _rfc822(self, iso):
        try:
            day = datetime.strptime(iso[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            day = self.build_stamp
        return day.strftime("%a, %d %b %Y 00:00:00 +0800")

    def _write_sitemap(self):
        urls = ["/", "/posts/", "/notes/", "/collection/", "/projects/", "/friends/", "/about/",
                "/locked/", "/guestbook/", "/search/", "/archive/", "/tags/", "/categories/"]
        urls += [post["url"] for post in self.posts]
        urls += ["/tags/%s/" % slugify(tag) for tag in self.tags]
        urls += ["/categories/%s/" % slugify(cat) for cat in self.categories]
        rows = []
        for url in urls:
            rows.append(
                "  <url><loc>%s</loc><lastmod>%s</lastmod></url>"
                % (self.base_url + url, self.stats["updated"] or self.build_stamp.strftime("%Y-%m-%d"))
            )
        write_text(
            os.path.join(self.out_dir, "sitemap.xml"),
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n'
            % "\n".join(rows),
        )

    def _write_robots(self):
        write_text(
            os.path.join(self.out_dir, "robots.txt"),
            "User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: %s/sitemap.xml\n" % self.base_url,
        )
        # CNAME 只对 GitHub Pages 有意义；用 netlify.app 之类的默认域名时不写
        if not self.config["domain"].endswith(".netlify.app"):
            write_text(os.path.join(self.out_dir, "CNAME"), self.config["domain"] + "\n")

    def _build_manifest(self):
        icons = [
            {"src": "/assets/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/assets/img/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ]
        manifest = {
            "name": "%s · %s" % (self.config["title"], self.config["titleEn"]),
            "short_name": self.config["title"],
            "description": self.config.get("description", ""),
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#f2e8d5",
            "theme_color": "#f2e8d5",
            "lang": "zh-CN",
            "icons": icons,
        }
        write_text(os.path.join(self.out_dir, "manifest.webmanifest"), json.dumps(manifest, ensure_ascii=False, indent=2))
        self._write_service_worker()

    def _write_service_worker(self):
        version = self.build_stamp.strftime("%Y%m%d%H%M")
        worker = """/* 饮冰室 service worker — generated at build time */
const VERSION = '%s';
const SHELL = 'icing-shell-' + VERSION;
const PRECACHE = [
  '/', '/posts/', '/notes/', '/collection/', '/projects/', '/friends/', '/about/',
  '/assets/css/fonts.css', '/assets/css/site.css', '/assets/js/site.js', '/assets/js/unlock.js',
  '/assets/js/comments.js',
  '/assets/data/search.json', '/manifest.webmanifest'
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => Promise.all(
    PRECACHE.map((url) => cache.add(new Request(url, { cache: 'reload' })).catch(() => null))
  )).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(
    keys.filter((key) => key !== SHELL).map((key) => caches.delete(key))
  )).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET' || !request.url.startsWith(self.location.origin)) return;
  const url = new URL(request.url);
  const isAsset = url.pathname.startsWith('/assets/');
  if (isAsset) {
    event.respondWith(caches.match(request).then((hit) => hit || fetch(request).then((response) => {
      const copy = response.clone();
      caches.open(SHELL).then((cache) => cache.put(request, copy));
      return response;
    })));
    return;
  }
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).then((response) => {
      const copy = response.clone();
      caches.open(SHELL).then((cache) => cache.put(request, copy));
      return response;
    }).catch(() => caches.match(request).then((hit) => hit || caches.match('/'))));
  }
});
""" % version
        write_text(os.path.join(self.out_dir, "sw.js"), worker)

    # -- images --------------------------------------------------------
    def _build_og_images(self):
        if not self.config.get("build", {}).get("ogImages", True):
            return
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            self.warnings.append(
                "没装 Pillow，跳过每篇文章的分享图（不影响网站）。"
                "想要的话运行：python -m pip install pillow"
            )
            return

        font_candidates = [
            r"C:\Windows\Fonts\STSONG.TTF",
            r"C:\Windows\Fonts\simsun.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        ]
        font_path = next((path for path in font_candidates if os.path.isfile(path)), None)
        if not font_path:
            self.warnings.append("no CJK font found — skipping OG images")
            return

        def font(size):
            return ImageFont.truetype(font_path, size)

        paper, ink, gold, rust = (242, 232, 213), (36, 28, 21), (168, 133, 63), (140, 47, 32)
        os.makedirs(os.path.join(self.out_dir, "assets", "img", "og"), exist_ok=True)

        def draw_card(title, kicker, footer, filename, big=False):
            width, height = (1200, 630)
            image = Image.new("RGB", (width, height), paper)
            draw = ImageDraw.Draw(image)
            draw.rectangle([28, 28, width - 29, height - 29], outline=ink, width=2)
            draw.rectangle([38, 38, width - 39, height - 39], outline=gold, width=1)
            draw.text((70, 74), kicker.upper(), font=font(24), fill=rust)
            draw.line([(70, 120), (width - 70, 120)], fill=gold, width=1)

            if big:
                # 右侧画一个印章式的圆环，把空白填起来
                center_x, center_y, radius = 960, 250, 118
                draw.ellipse(
                    [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                    outline=rust,
                    width=3,
                )
                inner = radius - 12
                draw.ellipse(
                    [center_x - inner, center_y - inner, center_x + inner, center_y + inner],
                    outline=gold,
                    width=1,
                )
                glyph = font(112)
                box = draw.textbbox((0, 0), "冰", font=glyph)
                draw.text(
                    (center_x - (box[2] - box[0]) / 2 - box[0], center_y - (box[3] - box[1]) / 2 - box[1]),
                    "冰",
                    font=glyph,
                    fill=rust,
                )

            title_font = font(96 if big else 58)
            max_width = (width - 300) if big else (width - 190)
            lines, current = [], ""
            for char in title:
                if draw.textlength(current + char, font=title_font) > max_width:
                    lines.append(current)
                    current = char
                else:
                    current += char
            lines.append(current)
            lines = lines[:4]
            y = 200 if big else 190
            for line in lines:
                draw.text((70, y), line, font=title_font, fill=ink)
                y += int(title_font.size * 1.28)

            draw.line([(70, height - 118), (150, height - 118)], fill=rust, width=3)
            draw.text((70, height - 100), footer, font=font(26), fill=(107, 91, 74))
            draw.text((width - 250, height - 100), "muzetr.com", font=font(26), fill=gold)
            image.save(os.path.join(self.out_dir, "assets", "img", "og", filename), optimize=True)

        draw_card(
            self.config["title"],
            self.config.get("titleEn", ""),
            self.config.get("motto", ""),
            "../og-default.png",
            big=True,
        )

        for post in self.posts:
            draw_card(post["title"], post["category"], post["date_cn"], "%s.png" % post["slug"])

        # app icons: a wax-seal style square
        for size in (192, 512):
            image = Image.new("RGB", (size, size), (36, 28, 21))
            draw = ImageDraw.Draw(image)
            draw.rectangle([size * 0.06, size * 0.06, size * 0.94, size * 0.94], outline=(201, 162, 91), width=max(2, size // 64))
            glyph = font(int(size * 0.52))
            text = "冰"
            box = draw.textbbox((0, 0), text, font=glyph)
            draw.text(
                ((size - (box[2] - box[0])) / 2 - box[0], (size - (box[3] - box[1])) / 2 - box[1]),
                text,
                font=glyph,
                fill=(242, 232, 213),
            )
            image.save(os.path.join(self.out_dir, "assets", "img", "icon-%d.png" % size), optimize=True)

    # -- report --------------------------------------------------------
    def report(self):
        total_bytes = 0
        pages = 0
        for root, _dirs, files in os.walk(self.out_dir):
            for name in files:
                total_bytes += os.path.getsize(os.path.join(root, name))
                if name.endswith(".html"):
                    pages += 1
        print("  页面 %d · 文章 %d · 碎碎念 %d · 收藏 %d · 作品 %d · 标签 %d"
              % (pages, self.stats["posts"], self.stats["notes"], self.stats["collection"], self.stats["projects"], self.stats["tags"]))
        print("  产物 %.1f MB" % (total_bytes / 1024.0 / 1024.0))
        if self.warnings:
            print("  提醒：")
            for warning in self.warnings:
                print("   - " + warning)


def main():
    setup_console()
    with open(os.path.join(ROOT, "site.config.json"), "r", encoding="utf-8") as handle:
        config = json.load(handle)
    if "--clean" in sys.argv:
        out = os.path.join(ROOT, config.get("build", {}).get("out", "public"))
        if os.path.isdir(out):
            shutil.rmtree(out)
    site = Site(config)
    site.build()
    site.report()


if __name__ == "__main__":
    main()
