# 饮冰室 · muzetr.com

一个人的书房型个人网站。文艺复兴 / 民国学人的气质：暖色纸张、宋体正文、
Garamond 拉丁字、烫金细线与印章式徽记。

**零第三方依赖**：只需要 Python 3.9+，没有 node_modules、没有数据库、没有构建框架。
`build.py` 把 `content/` 里的 Markdown 与 JSON 变成 `public/` 里的一整套静态网页。

> 🧭 **第一次用？先看 [新手手册 START-HERE.md](START-HERE.md)** ——
> 从装工具、改内容、到把 muzetr.com 接上线，一步一步写着，不用懂代码。

---

## 一、30 秒跑起来

需要先装 Python（3.9 或更新）。Windows 上安装时记得勾选 **Add Python to PATH**。

```bash
python build.py      # 生成网站到 public/
python serve.py      # 本地预览 http://127.0.0.1:8000
```

Windows 上**最简单的方式**：双击 **`0-开始.cmd`**，会出现一个中文菜单，
按数字选就行（1 生成 / 2 预览 / 3 写文章 / 4 装分享图组件 / 6 检查环境）。

也可以单独双击：

- `build.cmd` —— 只生成网站（出错时窗口会停住，方便看报错）
- `preview.cmd` —— 生成并打开预览
- `new-post.cmd` —— 写一篇新文章

以后每次改完内容，重新跑一次 `python build.py` 就行（本地预览时刷新浏览器即可）。

---

## 二、目录里都是什么

```
muzetr/
├─ 0-开始.cmd            总入口：双击它，菜单里什么都能干
├─ site.config.json     站点身份：站名、域名、导航、作者、社交、功能开关
├─ build.py             生成器（读 content/ → 写 public/）
├─ serve.py             本地预览服务器
├─ menu.py              菜单界面（0-开始.cmd 调的）
├─ new_post.py          写新文章的向导
├─ check.py             环境自检
├─ lib/
│  ├─ markdown.py       Markdown 解析 + 代码高亮 + 目录提取
│  ├─ template.py       极简 Mustache 模板引擎
│  └─ console.py        命令行中文显示 / 对齐
├─ content/             你的内容，日常只动这里
│  ├─ posts/            文章（.md，_template.md 是写作模板）
│  ├─ notes.json        碎碎念
│  ├─ collection.json   书影音收藏
│  ├─ projects.json     作品
│  ├─ friends.json      友链
│  ├─ about.json        关于页
│  └─ guestbook.json    留言板种子
├─ templates/           HTML 模板（改结构改这里）
├─ assets/              样式、脚本、字体、图片（改外观改这里）
├─ docs/                示意图
└─ public/              生成结果，部署的就是这个目录
```

内容怎么改、格式怎么写：见 **[CONTENT.md](CONTENT.md)**。

---

## 三、改哪里，得到什么

| 想改的东西 | 去改 |
| --- | --- |
| 站名、域名、副标题、座右铭 | `site.config.json` |
| 导航栏项目、顺序 | `site.config.json` → `nav` |
| 作者名、邮箱、GitHub | `site.config.json` → `author` / `social` |
| 每篇文章 | `content/posts/新文件名.md` |
| 碎碎念 | `content/notes.json` |
| 书影音收藏 | `content/collection.json` |
| 作品 / 项目 | `content/projects.json` |
| 友链 | `content/friends.json` |
| 关于页的自我介绍、年表、技能 | `content/about.json` |
| 配色、字号、间距 | `assets/css/site.css` 顶部 `:root` |
| 某个页面的结构 | `templates/` 下对应的 `.html` |
| 留言板接 Giscus | `site.config.json` → `features.giscus` |

改完跑 `python build.py`。

---

## 四、已经做好的功能

- **文章**：Markdown 写作，代码高亮、提示块（NOTE/TIP/WARNING/QUOTE/STUDY）、
  表格、图片图注、自动目录、上下篇、相关推荐、阅读时长、阅读进度条
- **碎碎念**：时间线流，支持按标签筛选
- **收藏**：书 / 电影 / 番剧，评分、状态、按类别与状态筛选
- **作品**：带状态徽章、技术栈标签、外链
- **友链**：卡片墙 + 交换友链说明
- **私密文章**：正文在构建时加密，浏览器输入口令本地解密（PBKDF2 + HMAC 流密码）
- **关于**：自我介绍、此刻、年表、手艺、通信方式、版本说明
- **检索**：整站全文搜索，任意页面按 `Ctrl/⌘ + K` 唤出命令面板，或按 `/`
- **留言板**：默认本地模式；填上 Giscus 仓库后自动切换成真留言板
- **显示设置**：日光纸 / 烛夜两套配色，三档字号，宋体 / 黑体切换（记忆在本地）
- **RSS / Sitemap / robots / JSON-LD / OG 分享图**（构建时用 Pillow 生成 1200×630 卡片）
- **PWA**：可安装到桌面，Service Worker 缓存静态资源
- **响应式**：手机、平板、桌面三套排版
- **打印样式**：文章直接打印会去掉导航与装饰

---

## 五、部署到 muzetr.com

三条路，任选一条。域名都在你的注册商后台做 DNS 解析。

### 1) GitHub Pages（免费，最稳）

1. 建一个 GitHub 仓库，把 `muzetr/` 里的文件推上去（`public/` 可以不入库，CI 会生成）。
2. 仓库 **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**。
3. 推送到 `main` 分支，`.github/workflows/deploy.yml` 会自动构建并发布。
4. 在 **Custom domain** 里填 `muzetr.com`，再按提示配置 DNS：

| 类型 | 主机记录 | 值 |
| --- | --- | --- |
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `你的用户名.github.io` |

5. 勾选 **Enforce HTTPS**。

### 2) Netlify

把 `muzetr/` 推到 GitHub 后，在 Netlify「Add new site → Import an existing project」选这个仓库。
`netlify.toml` 已经写好了（`publish = "public"`，`command = "python3 build.py"`）。
然后在 **Domain management** 里添加 `muzetr.com`，按提示把 DNS 指到 Netlify。

### 3) Vercel

```bash
npm i -g vercel      # 或者直接把 public/ 拖进 vercel.com
cd muzetr
python build.py
vercel --prod
```

`vercel.json` 里已经把输出目录设成 `public`。域名在 Vercel 项目的 **Settings → Domains** 里加。

> 小提示：OG 分享图需要 Pillow（`pip install pillow`）和一款中文字体。
> 生成不了时会自动退回默认分享图，不影响网站本身。

---

## 六、关于「私密文章」的诚实说明

文章正文在**构建时**用口令派生的密钥加密，静态页面里只有密文；
浏览器里输入口令后用 WebCrypto 本地解密，口令不会发给任何服务器。

它足够挡住随手点开的人，但**不是军事级加密**：
口令强度决定安全程度，且没有服务端限速。真正机密的日记，建议别放上来。

---

## 七、几个取舍

- 留言板默认是本地模式（存在访客浏览器里）。要真正的留言板，按 `guestbook` 页面底部的
  「留言板接入」配 Giscus，免费且不用写后端。
- 搜索是全站 JSON 索引 + 浏览器端匹配，所以文章多了以后索引会变大（目前 52 条记录，
  约 27 KB）。上千篇以后建议改成分片加载。
- 图片、音频、视频需要你自己放到 `assets/` 里，Markdown 里用相对路径引用。
- 设计上没有引外部字体 CDN：拉丁字用本地打包的 Garamond（OFL 授权），中文用系统宋体，
  所以在 Windows / macOS / iOS 上都能秒开，国内网络也不会卡。

---

## 八、许可

- 代码（`build.py`、`lib/`、`assets/js`、`assets/css`、模板）：MIT
- 文字内容（`content/`）：归你所有
- 字体：EB Garamond / Cormorant Garamond，SIL Open Font License 1.1

---

祝你在这间屋子里写得久一点。
