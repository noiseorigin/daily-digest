---
name: daily-digest
description: |
  通用日报生成技能。从 RSS 信息源抓取内容，生成飞书文档（全文 + 卡片代码块），并写入 Bitable。
  支持多主题配置，新增主题只需添加 config/*.yaml 文件。
  当用户说「生成日报」「更新日报」「出一期」「新建日报」「帮我做XX日报」时使用。
---

# Daily Digest Skill

## 目录结构

```
skills/daily-digest/
├── SKILL.md
├── config/
│   ├── garden.yaml         # 家庭园艺日报（已上线）
│   ├── art.yaml            # 当代艺术日报（已上线）
│   ├── pet.yaml            # 宠物日报（待建表）
│   └── example-tech.yaml   # 新主题示例
└── scripts/
    ├── fetch.py            # RSS 抓取 + 分类（通用）
    └── generate.py         # 日报生成（全文 + 卡片，通用）
```

## 已上线主题

| 主题 | 配置文件 |
|------|---------|
| 家庭园艺日报 | `config/garden.yaml` |
| 当代艺术日报 | `config/art.yaml` |
| 宠物日报 | `config/pet.yaml` |

---

## 完整调用流程

### Step 0：检查 Bitable 是否就绪

读取配置文件中的 `meta.bitable.app_token`：

- 如果值为 `YOUR_APP_TOKEN`（占位符）→ **执行建表流程**（见下方）
- 如果有真实 token → 用 `feishu_bitable_app_table` (action=list) 验证表是否存在
  - 表存在 → 继续生成日报
  - 表不存在 → **执行建表流程**

### 建表流程

1. 用 `feishu_bitable_app` (action=create) 创建多维表格，名称为 `{主题名}` 
2. 用 `feishu_bitable_app_table` (action=create) 创建数据表，传入完整字段定义：

```json
{
  "name": "日报",
  "fields": [
    { "field_name": "<title_field>",    "type": 1 },
    { "field_name": "<body_field>",     "type": 1 },
    { "field_name": "<doc_link_field>", "type": 15 },
    { "field_name": "日期",             "type": 5 },
    { "field_name": "主题",             "type": 3,
      "property": { "options": [{ "name": "<meta.name>" }] } }
  ]
}
```

> 字段名从配置文件的 `meta.bitable` 读取：`title_field` / `body_field` / `doc_link_field`

3. 将生成的 `app_token` 和 `table_id` **回写到配置文件**：
   - 编辑 `config/<主题>.yaml`，替换 `YOUR_APP_TOKEN` 和 `YOUR_TABLE_ID`

4. 告知用户表已建好，继续生成日报

---

### Step 1：抓取内容

```bash
cd /root/.openclaw/workspace/skills/daily-digest/scripts
python3 fetch.py --config <主题>.yaml > /tmp/digest_raw.json
```

参数：
- `--config`：配置文件名（必填）
- `--days`：抓取最近几天（默认 7）
- `--per-source`：每源最多几条（默认 5）

---

### Step 2：生成日报结构

```bash
cat /tmp/digest_raw.json | python3 generate.py > /tmp/digest_output.json
```

输出 JSON 字段：
- `full_doc`：飞书文档正文（Lark Markdown 骨架）
- `card`：卡片代码块内容（拍板器语法）
- `doc_title`：文档标题
- `meta`：配置元信息

---

### Step 3：AI 翻译润色

`generate.py` 输出的是英文原文骨架，**必须由 AI 处理后再写入飞书**：

- 英文标题 → 中文翻译（意译，不逐字）
- 英文摘要 → 中文改写（像编辑写稿，保留原意）
- 保留原文链接，每篇文章末尾加 `→ [阅读原文](链接)`
- 卡片版本每条末尾加 `*→ 原文链接*`（斜体，拍板器底部虚线样式）

---

### Step 4：创建飞书文档

用 `feishu_create_doc`：
- `title`：来自 `output.doc_title`
- `markdown`：翻译润色后的全文

文档结构：
```
[全文正文]

---

# 📱 卡片排版版本

*以下为拍板器卡片格式，可直接复制使用*

\`\`\`
[卡片内容]
\`\`\`
```

---

### Step 5：写入 Bitable

用 `feishu_bitable_app_table_record` (action=create)：

```json
{
  "<title_field>": "日报标题",
  "<body_field>":  "正文纯文本",
  "<doc_link_field>": { "link": "文档URL", "text": "文档标题" },
  "日期": <今日毫秒时间戳>
}
```

---

## 新增主题（完整步骤）

### 阶段一：找信息源（AI 执行）

1. 用 `web_search` 搜索：`best <主题> RSS feeds blogs`
2. 用 `web_search` 搜索：`site:reddit.com r/<主题相关subreddit>`
3. 用 Python 批量验证 RSS 地址是否有效（`feedparser.parse`，检查 `len(entries) > 0`）
4. 筛选标准：
   - 有效条目 > 0
   - 内容质量高（非纯广告）
   - 覆盖不同角度（媒体 + 社区 + 专业）

### 阶段二：写配置文件（AI 执行）

1. 复制 `config/example-tech.yaml` → `config/<新主题>.yaml`
2. 填入验证通过的信息源
3. 设计板块（sections）：3-6 个，关键词覆盖主题核心词
4. 写轮换内容池（rotating_content）：至少 7 条冷知识/推荐
5. 写固定结尾（fixed_footer）

### 阶段三：建表 + 首期日报（自动）

执行 Step 0 → Step 5 完整流程

---

## 降级策略

| 情况 | 处理方式 |
|------|---------|
| RSS 源超时/报错 | 自动跳过，继续其他源 |
| 某板块当天无内容 | 跳过该板块 |
| 内容全英文 | AI 翻译润色后写入 |
| Bitable 写入失败 | 先保存文档链接，手动补录 |
| 配置文件无 bitable 信息 | 触发建表流程 |
