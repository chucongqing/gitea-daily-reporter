# /// script
# dependencies = [
#   "flask",
#   "requests",
#   "python-dotenv",
#   "openai",
# ]
# ///

from flask import Flask, render_template, request, jsonify
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import gitea_summary  # Importing from our refactored script

load_dotenv()

app = Flask(__name__)

# Config
PORT = int(os.getenv("WEB_PORT", 5000))
GITEA_URL = os.getenv("GITEA_URL")

@app.route('/')
def index():
    return render_template('index.html', gitea_url=GITEA_URL)

def _parse_report_request(data):
    """从请求体提取公共字段，计算起始日期与报告标签。

    供 /api/generate 和 /api/prompt 共用。
    """
    gitea_url = data.get('gitea_url') or GITEA_URL
    token = data.get('token')
    username = data.get('username')
    manual_input = data.get('manual_input', '')
    report_type_key = data.get('report_type', 'daily')

    now = datetime.now()
    if report_type_key == 'weekly':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        report_label = "周报"
    else:
        start_date = now
        report_label = "日报"

    since_date = start_date.strftime('%Y-%m-%dT00:00:00Z')
    return gitea_url, token, username, manual_input, report_type_key, report_label, since_date


@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    gitea_url, token, username, manual_input, _, report_label, since_date = _parse_report_request(data)

    # AI 配置：优先用前端传入，回退到服务端 .env
    ai_config = data.get('ai_config', {}) or {}
    ai_api_key = ai_config.get('api_key') or os.getenv("OPENAI_API_KEY")
    ai_base_url = ai_config.get('base_url') or os.getenv("OPENAI_BASE_URL")
    ai_model = ai_config.get('model') or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    if not token or not username:
        return jsonify({"error": "Missing token or username"}), 400

    if not gitea_url:
        return jsonify({"error": "Missing Gitea URL"}), 400

    try:
        # 1. Get Commits
        commits = gitea_summary.get_activity_report(
            since_date=since_date,
            gitea_url=gitea_url,
            token=token,
            username=username
        )

        if not commits and not manual_input:
             return jsonify({"summary": f"--- {username} 在此时段没有提交记录且无手动补充 ---", "commits": []})

        # 2. Generate AI Summary
        summary = gitea_summary.generate_ai_summary(
            commits,
            report_type=report_label,
            manual_input=manual_input,
            api_key=ai_api_key,
            base_url=ai_base_url,
            model=ai_model
        )

        if not summary:
            summary = "AI Summary generation failed or API Key not configured."

        return jsonify({
            "summary": summary,
            "commits": commits
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/prompt', methods=['POST'])
def prompt():
    """只取 Gitea 数据并拼好 prompt 文本返回，不调用 AI。

    用户可复制这段文本粘到免费的网页版 AI（ChatGPT/DeepSeek/Kimi 等）
    让其生成日报，无需配置 API Key。
    """
    data = request.json
    gitea_url, token, username, manual_input, _, report_label, since_date = _parse_report_request(data)

    if not token or not username:
        return jsonify({"error": "Missing token or username"}), 400
    if not gitea_url:
        return jsonify({"error": "Missing Gitea URL"}), 400

    try:
        commits = gitea_summary.get_activity_report(
            since_date=since_date,
            gitea_url=gitea_url,
            token=token,
            username=username
        )

        prompt_text = gitea_summary.build_prompt(commits, report_type=report_label, manual_input=manual_input)

        return jsonify({
            "prompt": prompt_text,
            "commits": commits
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
