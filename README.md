# Daily Digest Skill

> 一套配置驱动的 AI 日报生成系统。从 RSS 信息源自动抓取内容，经 AI 翻译润色后生成飞书文档，并归档到 Bitable。新增主题只需一个 YAML 配置文件。

---

## 效果预览

每期日报包含：
- **飞书文档**：全文排版，含中文翻译、摘要、原文链接跳转
- **卡片代码块**：拍板器语法，可直接复制发布
- **Bitable 归档**：标题 + 文档链接，方便历史检索

内置三个开箱即用的主题：

| 主题 | 信息源数量 | 板块数量 |
|------|-----------|---------|
| 🌿 家庭园艺日报 | 9 个（博客 + Reddit） | 7 个 |
| 🎨 当代艺术日报 | 11 个（媒体 + 理论 + Reddit） | 6 个 |
| 🐾 宠物日报 | 11 个（媒体 + 兽医 + Reddit） | 6 个 |

---

## 目录结构

```
skills/daily-digest/
├── README.md
├── SKILL.md                  # AI 调用规范（供 agent 读取）
├── config/
│   ├── garden.yaml           # 家庭园艺日报
│   ├── art.yaml              # 当代艺术日报
│   ├── pet.yaml              # 宠物日报
│   └── example-tech.yaml     # 新主题模板（从这里开始）
└── scripts/
    ├── fetch.py              # RSS 抓取 + 分类（通用）
    └── generate.py           # 日报骨架生成（全文 + 卡片，通用）
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install feedparser pyyaml
```

### 2. 配置 Bitable

在 `config/*.yaml` 中填入你的飞书 Bitable 信息：

```yaml
bitable:
  app_token: "YOUR_APP_TOKEN"   # 飞书多维表格 token
  table_id: "YOUR_TABLE_ID"     # 数据表 ID
  title_field: "标题"
  body_field: "正文"
  doc_link_field: "飞书文档"
```

> 如果使用 OpenClaw agent，可以跳过这步——agent 会自动建表并回写 token。

### 3. 生成日报

```bash
cd scripts
python3 fetch.py --config garden.yaml | python3 generate.py > output.json
```

输出 JSON 包含 `full_doc`（飞书文档正文）和 `card`（卡片代码块），交给 AI 翻译润色后写入飞书。

---

## 给 Agent 的安装 Prompt

将以下内容加入 agent 的系统 prompt 或 `HEARTBEAT.md`，即可让 agent 理解并执行日报生成任务：

```
## 日报系统

我有一套日报生成系统，配置在 /path/to/skills/daily-digest/。

已有主题：
- 家庭园艺日报（config/garden.yaml）
- 当代艺术日报（config/art.yaml）
- 宠物日报（config/pet.yaml）

当用户说「生成日报」「出一期」「帮我做XX日报」时：
1. 读取 skills/daily-digest/SKILL.md，严格按照其中的流程执行
2. 如果是已有主题，直接从 Step 1 开始
3. 如果是新主题，先搜索信息源、写配置文件、建 Bitable，再生成第一期
```

---

## 使用案例

### 案例一：生成已有主题日报

**用户说：** 出一期宠物日报

**Agent 执行：**
1. 读取 `config/pet.yaml`，确认 Bitable 已就绪
2. 运行 `fetch.py --config pet.yaml`，抓取内容（约 40 条）
3. 运行 `generate.py`，生成骨架
4. AI 翻译润色（英文 → 中文，意译）
5. `feishu_create_doc` 创建飞书文档（全文 + 卡片代码块）
6. `feishu_bitable_app_table_record` 写入归档

**产出：**
- 飞书文档：含 6 个板块、约 11 篇文章、原文链接、今日冷知识
- Bitable 新增一条记录，含文档链接

---

### 案例二：新增主题（全自动）

**用户说：** 帮我做一个咖啡日报

**Agent 执行：**
1. `web_search` 搜索咖啡相关 RSS 源
2. Python 批量验证 RSS 有效性（`feedparser.parse`）
3. 写 `config/coffee.yaml`（信息源 + 板块 + 轮换内容）
4. `feishu_bitable_app` 建表，回写 token 到 yaml
5. 生成第一期日报

**产出：**
- `config/coffee.yaml`（可复用）
- 飞书 Bitable（永久归档）
- 第一期咖啡日报飞书文档

---

### 案例三：定时自动生成

配合 cron，每天自动生成：

```bash
# 每天早上 8 点生成园艺日报（输出到临时文件，由 agent 处理后续步骤）
0 8 * * * cd /path/to/skills/daily-digest/scripts && \
  python3 fetch.py --config garden.yaml | python3 generate.py > /tmp/garden_output.json
```

---

## YAML 配置说明

每个主题配置文件包含 5 个顶层字段：

```yaml
meta:             # 基本信息：名称、标题模板、Bitable 连接信息
sources:          # RSS 信息源列表（支持 blog / reddit / en_media / vet / theory 等类型）
sections:         # 日报板块（支持 top_pick / rotating / static / source_type 策略）
rotating_content: # 轮换内容池（按日期自动轮换，如植物推荐、冷知识）
fixed_footer:     # 固定结尾（每期不变，如品牌介绍、常用链接）
```

### 新增主题步骤

1. 复制 `config/example-tech.yaml` → `config/新主题.yaml`
2. 修改 `meta`（名称 + bitable 信息）
3. 填入 `sources`（RSS 源，建议 6-12 个）
4. 设计 `sections`（3-6 个板块 + 关键词）
5. 写 `rotating_content`（至少 7 条轮换内容）
6. 写 `fixed_footer`（固定结尾）

---

## sections 策略说明

| 策略 | 说明 | 示例 |
|------|------|------|
| `keywords` | 按关键词匹配内容 | `keywords: [how to, guide, diy]` |
| `source_type` | 直接映射信息源类型 | `source_type: reddit` |
| `strategy: rotating` | 从 `rotating_content` 轮换取一条 | 植物推荐、每日冷知识 |
| `strategy: static` | 静态内容，由 AI 生成 | 月度待办、节气提醒 |
| `strategy: top_pick` | 取所有条目中最值得行动的一条 | Lead Story |

---

## 注意事项

- `generate.py` 输出英文骨架，**需要 AI 翻译润色**后再写入飞书（不要直接写原始输出）
- 卡片代码块整体包在 ` ``` ` 中，不渲染，方便复制到拍板器
- 每篇文章末尾有 `→ [阅读原文](链接)` 跳转，卡片版本用 `*→ 链接*` 格式
- RSS 源抓不到时自动跳过，不影响其他源
- 固定结尾（`fixed_footer`）每期保持一致，有新展览/活动时手动更新 `current_show`

---

## 依赖

```
feedparser
pyyaml
```

Python 3.8+，无其他外部依赖。飞书操作通过 OpenClaw 工具完成。

---

## License

MIT
