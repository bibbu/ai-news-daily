#!/usr/bin/env python3
"""
gen_hourly_html.py — 每小时 GitHub Actions 调用
策略：滚动24h合并去重，历史存在 repo 的 news_history.json 中
"""
import os, sys, json, subprocess, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
HISTORY_FILE = "news_history.json"
MAX_AGE_HOURS = 24

UA = "Mozilla/5.0 (compatible; AI-News-GHQ/1.0)"
HISTORY_URL = "https://api.github.com/repos/bibbu/ai-news-daily/contents/news_history.json"


def fetch_news_all(take=500, mode="all"):
    url = f"https://aihot.virxact.com/api/public/items?mode={mode}&take={take}"
    r = subprocess.run(
        ["curl", "-s", "-H", f"User-Agent: {UA}", "-H", "Accept: application/json", url],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        raise RuntimeError(f"curl failed: {r.stderr}")
    data = json.loads(r.stdout)
    return data.get("items", [])


def load_history():
    """从 GitHub API 拉取历史，不存在则返回空列表"""
    if not GITHUB_TOKEN:
        # 本地调试模式
        p = Path(HISTORY_FILE)
        if p.exists():
            return json.loads(p.read_text())
        return []
    import urllib.request
    req = urllib.request.Request(
        HISTORY_URL,
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            content = data.get("content", "")
            import base64
            return json.loads(base64.b64decode(content).decode())
    except Exception:
        return []


def save_history(items):
    """写历史到本地文件（GitHub Actions 会自动 commit 此文件）"""
    Path(HISTORY_FILE).write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


def merge_and_dedupe(new_items, history, max_age_hours=24):
    """合并新条目和历史，24h去重，按时间戳滚动"""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max_age_hours)

    # 已有ID集合
    seen_ids = {it["id"] for it in history if it.get("id")}

    merged = list(history)
    added = 0
    for it in new_items:
        if it.get("id") not in seen_ids:
            merged.append(it)
            seen_ids.add(it["id"])
            added += 1

    # 过滤：只保留最近24h内的（按 published 或 fetched_at 排序）
    def age(ts):
        if not ts:
            return datetime.min.replace(tzinfo=timezone.utc)
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except:
            return datetime.min.replace(tzinfo=timezone.utc)

    merged.sort(key=lambda x: age(x.get("publishedAt") or x.get("published") or x.get("fetched_at")), reverse=True)

    # 截断到24h窗口
    trimmed = [it for it in merged if age(it.get("publishedAt") or it.get("published") or it.get("fetched_at")) >= cutoff]

    print(f"Merged: {len(history)} history + {len(new_items)} new = {len(merged)} total → trimmed to {len(trimmed)} (24h window)")
    print(f"New items added: {added}")
    return trimmed


def generate_html(items, date_str, updated_at):
    emoji_map = {
        "ai-models": "🤖", "ai-products": "🚀",
        "ai-research": "🔬", "industry": "📊", "other": "📰"
    }
    tag_color = {
        "ai-models": "#7c3aed", "ai-products": "#059669",
        "ai-research": "#dc2626", "industry": "#d97706", "other": "#6b7280"
    }

    def render_card(it):
        t = it.get("title", "")
        s = it.get("summary", "")
        src = it.get("source", "")
        u = it.get("url", "")
        cat = it.get("category", "other")
        em = emoji_map.get(cat, "📰")
        col = tag_color.get(cat, "#6b7280")
        pub = (it.get("publishedAt") or it.get("published") or "")[:16]

        summary_short = ((s or "")[:120] + "..." if len(s or "") > 120 else (s or ""))
        # 处理HTML特殊字符
        for old, new in [("&","&amp;"),("<","&lt;"),(">","&gt;")]:
            t = t.replace(old, new)
            summary_short = summary_short.replace(old, new)

        return f'''<li class="news-card">
  <div class="card-header">
    <span class="tag" style="background:{col}">{em} {cat}</span>
    <span class="pub">{pub}</span>
  </div>
  <div class="card-title">{t}</div>
  <div class="card-summary">{summary_short}</div>
  <div class="card-footer">
    <span class="source">{src}</span>
    <a href="{u}" class="read-more" target="_blank">阅读原文 →</a>
  </div>
</li>'''

    cards = "\n".join(render_card(it) for it in items[:100])

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>AI新闻台 · {date_str}</title>
<style>
  :root{{--bg:#faf9f7;--card-bg:#fff;--text:#18181b;--sub:#71717a;--border:#e4dfd6;--accent:#d4633a;--tag-bg:#f3f4f6}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Noto Sans SC,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;padding:20px}}
  .container{{max-width:800px;margin:0 auto}}
  .header{{background:#18181b;border-radius:12px;padding:24px;display:flex;align-items:center;gap:16px;margin-bottom:24px}}
  .logo{{width:44px;height:44px;background:#fff;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:900;color:#18181b;flex-shrink:0}}AI
  .header-info{{flex:1}}
  .header-title{{font-family:Georgia,serif;font-size:20px;font-weight:700;color:#fff}}
  .header-title span{{color:var(--accent)}}
  .header-meta{{font-size:12px;color:rgba(255,255,255,.5);margin-top:4px}}
  .stats{{display:flex;gap:16px;margin-top:8px}}
  .stat{{font-size:12px;color:rgba(255,255,255,.6)}}
  .stat strong{{color:#fff}}
  ul{{list-style:none;display:flex;flex-direction:column;gap:12px}}
  .news-card{{background:var(--card-bg);border-radius:12px;padding:16px 20px;border:1px solid var(--border);transition:box-shadow .2s}}
  .news-card:hover{{box-shadow:0 4px 16px rgba(0,0,0,.08)}}
  .card-header{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
  .tag{{font-size:11px;font-weight:600;color:#fff;padding:2px 8px;border-radius:999px;flex-shrink:0}}
  .pub{{font-size:11px;color:var(--sub);margin-left:auto}}
  .card-title{{font-size:15px;font-weight:700;color:var(--text);margin-bottom:6px;line-height:1.4}}
  .card-summary{{font-size:13px;color:var(--sub);margin-bottom:10px;line-height:1.6}}
  .card-footer{{display:flex;align-items:center;justify-content:space-between}}
  .source{{font-size:11px;color:var(--sub)}}
  .read-more{{font-size:12px;color:var(--accent);text-decoration:none;font-weight:600}}
  .read-more:hover{{text-decoration:underline}}
  .footer{{text-align:center;font-size:11px;color:var(--sub);margin-top:32px;padding-top:16px;border-top:1px solid var(--border)}}
  .update-time{{font-size:11px;color:var(--sub);text-align:center;margin-bottom:16px}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="logo">AI</div>
    <div class="header-info">
      <div class="header-title">AI新闻台 · <span>{date_str}</span></div>
      <div class="header-meta">信息聚合 · 每小时自动更新</div>
      <div class="stats">
        <div class="stat">共 <strong>{len(items)}</strong> 条</div>
        <div class="stat">24h 滚动去重</div>
        <div class="stat">来源: aihot.virxact.com</div>
      </div>
    </div>
  </div>
  <div class="update-time">更新时间：{updated_at}（每小时自动更新）</div>
  <ul>{cards}</ul>
  <div class="footer">
    由 GitHub Actions 自动生成 · 每小时抓取最新新闻并滚动合并24h历史<br>
    GitHub: <a href="https://github.com/bibbu/ai-news-daily" style="color:var(--accent)">bibbu/ai-news-daily</a>
  </div>
</div>
</body>
</html>"""
    return html


def commit_file(git_path, content_b64, message, sha=None):
    """通过 GitHub API 提交文件"""
    import urllib.request
    url = f"https://api.github.com/repos/bibbu/ai-news-daily/contents/{git_path}"
    body = {"message": message, "content": content_b64}
    if sha:
        body["sha"] = sha
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }, method="PUT")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = json.loads(e.read())
        raise RuntimeError(f"GitHub API error {e.code}: {err_body.get('message')}")


def get_sha(git_path):
    import urllib.request
    url = f"https://api.github.com/repos/bibbu/ai-news-daily/contents/{git_path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())["sha"]
    except:
        return None


def main():
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print(f"[{updated_at}] Starting hourly update...")

    # 1. 拉历史
    print("Loading history...")
    history = load_history()
    print(f"  History items: {len(history)}")

    # 2. 抓新新闻（mode=all，take=500）
    print("Fetching latest news (mode=all, take=500)...")
    try:
        new_items = fetch_news_all(take=500, mode="all")
    except Exception as e:
        print(f"  Fetch failed: {e}")
        new_items = []
    print(f"  New items fetched: {len(new_items)}")
    if len(new_items) == 0:
        print("  WARNING: API returned 0 items, preserving existing history")

    # 3. 合并+去重
    merged = merge_and_dedupe(new_items, history, max_age_hours=MAX_AGE_HOURS)

    # 4. 生成 HTML
    print("Generating HTML...")
    html = generate_html(merged, date_str, updated_at)
    html_path = Path("index.html")
    html_path.write_text(html, encoding="utf-8")
    print(f"  Written: {html_path} ({len(html)} bytes)")

    # 5. 写本地历史文件
    save_history(merged)
    print(f"  Written: {HISTORY_FILE} ({len(json.dumps(merged))} bytes)")

    # 6. 提交到 GitHub（history.json + index.html）
    if GITHUB_TOKEN:
        import base64
        print("Committing to GitHub...")

        # index.html
        sha_idx = get_sha("index.html")
        commit_file("index.html", base64.b64encode(html.encode()).decode(), "deploy: hourly news update", sha_idx)
        print("  index.html committed OK")

        # history.json
        hist_content = json.dumps(merged, ensure_ascii=False)
        sha_hist = get_sha(HISTORY_FILE)
        commit_file(HISTORY_FILE, base64.b64encode(hist_content.encode()).decode(), "chore: update news history", sha_hist)
        print(f"  {HISTORY_FILE} committed OK ({len(merged)} items)")
    else:
        print("No GITHUB_TOKEN, skipping commit (local debug mode)")

    print(f"Done. Total items in history: {len(merged)}")


if __name__ == "__main__":
    main()
