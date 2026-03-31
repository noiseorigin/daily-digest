#!/usr/bin/env python3
"""
通用 RSS 抓取脚本
用法: python3 fetch.py --config garden.yaml [--days 7] [--per-source 5]
输出: JSON 格式的分类内容，供 generate.py 使用
"""
import argparse
import feedparser
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_feed(name: str, url: str, source_type: str, days: int, per_source: int) -> list:
    try:
        feed = feedparser.parse(url)
        cutoff = datetime.now() - timedelta(days=days)
        entries = []
        for entry in feed.entries[:per_source * 2]:  # 多抓一些，过滤后取 per_source
            pub = None
            for attr in ("published_parsed", "updated_parsed"):
                if hasattr(entry, attr) and getattr(entry, attr):
                    pub = datetime(*getattr(entry, attr)[:6])
                    break
            if pub and pub < cutoff:
                continue
            title = entry.get("title", "").strip()
            desc = strip_html(entry.get("summary", ""))[:300]
            entries.append({
                "title": title,
                "link": entry.get("link", ""),
                "published": pub.strftime("%Y-%m-%d") if pub else "近期",
                "source": name,
                "desc": desc,
                "type": source_type,
            })
            if len(entries) >= per_source:
                break
        print(f"✅ {name}: {len(entries)} 条", file=sys.stderr)
        return entries
    except Exception as e:
        print(f"❌ {name}: {e}", file=sys.stderr)
        return []


def categorize(entries: list, sections: list) -> dict:
    """按 sections 配置分类内容"""
    result = {s["id"]: [] for s in sections}
    max_items = {s["id"]: s.get("max_items", 3) for s in sections}

    # 先处理 source_type 直接映射的板块
    type_sections = {s["id"]: s["source_type"] for s in sections if "source_type" in s}

    for entry in entries:
        placed = False
        # 优先按 source_type 分配
        for sec_id, stype in type_sections.items():
            if entry["type"] == stype and len(result[sec_id]) < max_items[sec_id]:
                result[sec_id].append(entry)
                placed = True
                break
        if placed:
            continue

        # 按关键词分配
        text = (entry["title"] + " " + entry["desc"]).lower()
        for s in sections:
            if "source_type" in s:
                continue
            if s.get("strategy") in ("rotating", "static"):
                continue
            kws = s.get("keywords", [])
            if kws and any(k in text for k in kws) and len(result[s["id"]]) < max_items[s["id"]]:
                result[s["id"]].append(entry)
                placed = True
                break

        # 未分类的放到第一个非特殊板块
        if not placed:
            for s in sections:
                if "source_type" not in s and s.get("strategy") not in ("rotating", "static"):
                    if len(result[s["id"]]) < max_items[s["id"]]:
                        result[s["id"]].append(entry)
                        break

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="配置文件名，如 garden.yaml")
    parser.add_argument("--days", type=int, default=7, help="抓取最近几天的内容")
    parser.add_argument("--per-source", type=int, default=5, help="每个信息源最多抓几条")
    args = parser.parse_args()

    config_dir = Path(__file__).parent.parent / "config"
    config_path = config_dir / args.config
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    print(f"🚀 开始抓取：{cfg['meta']['name']}", file=sys.stderr)

    all_entries = []
    for src in cfg["sources"]:
        entries = fetch_feed(src["name"], src["url"], src["type"], args.days, args.per_source)
        all_entries.extend(entries)
        time.sleep(0.8)

    print(f"\n📊 共抓到 {len(all_entries)} 条内容", file=sys.stderr)

    categorized = categorize(all_entries, cfg["sections"])

    print("\n📈 分类统计:", file=sys.stderr)
    for sec_id, items in categorized.items():
        print(f"  {sec_id}: {len(items)} 条", file=sys.stderr)

    # 输出 JSON 供 generate.py 使用
    output = {
        "config": cfg,
        "categorized": categorized,
        "fetched_at": datetime.now().isoformat(),
        "total": len(all_entries),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
