# 评论区怎么开（giscus）

评论会存在一个 GitHub 仓库的 Discussions 里：**免费、没有服务器、没有数据库、不会丢**。
代价是：**评论的人需要一个 GitHub 账号**（注册免费，一分钟）。

> 为什么不用"免注册"的 Valine / Waline？我实测过：它们依赖的 LeanCloud 在你的网络下**完全连不上**，
> 而 giscus 是 0.3 秒直连。这是被网络环境筛出来的选择，不是偷懒。

---

## 一、你要在 GitHub 上做的 4 步（约 10 分钟）

### 1. 注册 GitHub

打开 <https://github.com/signup>，用邮箱注册，验证邮箱。

### 2. 建一个公开仓库

右上角 **+** → **New repository**：

- Repository name：`muzetr-comments`（名字随意）
- 选 **Public**（必须是公开）
- 勾上 **Add a README file**
- 点 **Create repository**

### 3. 打开 Discussions

进这个仓库 → **Settings** → 左侧 **General** → 往下找到 **Features** →
勾选 **Discussions** → 保存（有的版本是自动保存）。

### 4. 安装 giscus

打开 <https://github.com/apps/giscus> → **Install** →
**Only select repositories** → 选中 `muzetr-comments` → **Install**。

---

## 二、拿到 4 个值

打开 <https://giscus.app/zh-CN>，在页面里填：

| 页面上的项 | 填什么 |
| --- | --- |
| 仓库 | `你的用户名/muzetr-comments` |
| Discussion 分类 | 选 **Announcements**（推荐：只有你能发帖，别人只能评论） |
| 页面 ↔ Discussion 映射 | **pathname**（默认） |

往下拉，看到一个代码框，里面有这四个属性，把它们抄下来：

```html
data-repo="你的用户名/muzetr-comments"
data-repo-id="R_xxxxxxxx"
data-category="Announcements"
data-category-id="DIC_xxxxxxxx"
```

---

## 三、填进网站

打开 `site.config.json`，找到这一段，把四个值填进去：

```json
"features": {
  "comments": { "provider": "giscus" },
  "giscus": {
    "repo": "你的用户名/muzetr-comments",
    "repoId": "R_xxxxxxxx",
    "category": "Announcements",
    "categoryId": "DIC_xxxxxxxx"
  }
}
```

然后双击 **⑤ 更新到网站** → 拖 zip。打开任意一篇文章，滑到底部就能看到评论区。

> 四个值没填全之前，页面上**不会出现评论区**（不会显示一个坏掉的框）。

---

## 四、日常怎么管评论

- **看评论 / 回评论**：直接在 GitHub 那个仓库的 **Discussions** 里回，网页上会同步显示。
- **删评论**：在 Discussions 里删。
- **屏蔽某人**：在 Discussions 里 Block。
- **换主题**：评论区会自动跟着网站的日夜模式变色。

---

## 五、如果朋友们大多没有 GitHub 账号

那就得换方案，可选：

| 方案 | 门槛 | 说明 |
| --- | --- | --- |
| 自建 Waline / Twikoo | 要一台服务器或云函数 | 评论者免注册，但要花钱或有免费额度限制 |
| 换成"邮件留言" | 评论者不用注册 | 不是公开评论区，留言只有你能看到 |

跟我说一声，我按你选的方向改。代码里已经留好了 `features.comments.provider` 这个开关，
换供应商不用重写页面。
