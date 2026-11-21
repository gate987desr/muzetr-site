"""Dependency-free Markdown renderer tuned for the 饮冰室 site.

Supported: ATX headings, paragraphs, emphasis, inline code, links, images with
captions, bullet/ordered lists (nested), block quotes, callouts, fenced code
with lightweight highlighting, tables, horizontal rules, raw HTML blocks.

Everything is escaped; only the whitelisted constructs above produce markup.
"""

from __future__ import annotations

import html
import re

# --------------------------------------------------------------------------
# front matter
# --------------------------------------------------------------------------

_KEY_RE = re.compile(r"^([A-Za-z_][\w\-]*)\s*:\s*(.*)$")


def _parse_scalar(raw):
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in _split_list(inner)]
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    lowered = raw.lower()
    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    if lowered in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if re.fullmatch(r"-?\d+\.\d+", raw):
        return float(raw)
    return raw


def _split_list(inner):
    parts, buf, quote = [], [], None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == ",":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def split_front_matter(text):
    """Return (meta dict, body). Body keeps its original line endings."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    end = None
    for index in range(1, min(len(lines), 200)):
        if lines[index].strip() in ("---", "..."):
            end = index
            break
    if end is None:
        return {}, text
    meta = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _KEY_RE.match(line)
        if match:
            meta[match.group(1)] = _parse_scalar(match.group(2))
    return meta, "\n".join(lines[end + 1:]).lstrip("\n")


# --------------------------------------------------------------------------
# inline
# --------------------------------------------------------------------------

_CODE_TOKEN = "\x02%d\x03"

INLINE_RULES = [
    (re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"']([^\"']*)[\"'])?\)"), "image"),
    (re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+[\"']([^\"']*)[\"'])?\)"), "link"),
    (re.compile(r"\*\*([^*]+)\*\*"), "strong"),
    (re.compile(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])"), "em"),
    (re.compile(r"~~([^~]+)~~"), "del"),
]


def _is_external(url):
    return bool(re.match(r"^https?://", url, re.I))


def render_inline(text, site_host=""):
    """Render inline markdown. `text` must already have HTML escaped."""
    placeholders = []

    def stash(fragment):
        placeholders.append(fragment)
        return _CODE_TOKEN % (len(placeholders) - 1)

    # inline code first, so its contents are never touched again
    text = re.sub(
        r"`([^`\n]+)`",
        lambda m: stash('<code class="code-inline">%s</code>' % m.group(1)),
        text,
    )

    for pattern, kind in INLINE_RULES:
        def repl(match, kind=kind):
            if kind == "image":
                alt, src, title = match.group(1), match.group(2), match.group(3)
                img = '<img src="%s" alt="%s" loading="lazy" decoding="async">' % (src, alt)
                if title:
                    return stash(
                        '<figure class="plate"><div class="plate-frame">%s</div>'
                        '<figcaption>%s</figcaption></figure>' % (img, title)
                    )
                return stash(img)
            if kind == "link":
                label, href, title = match.group(1), match.group(2), match.group(3)
                attrs = ' href="%s"' % href
                if title:
                    attrs += ' title="%s"' % title
                if _is_external(href) and site_host and site_host not in href:
                    attrs += ' target="_blank" rel="noopener noreferrer"'
                return stash("<a%s>%s</a>" % (attrs, label))
            if kind == "strong":
                return stash("<strong>%s</strong>" % match.group(1))
            if kind == "em":
                return stash("<em>%s</em>" % match.group(1))
            if kind == "del":
                return stash("<del>%s</del>" % match.group(1))
            return match.group(0)

        text = pattern.sub(repl, text)

    text = text.replace("\\*", "*").replace("\\_", "_")

    for index, fragment in enumerate(placeholders):
        text = text.replace(_CODE_TOKEN % index, fragment)
    return text


# --------------------------------------------------------------------------
# highlighting
# --------------------------------------------------------------------------

KEYWORDS = {
    "python": (
        "and as assert async await break class continue def del elif else except "
        "finally for from global if import in is lambda nonlocal not or pass raise "
        "return try while with yield match case"
    ),
    "js": (
        "const let var function return if else for while do switch case break continue "
        "new class extends import from export default await async try catch finally throw "
        "typeof instanceof in of this super null undefined true false"
    ),
    "bash": "if then else elif fi for while do done case esac function return export local in",
    "sql": "select from where group by order limit join left right inner outer on as insert update delete into values create table index",
}

PY_BUILTINS = "print len range str int dict list set tuple enumerate zip open sorted sum min max type isinstance super self None True False"


def _tokenizer(lang):
    """Return a compiled regex whose named groups are token classes, or None."""
    lang = (lang or "").lower()
    if lang in ("python", "py"):
        return re.compile(
            r"(?P<str>\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')"
            r"|(?P<com>#[^\n]*)"
            r"|(?P<dec>@[\w.]+)"
            r"|(?P<num>\b\d+(?:\.\d+)?\b)"
            r"|(?P<kw>\b(?:%s)\b)" % KEYWORDS["python"]
            + r"|(?P<bi>\b(?:%s)\b)" % PY_BUILTINS
            + r"|(?P<fn>\b[A-Za-z_]\w*(?=\())"
        )
    if lang in ("js", "javascript", "ts", "typescript", "json"):
        return re.compile(
            r"(?P<str>`(?:\\.|[^`\\])*`|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')"
            r"|(?P<com>//[^\n]*|/\*[\s\S]*?\*/)"
            r"|(?P<num>\b\d+(?:\.\d+)?\b)"
            r"|(?P<kw>\b(?:%s)\b)" % KEYWORDS["js"]
            + r"|(?P<fn>\b[A-Za-z_$][\w$]*(?=\())"
        )
    if lang in ("bash", "sh", "shell", "zsh", "console"):
        return re.compile(
            r"(?P<str>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')"
            r"|(?P<com>#[^\n]*)"
            r"|(?P<num>\b\d+\b)"
            r"|(?P<kw>\b(?:%s)\b)" % KEYWORDS["bash"]
            + r"|(?P<var>\$\{?\w+\}?)"
        )
    if lang in ("html", "xml", "svg"):
        return re.compile(r"(?P<com><!--[\s\S]*?-->)|(?P<tag></?[\w:-]+)|(?P<attr>\s[\w:-]+=)|(?P<str>\"[^\"]*\")")
    if lang in ("css", "scss"):
        return re.compile(r"(?P<com>/\*[\s\S]*?\*/)|(?P<str>\"[^\"]*\"|'[^']*')|(?P<num>#[0-9a-fA-F]{3,8}\b|\b\d+(?:\.\d+)?(?:px|rem|em|%|s|ms)?\b)|(?P<kw>[a-z-]+(?=\s*:))")
    if lang == "sql":
        return re.compile(r"(?P<str>'[^']*')|(?P<com>--[^\n]*)|(?P<num>\b\d+\b)|(?P<kw>\b(?:%s)\b)" % KEYWORDS["sql"])
    return None


TOKEN_CLASS = {
    "str": "t-str",
    "com": "t-com",
    "num": "t-num",
    "kw": "t-kw",
    "bi": "t-bi",
    "fn": "t-fn",
    "dec": "t-dec",
    "var": "t-var",
    "tag": "t-tag",
    "attr": "t-attr",
}


def highlight(code, lang):
    tokenizer = _tokenizer(lang)
    if not tokenizer:
        return html.escape(code, quote=False)

    out, pos = [], 0
    for match in tokenizer.finditer(code):
        if match.start() > pos:
            out.append(html.escape(code[pos:match.start()], quote=False))
        kind = match.lastgroup
        cls = TOKEN_CLASS.get(kind, "t-kw")
        out.append('<span class="%s">%s</span>' % (cls, html.escape(match.group(0), quote=False)))
        pos = match.end()
    out.append(html.escape(code[pos:], quote=False))
    return "".join(out)


# --------------------------------------------------------------------------
# blocks
# --------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^```\s*([\w+-]*)\s*$")
LIST_RE = re.compile(r"^(\s*)([-*+]|\d{1,3}[.)])\s+(.*)$")
HR_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?\s*$")
CALLOUT_RE = re.compile(r"^\[!(NOTE|TIP|WARNING|QUOTE|STUDY|DANGER)\]\s*(.*)$", re.I)
RAW_HTML_RE = re.compile(r"^\s*<(?:figure|div|section|aside|video|audio|iframe|picture|table|p|ul|ol|blockquote|hr|img|span|details|summary|script|style|br)\b", re.I)

CALLOUT_TITLES = {
    "note": "注",
    "tip": "诀",
    "warning": "诫",
    "quote": "引",
    "study": "考",
    "danger": "危",
}

LANG_LABELS = {
    "python": "Python",
    "py": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "bash": "Shell",
    "sh": "Shell",
    "shell": "Shell",
    "json": "JSON",
    "html": "HTML",
    "css": "CSS",
    "sql": "SQL",
    "text": "文本",
}


def slugify(text):
    plain = re.sub(r"[`*_~\[\]()]", "", text)
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", plain).strip("-").lower()
    return slug


class MarkdownRenderer:
    def __init__(self, site_host=""):
        self.site_host = site_host
        self.headings = []
        self._slug_counts = {}

    # -- helpers -------------------------------------------------------
    def _unique_slug(self, text):
        base = slugify(text) or "section"
        count = self._slug_counts.get(base, 0)
        self._slug_counts[base] = count + 1
        return base if count == 0 else "%s-%d" % (base, count + 1)

    def _inline(self, text):
        return render_inline(html.escape(text, quote=False), self.site_host)

    # -- entry ---------------------------------------------------------
    def render(self, text):
        self.headings = []
        self._slug_counts = {}
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        out = self._render_blocks(lines, top_level=True)
        return out

    def _render_blocks(self, lines, top_level=False):
        chunks, index = [], 0
        total = len(lines)
        while index < total:
            line = lines[index]
            stripped = line.strip()

            if not stripped:
                index += 1
                continue

            match = FENCE_RE.match(line)
            if match:
                lang = match.group(1)
                buffer = []
                index += 1
                while index < total and not lines[index].strip().startswith("```"):
                    buffer.append(lines[index])
                    index += 1
                index += 1  # closing fence
                code = "\n".join(buffer)
                label = lang or "text"
                shown = LANG_LABELS.get(label.lower(), label)
                chunks.append(
                    '<div class="code-block" data-lang="%s">'
                    '<div class="code-head"><span class="code-lang">%s</span></div>'
                    '<pre><code>%s</code></pre></div>'
                    % (html.escape(label), html.escape(shown), highlight(code, lang))
                )
                continue

            match = HEADING_RE.match(line)
            if match:
                level = len(match.group(1))
                raw = match.group(2)
                text_html = self._inline(raw)
                slug = self._unique_slug(raw)
                if level in (2, 3):
                    self.headings.append({"level": level, "text": re.sub(r"[`*_~]", "", raw), "id": slug})
                chunks.append('<h%d id="%s">%s</h%d>' % (level, slug, text_html, level))
                index += 1
                continue

            if HR_RE.match(line):
                chunks.append('<hr class="rule">')
                index += 1
                continue

            if line.lstrip().startswith(">"):
                block, index = self._collect_quote(lines, index)
                chunks.append(self._render_quote(block))
                continue

            if LIST_RE.match(line):
                block, index = self._collect_list(lines, index)
                chunks.append(self._render_list(block))
                continue

            if "|" in line and index + 1 < total and TABLE_SEP_RE.match(lines[index + 1]):
                block, index = self._collect_table(lines, index)
                chunks.append(self._render_table(block))
                continue

            if RAW_HTML_RE.match(line):
                buffer = []
                while index < total and lines[index].strip():
                    buffer.append(lines[index])
                    index += 1
                chunks.append("\n".join(buffer))
                continue

            paragraph, index = self._collect_paragraph(lines, index)
            chunks.append(self._render_paragraph(paragraph))

        return "\n".join(chunk for chunk in chunks if chunk)

    def _collect_quote(self, lines, index):
        buffer = []
        while index < len(lines) and lines[index].lstrip().startswith(">"):
            raw = lines[index].lstrip()[1:]
            buffer.append(raw[1:] if raw.startswith(" ") else raw)
            index += 1
        return buffer, index

    def _render_quote(self, lines):
        if not lines:
            return ""
        callout = CALLOUT_RE.match(lines[0].strip())
        if callout:
            kind = callout.group(1).lower()
            title = callout.group(2).strip() or CALLOUT_TITLES.get(kind, kind)
            body = self._render_blocks(lines[1:])
            return (
                '<aside class="callout callout-%s"><p class="callout-title">'
                '<span class="callout-mark" aria-hidden="true">%s</span>%s</p>'
                '<div class="callout-body">%s</div></aside>'
                % (kind, "※", self._inline(title), body)
            )
        body = self._render_blocks(lines)
        return '<blockquote class="quote">%s</blockquote>' % body

    def _collect_list(self, lines, index):
        start = index
        base_indent = len(LIST_RE.match(lines[index]).group(1).expandtabs(4))
        buffer = []
        while index < len(lines):
            line = lines[index]
            if not line.strip():
                # allow a blank line only if the list continues
                lookahead = index + 1
                while lookahead < len(lines) and not lines[lookahead].strip():
                    lookahead += 1
                if lookahead < len(lines):
                    nxt = lines[lookahead]
                    match = LIST_RE.match(nxt)
                    if match and len(match.group(1).expandtabs(4)) >= base_indent:
                        buffer.append("")
                        index = lookahead
                        continue
                break
            match = LIST_RE.match(line)
            indent = len(line) - len(line.lstrip())
            if match:
                buffer.append(line)
                index += 1
                continue
            if indent > base_indent:
                buffer.append(line)
                index += 1
                continue
            break
        del start
        return buffer, index

    def _render_list(self, lines):
        if not lines:
            return ""
        first = LIST_RE.match(lines[0])
        base_indent = len(first.group(1).expandtabs(4))
        ordered = bool(re.match(r"\d", first.group(2)))
        items, current = [], None

        for line in lines:
            match = LIST_RE.match(line)
            indent = len(line) - len(line.lstrip()) if line.strip() else 0
            if match and len(match.group(1).expandtabs(4)) == base_indent and (bool(re.match(r"\d", match.group(2))) == ordered or not items):
                if current is not None:
                    items.append(current)
                current = [match.group(3)]
            elif current is not None:
                if not line.strip():
                    current.append("")
                else:
                    strip_n = min(len(line) - len(line.lstrip()), base_indent + 2)
                    current.append(line[strip_n:])
        if current is not None:
            items.append(current)

        rendered = []
        for item in items:
            tight = "" not in item[:-1]
            body_lines = item
            body = self._render_blocks(body_lines)
            if tight:
                body = re.sub(r"^<p>(.*?)</p>", r"\1", body.strip(), count=1, flags=re.S)
            rendered.append("<li>%s</li>" % body.strip())

        tag = "ol" if ordered else "ul"
        start_attr = ""
        if ordered:
            start_match = re.match(r"(\d+)", first.group(2))
            if start_match and start_match.group(1) != "1":
                start_attr = ' start="%s"' % start_match.group(1)
        return "<%s%s>\n%s\n</%s>" % (tag, start_attr, "\n".join(rendered), tag)

    def _collect_table(self, lines, index):
        buffer = [lines[index], lines[index + 1]]
        index += 2
        while index < len(lines) and lines[index].strip() and "|" in lines[index]:
            buffer.append(lines[index])
            index += 1
        return buffer, index

    def _render_table(self, lines):
        def cells(row):
            row = row.strip().strip("|")
            return [cell.strip() for cell in re.split(r"(?<!\\)\|", row)]

        header = cells(lines[0])
        aligns = []
        for spec in cells(lines[1]):
            spec = spec.strip()
            if spec.startswith(":") and spec.endswith(":"):
                aligns.append("center")
            elif spec.endswith(":"):
                aligns.append("right")
            else:
                aligns.append("left")

        def row_html(row_cells, tag):
            out = []
            for position, cell in enumerate(row_cells):
                align = aligns[position] if position < len(aligns) else "left"
                out.append('<%s style="text-align:%s">%s</%s>' % (tag, align, self._inline(cell), tag))
            return "<tr>%s</tr>" % "".join(out)

        head = "<thead>%s</thead>" % row_html(header, "th")
        body_rows = [row_html(cells(line), "td") for line in lines[2:]]
        body = "<tbody>%s</tbody>" % "".join(body_rows) if body_rows else ""
        return '<div class="table-wrap"><table class="table">%s%s</table></div>' % (head, body)

    def _collect_paragraph(self, lines, index):
        buffer = []
        while index < len(lines):
            line = lines[index]
            if not line.strip():
                break
            if FENCE_RE.match(line) or HEADING_RE.match(line) or HR_RE.match(line):
                break
            if line.lstrip().startswith(">") or LIST_RE.match(line):
                break
            if RAW_HTML_RE.match(line):
                break
            if "|" in line and index + 1 < len(lines) and TABLE_SEP_RE.match(lines[index + 1]):
                break
            buffer.append(line)
            index += 1
        return buffer, index

    def _render_paragraph(self, lines):
        hard_break = "  "
        parts = []
        for line in lines:
            if line.endswith(hard_break) or line.rstrip().endswith("\\"):
                parts.append(self._inline(line.rstrip().rstrip("\\")))
                parts.append("<br>")
            else:
                parts.append(self._inline(line.strip()))
        joined = " ".join(parts).replace("<br> ", "<br>").replace(" <br>", "<br>")
        return "<p>%s</p>" % joined


def render(text, site_host=""):
    renderer = MarkdownRenderer(site_host=site_host)
    body = renderer.render(text)
    plain = re.sub(r"<[^>]+>", "", body)
    plain = html.unescape(re.sub(r"\s+", " ", plain)).strip()
    lang_chars = len(re.findall(r"[\u4e00-\u9fff]", plain))
    latin_words = len(re.findall(r"[A-Za-z0-9']+", plain))
    minutes = max(1, round((lang_chars / 320.0) + (latin_words / 220.0)))
    return {
        "html": body,
        "toc": renderer.headings,
        "text": plain,
        "chars": len(plain),
        "words": lang_chars + latin_words,
        "minutes": minutes,
    }
