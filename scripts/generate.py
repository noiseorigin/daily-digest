#!/usr/bin/env python3
"""
通用日报生成脚本
用法: python3 fetch.py --config garden.yaml | python3 generate.py
输出: 飞书文档 Markdown（全文）+ 卡片代码块，打印到 stdout
"""
import json
import sys
from datetime import datetime
from pathlib import Path


def get_rotating_item(pool: list, key: str = None) -> dict:
    """按日期轮换取一条内容"""
    day = datetime.now().timetuple().tm_yday
    return pool[day % len(pool)]


def format_date_zh() -> str:
    now = datetime.now()
    return f"{now.year}年{now.month}月{now.day}日"


def format_date_en() -> str:
    return datetime.now().strftime("%B %d, %Y")


# ── 全文生成 ─────────────────────────────────────────────────────────────────

def render_full_doc(cfg: dict, categorized: dict) -> str:
    meta = cfg["meta"]
    sections = cfg["sections"]
    rotating = cfg.get("rotating_content", {})
    footer = cfg.get("fixed_footer", {})
    date_str = format_date_zh()

    lines = []

    # 封面 callout
    sources_str = " / ".join(s["name"] for s in cfg["sources"][:5])
    lines += [
        f'<callout emoji="🌿" background-color="light-green">',
        f'**今日速览** · {date_str} · 来源：{sources_str}',
        f'</callout>',
        "",
        "---",
        "",
    ]

    for sec in sections:
        sec_id = sec["id"]
        strategy = sec.get("strategy")
        items = categorized.get(sec_id, [])

        # 跳过空板块（rotating/static 除外）
        if not items and strategy not in ("rotating", "static"):
            continue

        lines.append(f"## {sec['title']}")
        lines.append("")

        if strategy == "rotating":
            # 植物推荐
            pool_key = list(rotating.keys())[0] if rotating else None
            if pool_key:
                plant = get_rotating_item(rotating[pool_key])
                pet_icon = "✅ 友好" if plant.get("pet_safe") else "❌ 不友好"
                reasons = "\n".join(f"- {r}" for r in plant.get("reasons", []))
                lines += [
                    f'<callout emoji="{plant.get("emoji", "🌱")}" background-color="light-green">',
                    f'**{plant["name"]}**（{plant["latin"]}）',
                    "",
                    "**为什么推荐：**",
                    reasons,
                    "",
                    f'**养护要点：** {plant["care"]}',
                    "",
                    f'**🐾 宠物友好：{pet_icon}**',
                    plant.get("pet_note", ""),
                    "</callout>",
                    "",
                ]
        elif strategy == "static":
            # 静态内容（如月度待办），由 AI 在调用时补充
            lines += [
                "> *（本板块内容由 AI 根据当前节气和月份生成）*",
                "",
            ]
        else:
            for item in items:
                title = item["title"]
                link = item["link"]
                source = item["source"]
                desc = item.get("desc", "")
                lines += [
                    f"**[{title}]({link})** · {source}",
                    "",
                ]
                if desc:
                    lines += [desc, ""]
                lines += [
                    f"→ [阅读原文]({link})",
                    "",
                    "---",
                    "",
                ]

    # 今日冷知识（如果有）
    if "fact" in rotating:
        fact = get_rotating_item(rotating["fact"])
        lines += [
            "## 💡 今日冷知识",
            "",
            f'<callout emoji="💡" background-color="light-yellow">',
            f'**{fact["title"]}**',
            "",
            fact["body"],
            "</callout>",
            "",
            "---",
            "",
        ]

    # 固定结尾
    if footer:
        lines.append(f"## {footer['title']}")
        lines.append("")
        if footer.get("tagline"):
            lines.append(f"**{footer['tagline']}**")
            lines.append("")
        if footer.get("content"):
            lines.append(footer["content"])
            lines.append("")
        # 当前展览
        show = footer.get("current_show")
        if show:
            lines += [
                f"**当前展览：{show['title']}**",
                f"📅 {show['dates']}",
                show.get("blurb", ""),
                f"→ {show['link']}",
                "",
            ]
        for lnk in footer.get("links", []):
            lines.append(f"→ [{lnk['text']}]({lnk['url']})")
        lines.append("")

    return "\n".join(lines)


# ── 卡片代码块生成 ────────────────────────────────────────────────────────────

def render_card(cfg: dict, categorized: dict) -> str:
    meta = cfg["meta"]
    sections = cfg["sections"]
    rotating = cfg.get("rotating_content", {})
    footer = cfg.get("fixed_footer", {})
    date_str = format_date_zh()

    lines = [
        f"# {meta['card_header']}",
        f"#### {date_str} · {meta['card_vol_prefix']}",
        "",
        "---",
        "",
    ]

    counter = 1
    for sec in sections:
        sec_id = sec["id"]
        strategy = sec.get("strategy")
        items = categorized.get(sec_id, [])

        if not items and strategy not in ("rotating", "static"):
            continue

        lines += [f"## {sec['title']}", ""]

        if strategy == "rotating":
            pool_key = list(rotating.keys())[0] if rotating else None
            if pool_key:
                plant = get_rotating_item(rotating[pool_key])
                pet_icon = "✅ 友好" if plant.get("pet_safe") else "❌ 不友好"
                lines += [
                    f"### {plant['name']} {plant.get('emoji', '')}",
                    f"> 极耐旱、耐阴、净化空气，新手首选。{plant['care']}",
                    f"```",
                    f"🐾 宠物友好：{pet_icon} — {plant.get('pet_note', '')}",
                    f"```",
                    f"*{plant['latin']}*",
                    "",
                    "---",
                    "",
                ]
        elif strategy == "static":
            lines += [
                "> *（本板块内容由 AI 根据当前节气和月份生成）*",
                "",
                "---",
                "",
            ]
        else:
            for item in items:
                title = item["title"]
                link = item["link"]
                source = item["source"]
                desc = item.get("desc", "")
                num = f"{counter:02d}"
                counter += 1
                lines += [f"### {num} {title}"]
                if desc:
                    lines += [f"> {desc[:100]}"]
                lines += [
                    f"*{source}*",
                    f"*→ {link}*",
                    "",
                ]
            lines += ["---", ""]

    # 冷知识
    if "fact" in rotating:
        fact = get_rotating_item(rotating["fact"])
        lines += [
            "## 💡 今日冷知识",
            f"```{fact['title']}——{fact['body'][:80]}```",
            "",
            "---",
            "",
        ]

    # 固定结尾
    if footer:
        lines += [f"## {footer['title']}"]
        if footer.get("tagline"):
            lines.append(f"> **{footer['tagline']}**")
        if footer.get("content"):
            lines.append(f"> {footer['content']}")
        for lnk in footer.get("links", []):
            lines.append(f"*{lnk['url']}*")
        lines.append("")

    return "\n".join(lines)


# ── 主程序 ───────────────────────────────────────────────────────────────────

def main():
    raw = sys.stdin.read()
    data = json.loads(raw)
    cfg = data["config"]
    categorized = data["categorized"]

    full_doc = render_full_doc(cfg, categorized)
    card = render_card(cfg, categorized)

    output = {
        "meta": cfg["meta"],
        "full_doc": full_doc,
        "card": card,
        "date": format_date_zh(),
        "doc_title": cfg["meta"]["doc_title_template"].replace("{date}", format_date_zh()),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
