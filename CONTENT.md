# 内容手册

日常写作只碰 `content/` 目录。改完记得跑 `python build.py`。

---

## 一、写文章

**最快的方式**：双击 `0-开始.cmd` 输入 `3`（或双击 `new-post.cmd`），按提示回答问题
（标题、栏目、标签、短名），它会自动建好文件并打开，你只管写正文。

**手动方式**：新文件放进 `content/posts/`，文件名用英文短横线，它同时是网址：
`content/posts/wo-de-shu-fang.md` → `https://muzetr.com/posts/wo-de-shu-fang/`

文件名以 `_` 或 `.` 开头的不会被打包（`_template.md` 就是模板）。

### frontmatter

文件开头两条 `---` 之间是元信息：

```yaml
---
title: 论读书的姿势
date: 2026-10-12
category: 札记
tags: [阅读, 慢, 姿势]
summary: 一句 40 字以内的摘要，会出现在列表、搜索结果和分享卡片里。
featured: false
---
```

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `title` | ✅ | 标题 |
| `date` | ✅ | `YYYY-MM-DD`，排序与 RSS 都用它 |
| `category` | ✅ | 栏目名，自己定（目前有 札记/书事/器物/城事/技艺/序跋），会自动生成分类页 |
| `tags` |  | 数组，会自动生成标签页 |
| `summary` |  | 列表摘要；不写则截取正文 |
| `featured` |  | `true` 会进首页「精选」 |
| `cover` |  | 预留字段（当前首页不显示封面） |
| `slug` |  | 自定义网址；不写就用文件名 |
| `locked` |  | `true` = 加密文章 |
| `password` | 私密必填 | 阅读口令（构建后会被抹掉，页面里只有密文） |
| `password_hint` |  | 给读者的提示 |

### 支持的 Markdown

| 写法 | 效果 |
| --- | --- |
| `## 标题` / `### 标题` | 小节标题，自动进右侧目录 |
| `**粗体**` `*斜体*` `~~删除线~~` | 行内样式 |
| `` `代码` `` | 行内代码 |
| `[文字](链接)` | 链接，外链自动新窗口打开 |
| `![说明](/路径.svg "图注")` | 图片；带图注会变成带边框的图版 |
| `- 项` / `1. 项` | 列表，可嵌套（缩进两个空格） |
| `> 引用` | 引用块 |
| `> [!NOTE] 小标题` | 提示块，类型：NOTE / TIP / WARNING / QUOTE / STUDY / DANGER |
| ` ```python ` | 代码块，支持 python/js/bash/html/css/sql 高亮 |
| `\| 表格 \|` | 表格 |
| `---` | 分隔线 |

正文里直接写 `<video>`、`<audio>`、`<iframe>`、`<figure>` 这类 HTML 也能通过（原样输出），
嵌入 B 站视频就用这个办法。

**首字下沉**：文章第一段的第一个字会自动放大成烫红色，所以第一段别以图片或标点开头。

### 私密文章

```yaml
locked: true
password: bingxin
password_hint: 一种心境，两个字，与"冰心"同音
```

- 口令不会写进 HTML，正文在构建时加密。
- 想改口令：改 frontmatter，重新 build。
- 口令丢了只能重新写。

---

## 二、碎碎念 `content/notes.json`

按日期倒序，一条一句话：

```json
[
  {
    "date": "2026-11-14",
    "text": "入冬以后，下午四点的光斜着进来，把书脊照成一排深浅不一的黄。",
    "tags": ["light", "winter"]
  }
]
```

页面顶部的筛选按钮由 `tags` 自动生成。

---

## 三、收藏 `content/collection.json`

```json
[
  {
    "type": "anime",
    "title": "虫师",
    "original": "蟲師",
    "year": 2005,
    "status": "看完",
    "score": 9.4,
    "note": "每一集都像在等一场雨，雨停了，人也该走了。",
    "tags": ["治愈", "幻想"]
  }
]
```

- `type`：`anime` / `film` / `book`
- `status`：`看完` / `在看` / `待看` / `搁置`
- `score`：1–10，没有就写 `null`
- `year`：年份；写负数会显示成「先秦」这种

---

## 四、作品 `content/projects.json`

```json
[
  {
    "title": "眉批",
    "year": "2026",
    "subtitle": "一句话定位",
    "summary": "五十到八十个字，说清它解决什么问题、你怎么做的。",
    "stack": ["Python", "SQLite"],
    "status": "进行中",
    "links": [{ "label": "GitHub", "url": "https://github.com/你的仓库" }],
    "featured": true
  }
]
```

`status` 决定徽章颜色：`进行中` 红、`已完成` 绿、`沉淀中` 灰。

---

## 五、友链 `content/friends.json`

```json
[
  { "name": "Keke's Atelier", "url": "https://kekenest.com", "desc": "一句话介绍", "since": "2026" }
]
```

---

## 六、关于 `content/about.json`

```json
{
  "intro": ["第一段", "第二段"],
  "now": [{ "label": "在读", "value": "《蒙田随笔》" }],
  "timeline": [{ "year": "2026", "month": "11", "title": "饮冰室开张", "text": "一句话" }],
  "skills": [{ "group": "文字", "items": ["随笔", "校勘"] }],
  "contacts": [{ "label": "邮箱", "value": "hello@muzetr.com", "url": "mailto:hello@muzetr.com" }],
  "colophon": "关于这个站怎么做出来的说明。"
}
```

`intro` 第一段的第一个字会变成红色的首字下沉。

---

## 七、留言板种子 `content/guestbook.json`

```json
[{ "name": "北窗", "text": "纸的颜色很舒服。", "date": "2026-11-08" }]
```

这些是**静态展示**的留言。访客自己写的留言默认存在他的浏览器里（本地模式）；
想换成真留言板，看 `site.config.json` 的 `features.giscus`，填上仓库就会自动启用。

---

## 八、站点配置 `site.config.json`

最常改的几项：

```json
{
  "domain": "muzetr.com",
  "baseUrl": "https://muzetr.com",
  "title": "饮冰室",
  "titleEn": "The Ice-Drinking Room",
  "motto": "朝受命而夕饮冰，我其内热与。",
  "mottoSource": "《庄子·人间世》",
  "description": "站点简介（会进搜素结果和分享卡片）",
  "author": { "name": "饮冰室主人", "handle": "@muzetr", "email": "hello@muzetr.com" }
}
```

- 换域名时 `domain` 与 `baseUrl` 要一起改（否则 RSS、sitemap、分享图里的地址不对）。
- `nav` 控制导航栏；每一项的 `url` 要和 `sections` 里的页面对应。
- `sections` 里每页的 `epigraph` / `epigraphNote` 是页首的拉丁题词与出处。
- `features.search` / `pwa` / `guestbook` 可以关掉对应功能。

---

## 九、换外观

- **配色**：`assets/css/site.css` 顶部 `:root` 里的 `--paper`（纸色）、`--ink`（墨色）、
  `--accent`（朱红）、`--accent-2`（烫金）。`html[data-theme="night"]` 是烛夜配色。
- **字号**：`html { font-size: 17px }`，三档在下面的 `[data-size]`。
- **中文衬线字体**：`--font-body` 里把 `"Songti SC", "STSong", "SimSun"` 换成你喜欢的
  （比如装了思源宋体就写 `"Source Han Serif SC"`）。
- **换拉丁字**：把 `.woff2` 放进 `assets/fonts/`，改 `assets/css/fonts.css`。
- **纹章、花饰**：`templates/partials/seal.html`（圆章）、`flourish.html`（分隔花饰），
  都是内联 SVG，改 `currentColor` 会跟着主题变。

---

## 十、常见问题

**Q：改了内容，网站没变？**
A：先跑 `python build.py`。部署到线上还要提交并推送（GitHub Pages）或重新部署。

**Q：`python` 不是内部或外部命令？**
A：Python 没装或没加进 PATH。重装时勾选 Add Python to PATH，或者用 `py build.py`。

**Q：构建报错说找不到模板？**
A：`templates/` 里文件名要和 `build.py` 里调用的一致；`partials/` 里的可以直接写 `{{> seal.html }}`。

**Q：想加「归档」「标签」到导航栏？**
A：在 `site.config.json` 的 `nav` 里加一项 `{"label": "归档", "en": "Archive", "url": "/archive/"}`。

**Q：怎么发带图片的文章？**
A：把图片放进 `assets/img/posts/`，正文写 `![说明](/assets/img/posts/你的图.jpg "图注")`。

**Q：文章很多了，首页「最新」太长？**
A：`build.py` 里 `_build_home` 的 `self.posts[:6]` 改成你要的条数。
