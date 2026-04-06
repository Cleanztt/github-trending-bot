import os
import json
import requests

DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK")

def _post_to_dingtalk(payload):
    """通用钉钉 Webhook 发送。"""
    try:
        resp = requests.post(
            DINGTALK_WEBHOOK,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=30,
        )
        result = resp.json()
        if result.get("errcode") == 0:
            print("✅ 推送成功！")
        else:
            print(f"❌ 推送失败: {result}")
            if result.get("errcode") == 300005:
                print("   👉 注意：错误原因 300005 (token is not exist) 意味着你的 Webhook URL 缺少了 ?access_token=xxx 部分！")
                print("   请到 GitHub Settings 中检查 DINGTALK_WEBHOOK 变量是否填入了完整的链接。")
    except Exception as e:
        print(f"❌ 调用钉钉接口异常: {e}")

def format_stars(n):
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)

import time

def send_dingtalk_image(image_url, today):
    """消息①：图片报告（嵌入 GitHub Raw URL）。"""
    # 添加时间戳以绕过 GitHub CDN 缓存
    cache_buster = int(time.time())
    final_url = f"{image_url}?t={cache_buster}"
    print(f"📨 推送图片消息: {final_url}")
    title = f"GitHub 近7天 Star 增速 TOP 10 · {today}"
    text = f"### 📊 {title}\n\n![GitHub Trending]({final_url})"
    _post_to_dingtalk({"msgtype": "markdown", "markdown": {"title": title, "text": text}})

def send_dingtalk_links(repos, today):
    """消息②：紧跟图片的纯链接列表，方便一键直达仓库。"""
    print("📨 推送链接列表消息...")
    title = f"🔗 GitHub TOP 10 · {today} · 点击直达仓库"
    lines = [f"**{title}**\n"]
    for i, repo in enumerate(repos, 1):
        short = repo['name'].split('/')[-1]
        lines.append(f"{i}. [{repo['name']}]({repo['url']}) ⭐ {format_stars(repo['stars'])}")
    text = "\n".join(lines)
    _post_to_dingtalk({"msgtype": "markdown", "markdown": {"title": title, "text": text}})

if __name__ == "__main__":
    if not DINGTALK_WEBHOOK:
        print("错误：未找到 DINGTALK_WEBHOOK 环境变量！")
        exit(1)

    try:
        with open("repos_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("未找到 repos_data.json，无法推送通知。")
        exit(1)

    today = data["today"]
    repos = data["repos"]
    image_filename = data["image_filename"]

    github_repo = os.getenv("GITHUB_REPOSITORY", "")
    github_ref = os.getenv("GITHUB_REF_NAME", "main")
    
    if github_repo:
        image_url = f"https://raw.githubusercontent.com/{github_repo}/{github_ref}/{image_filename}"
        send_dingtalk_image(image_url, today)   # 消息①：图片报告
        send_dingtalk_links(repos, today)       # 消息②：可点击链接列表
    else:
        print("ℹ️ 本地模式：跳过钉钉推送。")
