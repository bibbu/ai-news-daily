#!/usr/bin/env python3
"""gen_hourly_html.py — 每小时 GitHub Actions 调用：拉取最新新闻，生成自含 HTML。"""
import os, sys, json, subprocess
from pathlib import Path
from datetime import datetime, timezone

UA = "Mozilla/5.0 (compatible; AI-News-GHQ/1.0)"

def fetch_news(take=50, mode="selected"):
    url = f"https://aihot.virxact.com/api/public/items?mode={mode}&take={take}"
    r = subprocess.run(
        ["curl", "-s", "-H", f"User-Agent: {UA}", "-H", "Accept: application/json", url],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        raise RuntimeError(f"curl failed: {r.stderr}")
    data = json.loads(r.stdout)
    return data.get("items", [])

def generate_news_html(news_items, date_str):
    emoji_map = {"ai-models":"🤖","ai-products":"🚀","ai-research":"🔬","industry":"📊","other":"📰"}
    rows = []
    for it in news_items:
        t = it.get("title",""); s = it.get("summary",""); src = it.get("source","")
        u = it.get("url",""); cat = it.get("category","other")
        em = emoji_map.get(cat,"📰")
        rows.append(f'<li style="margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid #e4dfd6"><div style="display:flex;gap:8px;align-items:baseline;margin-bottom:4px"><span style="font-size:13px;font-weight:700;color:#18181b">{em} {t}</span></div><div style="font-size:13px;color:#52525b;line-height:1.6">{s}</div><div style="margin-top:4px;font-size:11px;color:#a1a1aa">{src}</div></li>')
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>AI新闻台 · {date_str}</title><style>body{{margin:0;padding:20px;background:#faf9f7;font-family:-apple-system,Segoe UI,Noto Sans SC,sans-serif;color:#18181b}}.container{{max-width:720px;margin:0 auto}}.header{{background:#18181b;border-radius:12px 12px 0 0;padding:20px 24px;display:flex;align-items:center;gap:12px}}.header-logo{{width:36px;height:36px;background:#fff;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;color:#18181b}}AI.header-title{{font-family:Georgia,serif;font-size:18px;font-weight:700;color:#fff}}AI新闻台 · <span style="color:#d4633a">{date_str}</span>.header-sub{{font-size:11px;color:rgba(255,255,255,.5)}}每小时自动更新 · 共{len(news_items)}条.updated{{font-size:11px;color:#a1a1aa;text-align:center;margin-top:16px}}ul{{list-style:none;margin:0;padding:16px 20px}}</style></head><body><div class="container"><div class="header"><div class="header-logo">AI</div><div><div class="header-title">AI新闻台 · {date_str}</div><div class="header-sub">每小时自动更新 · 共{len(news_items)}条</div></div></div><ul>{''.join(rows)}</ul><div class="updated">由 GitHub Actions 自动生成 · 更新时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div></div></body></html>"""
    return html

def main():
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = Path(os.getenv("OUTPUT_DIR", "/tmp/ai-news-workflow/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Fetching news for {date_str}...")
    items = fetch_news(take=50)
    print(f"Got {len(items)} items")
    html = generate_news_html(items, date_str)
    out_path = out_dir / f"news_{date_str}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Written: {out_path} ({len(html)} bytes)")
    # Also write as index.html for GitHub Pages
    index_path = out_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    print(f"Written: {index_path} ({len(html)} bytes)")

if __name__ == "__main__":
    main()
