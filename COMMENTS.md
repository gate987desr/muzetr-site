# 评论区（已启用）

每篇文章底部都有评论区：**昵称 + 评论内容 + 可选一张图片**，访客不需要注册任何账号。

## 它是怎么工作的

```
访客填表  →  POST /api/comments  →  Netlify Function  →  Netlify Blobs（存数据 + 存图）
页面加载  →  GET  /api/comments?path=/posts/xxx/  →  返回这篇的评论
```

- **不需要数据库、不需要额外服务器、不花钱**：数据存在 Netlify 自带的 Blobs 里
- **接口和网站同一个域名**（`muzetr123.netlify.app/api/...`），所以国内访问不用跨墙、也没有跨域问题
- 代码就两个文件：`netlify/functions/comments.mjs`、`netlify/functions/image.mjs`

## 访客看到什么

- 已经有评论：按时间顺序列出（昵称、时间、内容、图片）
- 还没有评论：显示"还没有人说话。第一个位置留给你。"
- 底部表单：昵称、评论内容、"添加图片"、发布评论

## 已经内置的防滥用

| 规则 | 值 |
| --- | --- |
| 昵称长度 | ≤ 24 字 |
| 正文长度 | 2–800 字 |
| 图片 | JPG / PNG / WEBP / GIF，≤ 2 MB |
| 单 IP 频率 | 每天最多 20 条 |
| 机器人 | 隐藏的 honeypot 字段（填了就丢弃） |

被限流时，页面会提示"今天发得有点多，明天再来"。

## 怎么删评论（管理员）

评论以"每篇文章的路径哈希"分组存在 Blobs 里。删除需要管理员令牌，令牌在 Netlify 的
**环境变量 `ADMIN_TOKEN`** 里（已为你生成）。

**删一条：**

```bash
curl -X POST https://muzetr123.netlify.app/api/comments \
  -H "content-type: application/json" \
  -H "x-admin-token: 你的ADMIN_TOKEN" \
  -d '{"action":"delete","path":"/posts/zui-huasuan-de-shi/","id":"评论id"}'
```

**清空一篇文章的评论：**

```bash
curl -X POST https://muzetr123.netlify.app/api/comments \
  -H "content-type: application/json" \
  -H "x-admin-token: 你的ADMIN_TOKEN" \
  -d '{"action":"purge","path":"/posts/zui-huasuan-de-shi/"}'
```

评论 id 可以从 `GET /api/comments?path=...` 的返回里看到。

> 以后如果觉得用 curl 麻烦，可以让我给你做一个"评论管理页"（列表 + 删除按钮），
> 打开就能点。

## 怎么改外观

- 表单和列表的样式在 `assets/css/site.css` 的「评论区：本站接口版」那一段
- 交互逻辑在 `assets/js/comments.js`（`mountNative` 函数）
- 想改提示语，搜 `还没有人说话`、`今天发得有点多` 就能找到

## 常见问题

**评论发出去没显示？** 刷新页面。列表是每次加载时现取的，不缓存。

**图片传不上去？** 检查大小是否超过 2 MB；手机原图常常 3–5 MB，先压一下。

**能改成先审核再显示吗？** 可以。在 `comments.mjs` 里把默认 `hidden` 设为 true，
再配一个管理员通过接口，通过后才显示。需要的话告诉我，我来加。

**换成别的评论系统？** 改 `site.config.json` 的 `features.comments.provider` 即可，
前端已经做了分支（`netlify` / `giscus`）。
