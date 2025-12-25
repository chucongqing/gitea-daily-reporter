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

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    token = data.get('token')
    username = data.get('username')
    manual_input = data.get('manual_input', '')
    report_type_key = data.get('report_type', 'daily')
    
    if not token or not username:
        return jsonify({"error": "Missing token or username"}), 400

    now = datetime.now()
    
    if report_type_key == 'weekly':
        # Calculate start of the week (Monday)
        start_date = now - timedelta(days=now.weekday())
        report_label = "周报"
        # Reset time to beginning of that day
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Daily
        start_date = now
        report_label = "日报"

    since_date = start_date.strftime('%Y-%m-%dT00:00:00Z')
    
    try:
        # 1. Get Commits
        # Note: We rely on the server's GITEA_URL, but use the user's Token/Username
        commits = gitea_summary.get_activity_report(
            since_date=since_date,
            gitea_url=GITEA_URL,
            token=token,
            username=username
        )

        if not commits and not manual_input:
             return jsonify({"summary": f"--- {username} 在此时段没有提交记录且无手动补充 ---", "commits": []})

        # 2. Generate AI Summary
        # Uses server's OpenAI config
        summary = gitea_summary.generate_ai_summary(commits, report_type=report_label, manual_input=manual_input)
        
        if not summary:
            summary = "AI Summary generation failed or API Key not configured."

        return jsonify({
            "summary": summary,
            "commits": commits
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
