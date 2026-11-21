"""A small, dependency-free template engine (a Mustache subset).

Syntax
------
    {{ name }}              HTML-escaped value (dotted paths allowed: {{ site.title }})
    {{{ name }}}            raw value, not escaped
    {{# name }}...{{/ name}}  section: list -> iterate, dict -> new scope, truthy -> once
    {{^ name }}...{{/ name}}  inverted section: rendered only when falsy/empty
    {{> partial.html }}     include another template (rendered with the same scope)
    {{ . }}                 current item, for lists of strings

Everything else is passed through verbatim.
"""

from __future__ import annotations

import html
import os
import re

TOKEN_RE = re.compile(r"\{\{(\{?)\s*(.*?)\s*(\}?)\}\}", re.S)

_MISSING = object()


class TemplateError(Exception):
    pass


def _lookup(scope, path):
    """Resolve a dotted path against nested dicts, with a few conveniences."""
    if path == ".":
        if isinstance(scope, dict):
            return scope.get(".", scope)
        return scope
    current = scope
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part, _MISSING)
        elif isinstance(current, (list, tuple)):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return _MISSING
        else:
            current = getattr(current, part, _MISSING)
        if current is _MISSING:
            return _MISSING
    return current


def _truthy(value):
    if value is _MISSING or value is None or value is False:
        return False
    if isinstance(value, (str, list, tuple, dict)):
        return len(value) > 0
    return True


def _stringify(value):
    if value is _MISSING or value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return ""
    if isinstance(value, dict):
        return ""
    return str(value)


class TemplateEngine:
    def __init__(self, directory, autoescape=True):
        self.directory = directory
        self.autoescape = autoescape
        self._raw_cache = {}
        self._ast_cache = {}

    # -- loading ---------------------------------------------------------
    def _load(self, name):
        if name not in self._raw_cache:
            path = os.path.join(self.directory, name)
            if not os.path.isfile(path):
                fallback = os.path.join(self.directory, "partials", name)
                if os.path.isfile(fallback):
                    path = fallback
            if not os.path.isfile(path):
                raise TemplateError("template not found: %s" % path)
            with open(path, "r", encoding="utf-8") as fh:
                self._raw_cache[name] = fh.read()
        return self._raw_cache[name]

    # -- parsing ---------------------------------------------------------
    def _parse(self, name):
        if name in self._ast_cache:
            return self._ast_cache[name]
        source = self._load(name)
        nodes, _ = self._parse_until(source, 0, None, name)
        self._ast_cache[name] = nodes
        return nodes

    def _parse_until(self, source, pos, closing, name):
        nodes = []
        while True:
            match = TOKEN_RE.search(source, pos)
            if not match:
                if closing is not None:
                    raise TemplateError(
                        "unclosed section %r in %s" % (closing, name)
                    )
                nodes.append(("text", source[pos:]))
                return nodes, len(source)

            raw_open = match.group(1) == "{"
            triple_close = match.group(3) == "}"
            tag = match.group(2)
            nodes.append(("text", source[pos:match.start()]))
            pos = match.end()

            if raw_open or triple_close:
                nodes.append(("raw", tag.lstrip("{").rstrip("}")))
                continue

            if tag.startswith("#"):
                section = tag[1:].strip()
                children, pos = self._parse_until(source, pos, section, name)
                nodes.append(("section", section, children))
            elif tag.startswith("^"):
                section = tag[1:].strip()
                children, pos = self._parse_until(source, pos, section, name)
                nodes.append(("inverted", section, children))
            elif tag.startswith("/"):
                if closing is None:
                    raise TemplateError("unexpected closing tag %r in %s" % (tag, name))
                if tag[1:].strip() != closing:
                    raise TemplateError(
                        "mismatched closing tag %r (expected %r) in %s"
                        % (tag, closing, name)
                    )
                return nodes, pos
            elif tag.startswith(">"):
                nodes.append(("partial", tag[1:].strip()))
            elif tag.startswith("!"):
                continue  # comment
            else:
                nodes.append(("var", tag, raw_open))

    # -- rendering -------------------------------------------------------
    def render(self, name, context):
        if isinstance(context, dict):
            scope = dict(context)
            scope.setdefault("_engine", self)
        else:
            scope = context
        return self._render_nodes(self._parse(name), scope)

    def _render_nodes(self, nodes, scope):
        out = []
        for node in nodes:
            kind = node[0]
            if kind == "text":
                out.append(node[1])
            elif kind == "var":
                value = _stringify(_lookup(scope, node[1]))
                out.append(html.escape(value, quote=True) if (self.autoescape and not node[2]) else value)
            elif kind == "raw":
                out.append(_stringify(_lookup(scope, node[1])))
            elif kind == "section":
                out.append(self._render_section(node[1], node[2], scope))
            elif kind == "inverted":
                out.append("" if _truthy(_lookup(scope, node[1])) else self._render_nodes(node[2], scope))
            elif kind == "partial":
                out.append(self.render(node[1], scope))
        return "".join(out)

    def _render_section(self, path, children, scope):
        value = _lookup(scope, path)
        if not _truthy(value):
            return ""
        if isinstance(value, (list, tuple)):
            chunks = []
            for item in value:
                if isinstance(item, dict):
                    merged = dict(scope)
                    merged.update(item)
                    chunks.append(self._render_nodes(children, merged))
                else:
                    merged = dict(scope) if isinstance(scope, dict) else {}
                    merged["."] = item
                    chunks.append(self._render_nodes(children, merged))
            return "".join(chunks)
        if isinstance(value, dict):
            merged = dict(scope)
            merged.update(value)
            return self._render_nodes(children, merged)
        return self._render_nodes(children, scope)
