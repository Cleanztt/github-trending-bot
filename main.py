import os
import requests
import json
import datetime
import hashlib
import base64
import re
import html as html_module
from playwright.sync_api import sync_playwright

DEEPSEEK_API_KEY = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
DINGTALK_WEBHOOK = (os.getenv("DINGTALK_WEBHOOK") or "").strip()

_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans',
                 'Noto Sans CJK SC', 'PingFang SC', 'Microsoft YaHei',
                 'Helvetica Neue', Arial, sans-serif;
    background: #0a0e1a;
    color: #c9d1d9;
    width: 900px;
}
.container { width: 900px; }
.header {
    background: linear-gradient(135deg, #1a3a6e 0%, #1e1060 60%, #0a1628 100%);
    padding: 36px 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 2px solid #1f6feb;
    position: relative;
    overflow: hidden;
}
.header-glow {
    position: absolute; top: -80px; right: -80px;
    width: 320px; height: 320px;
    background: radial-gradient(circle, rgba(88,166,255,0.15) 0%, transparent 70%);
    pointer-events: none;
}
.header-left { display: flex; align-items: center; gap: 18px; position: relative; z-index: 1; }
.header-icon { font-size: 44px; line-height: 1; }
.main-title { font-size: 22px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px; line-height: 1.35; }
.sub-title { font-size: 13px; color: #8b949e; margin-top: 6px; }
.daily-badge {
    background: linear-gradient(135deg, #238636, #2ea043);
    color: white; font-size: 10px; font-weight: 700;
    letter-spacing: 2.5px; padding: 8px 16px;
    border-radius: 20px; position: relative; z-index: 1;
}
.col-header {
    display: flex; align-items: center;
    padding: 10px 24px 10px 20px;
    background: #161b22;
    border-bottom: 1px solid #30363d;
    font-size: 11px; font-weight: 600;
    color: #6e7681; letter-spacing: 1.2px; text-transform: uppercase;
}
.ch-rank { width: 70px; text-align: center; }
.ch-project { flex: 1; }
.project-row {
    display: flex; align-items: flex-start;
    padding: 22px 24px 22px 20px;
    border-bottom: 1px solid #21262d;
    gap: 18px;
}
.project-row:nth-child(odd) { background: #0d1117; }
.project-row:nth-child(even) { background: #0a0e18; }
.project-row:last-child { border-bottom: none; }
.rank-badge {
    width: 42px; height: 42px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; font-weight: 800;
    flex-shrink: 0; margin-top: 2px;
}
.rank-1 { background: linear-gradient(135deg, #f6a821, #f0c040); color: #3d1f00; box-shadow: 0 0 14px rgba(240,192,64,0.5); }
.rank-2 { background: linear-gradient(135deg, #909599, #c8cdd2); color: #111; box-shadow: 0 0 10px rgba(200,205,210,0.3); }
.rank-3 { background: linear-gradient(135deg, #a0522d, #cd8b4a); color: #2a0a00; box-shadow: 0 0 10px rgba(205,139,74,0.35); }
.rank-other { background: #161b22; border: 1px solid #30363d; color: #58a6ff; }
.project-content { flex: 1; min-width: 0; }
.project-title-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.project-path { font-size: 13px; color: #8b949e; }
.slash { color: #484f58; margin: 0 1px; }
.project-name { font-size: 17px; font-weight: 700; color: #58a6ff; letter-spacing: -0.3px; }
.stars-chip {
    display: inline-flex; align-items: center; gap: 4px;
    background: rgba(210,153,34,0.12);
    border: 1px solid rgba(210,153,34,0.35);
    border-radius: 20px; padding: 2px 10px;
    font-size: 13px; font-weight: 600; color: #e3b341;
}
.lang-chip {
    display: inline-flex; align-items: center;
    background: rgba(88,166,255,0.08);
    border: 1px solid rgba(88,166,255,0.2);
    border-radius: 20px; padding: 2px 10px;
    font-size: 12px; color: #58a6ff;
}
.summary { font-size: 13.5px; line-height: 1.75; color: #8b949e; }
.footer {
    padding: 18px 40px; text-align: center;
    font-size: 12px; color: #3d444d;
    background: #080b14; border-top: 1px solid #21262d;
    letter-spacing: 0.5px;
}
"""


def fetch_github_trending():
    print("📡 正在通过 GitHub Search API 获取数据...")
    week_ago = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    api_url = (
        f"https://api.github.com/search/repositories"
        f"?q=created:>{week_ago}&sort=stars&order=desc&per_page=10"
    )
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "GitHub-Trending-Bot/1.0"}
    gh_token = (os.getenv("GH_TOKEN") or "").strip()
    if gh_token:
        headers["Authorization"] = f"token {gh_token}"
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ GitHub API 请求失败: {e}")
        return []
    repos = []
    for item in response.json().get("items", []):
        repos.append({
            "name": item["full_name"],
            "url": item["html_url"],
            "description": item.get("description") or "No description provided.",
            "stars": item["stargazers_count"],
            "language": item.get("language") or "N/A",
            "created_at": item["created_at"][:10],
        })
    print(f"✅ 成功获取 {len(repos)} 个项目。")
    return repos


def generate_summary(repos):
    print("🧠 正在调用 DeepSeek AI 生成项目解读...")
    repo_list_text = ""
    for i, repo in enumerate(repos, 1):
        repo_list_text += (
            f"{i}. 项目名: {repo['name']}\n"
            f"   官方简介(英文): {repo['description']}\n"
            f"   编程语言: {repo['language']}\n"
            f"   GitHub Stars: {repo['stars']:,}\n\n"
        )
    
    prompt = f"""你是一位资深技术专家，请对以下10个近期在 GitHub 上 Star 数激增的新兴项目进行解读。

{repo_list_text}
要求：
1. 用中文，每个项目写3到5句话，涵盖：是什么工具、解决什么问题、适合谁用、有何亮点。
2. 语言通俗易懂，非技术人员也能快速理解。
3. 必须返回纯 JSON 数据，且为一个数组格式。不要有任何额外的文字如 markdown 代码块。格式示例：
[
  {{"rank": 1, "name": "仓库全名", "summary": "3-5句话解读..."}},
  ...
]"""

    try:
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一名资深技术专家，必须只返回 JSON 格式结果，不要包含 Markdown 代码块。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4
        }
        
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        
        raw_content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        
        # 1. Cleaner JSON Extraction: Remove potential markdown wrappers
        if raw_content.startswith("```"):
            raw_content = re.sub(r'^```(json)?\n', '', raw_content)
            raw_content = re.sub(r'\n```$', '', raw_content)
            
        json_match = re.search(r'(\[.*\]|\{.*\})', raw_content, re.DOTALL)
        if json_match:
            raw_content = json_match.group(1)
            
        summaries_data = json.loads(raw_content)
        
        # 2. Structural Normalization: Convert all variants to a standard list of objects
        normalized_list = []
        if isinstance(summaries_data, dict):
            # Case A: {"projects": [...]}
            for k, v in summaries_data.items():
                if isinstance(v, list):
                    normalized_list = v
                    break
            else:
                # Case B: {"1": "summary text"} or {"1": {"summary": "..."}}
                for k, v in summaries_data.items():
                    if isinstance(v, str):
                        normalized_list.append({"rank": k, "summary": v})
                    elif isinstance(v, dict):
                        if "rank" not in v: v["rank"] = k
                        normalized_list.append(v)
        elif isinstance(summaries_data, list):
            # Case C: ["summary1", "summary2"] (positional strings)
            for i, item in enumerate(summaries_data):
                if isinstance(item, str):
                    normalized_list.append({"rank": i+1, "summary": item})
                else:
                    normalized_list.append(item)

        # 3. Final Mapping Logic: Map by Rank (priority) then Name (fuzzy) then Position (fallback)
        result = {}
        for item in normalized_list:
            if not isinstance(item, dict): continue
            
            val = item.get("summary") or item.get("description") or "暂无解读。"
            
            # Use Rank if available
            if "rank" in item:
                try:
                    result[int(item["rank"])] = val
                except (ValueError, TypeError):
                    pass
            
            # Fuzzy match by name if repo index still missing
            item_name = item.get("name", "").lower()
            if item_name:
                for i, r in enumerate(repos, 1):
                    if i not in result:
                        repo_name = r["name"].lower()
                        if item_name in repo_name or repo_name in item_name:
                            result[i] = val

        # 4. Final Fail-Safe: If counts match but keys are missing, map by index
        if len(normalized_list) == len(repos):
            for i in range(len(repos)):
                idx = i + 1
                if idx not in result:
                    item = normalized_list[i]
                    result[idx] = item.get("summary") if isinstance(item, dict) else str(item)

        print(f"📊 成功解析了 {len(result)}/{len(repos)} 个项目的深度解读。")
        return result

    except Exception as e:
        if "Invalid header value" in str(e):
            print(f"❌ DeepSeek 调用失败: 检测到非法的 API Key 格式 (可能包含空格或换行符)，请检查 GitHub Secrets 配置。")
        else:
            print(f"⚠️ DeepSeek 调用或解析失败: {e}")
        import traceback
        traceback.print_exc()
        return {}


def format_stars(n):
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


def generate_html(repos, summaries, today):
    rows_html = ""
    for i, repo in enumerate(repos, 1):
        summary = summaries.get(i, "暂无解读。")
        parts = repo["name"].split("/")
        owner = html_module.escape(parts[0])
        short_name = html_module.escape(parts[1] if len(parts) > 1 else parts[0])
        stars = format_stars(repo["stars"])
        lang = repo["language"]
        rank_cls = {1: "rank-1", 2: "rank-2", 3: "rank-3"}.get(i, "rank-other")
        lang_html = (
            f'<span class="lang-chip">{html_module.escape(lang)}</span>'
            if lang and lang != "N/A" else ""
        )
        rows_html += f"""
        <div class="project-row">
            <div class="rank-badge {rank_cls}">{i}</div>
            <div class="project-content">
                <div class="project-title-row">
                    <span>
                        <span class="project-path">{owner}</span>
                        <span class="slash">/</span>
                        <span class="project-name">{short_name}</span>
                    </span>
                    <span class="stars-chip">⭐ {stars}</span>
                    {lang_html}
                </div>
                <div class="summary">{html_module.escape(summary)}</div>
            </div>
        </div>"""

    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<style>{_CSS}</style></head><body><div class="container">
    <div class="header">
        <div class="header-glow"></div>
        <div class="header-left">
            <div class="header-icon">📊</div>
            <div>
                <div class="main-title">GitHub 近7天 Star 增速 TOP 10</div>
                <div class="sub-title">{today}&nbsp;&nbsp;·&nbsp;&nbsp;DeepSeek AI 深度解读&nbsp;&nbsp;·&nbsp;&nbsp;全自动生成</div>
            </div>
        </div>
        <div class="daily-badge">DAILY</div>
    </div>

    {rows_html}
    <div class="footer">💡 Antigravity + DeepSeek · 每日 09:00 自动推送</div>
</div></body></html>"""


def render_image(html_content):
    print("🎨 正在渲染图片（Playwright）...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 600}, device_scale_factor=1.5)
        page.set_content(html_content, wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        image_bytes = page.screenshot(full_page=True)
        browser.close()
    print(f"✅ 图片渲染完成，大小: {len(image_bytes) / 1024:.0f} KB")
    return image_bytes






if __name__ == "__main__":
    if not DEEPSEEK_API_KEY:
        print("错误：未找到 DEEPSEEK_API_KEY 环境变量！")
        exit(1)

    repos = fetch_github_trending()
    if not repos:
        print("未获取到项目数据，退出。")
        exit(1)

    today = datetime.date.today().strftime("%Y-%m-%d")
    summaries = generate_summary(repos)
    html_content = generate_html(repos, summaries, today)
    image_bytes = render_image(html_content)

    image_filename = f"report-{today}.png"
    with open(image_filename, "wb") as f:
        f.write(image_bytes)
    print(f"💾 图片已保存: {image_filename}")
    
    # Save metadata for notify.py
    with open("repos_data.json", "w", encoding="utf-8") as f:
        json.dump({"today": today, "repos": repos, "image_filename": image_filename}, f, ensure_ascii=False)
    print("💾 元数据已被存入 repos_data.json，供 notify.py 使用。")

