# /// script
# dependencies = [
#   "requests",
#   "python-dotenv",
#   "openai",
# ]
# ///

import os
import json
import time
import sys
import argparse
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI

# 加载 .env 文件中的变量
load_dotenv()

# 从环境变量中获取配置
GITEA_URL = os.getenv("GITEA_URL")
TOKEN = os.getenv("GITEA_TOKEN")
USERNAME = os.getenv("GITEA_USERNAME")

# OpenAI 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Issue/PR 活动类型 -> 中文标签
# content 格式为 "编号|文本"，close/reopen 的文本为空
_ISSUE_PR_LABELS = {
    "create_issue": ("issue", "新建issue"),
    "comment_issue": ("comment", "评论issue"),
    "close_issue": ("issue", "关闭issue"),
    "reopen_issue": ("issue", "重开issue"),
    "create_pull_request": ("pull_request", "新建PR"),
    "merge_pull_request": ("pull_request", "合并PR"),
    "close_pull_request": ("pull_request", "关闭PR"),
    "reopen_pull_request": ("pull_request", "重开PR"),
    "comment_pull": ("comment", "评论PR"),
}

def _parse_issue_content(content):
    """解析 issue/PR 活动的 content 字段。

    Gitea 的 content 格式为 "编号|文本"（文本可能为空，如 close/reopen）。
    返回 (编号字符串, 文本)，解析失败时编号为 None、文本为原值。
    """
    if not content:
        return None, ""
    idx, sep, text = content.partition("|")
    if not sep:
        # 没有分隔符，整段当作文本
        return None, content
    return idx.strip(), text


def get_activity_report(since_date, gitea_url=GITEA_URL, token=TOKEN, username=USERNAME):
    if not gitea_url or not token or not username:
        return "错误: 未提供完整的 Gitea 配置 (URL, Token 或 用户名)"

    report_data = []
    seen = set()  # 去重：以 (repo, date, type, msg) 为唯一键

    # 构造请求头，使用传入的 token
    req_headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json",
        # Gitea 自带反机器人机制：未带 i_like_gitea cookie 的请求会被
        # 302 重定向到 challenge.html 做浏览器人机验证，脚本无法执行 JS
        # 从而永远过不了验证。带上这个 cookie 即可跳过该校验。
        "Cookie": "i_like_gitea=1"
    }

    # 2. 从用户活动流中获取数据
    page = 1
    has_more = True

    def _add_entry(repo_name, date, act_type, msg):
        """去重后追加一条记录，重复条目直接跳过。"""
        key = (repo_name, date, act_type, msg)
        if key in seen:
            return
        seen.add(key)
        report_data.append({
            "repo": repo_name,
            "date": date,
            "type": act_type,
            "msg": msg,
        })

    while has_more:
        # 获取用户活动 feeds（标准 API 路径需带 /api/v1 前缀）
        url = f"{gitea_url}/api/v1/users/{username}/activities/feeds"
        params = {
            "limit": 50,
            "page": page
        }

        try:
            res = requests.get(url, headers=req_headers, params=params, timeout=30)
            res.raise_for_status()
            activities = res.json()
        except requests.exceptions.ConnectionError:
            raise Exception("无法连接到Gitea服务器，请检查网络连接或服务器地址是否正确")
        except requests.exceptions.Timeout:
            raise Exception("连接Gitea服务器超时，请检查网络或稍后重试")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("认证失败：Token无效或已过期，请检查Token是否正确")
            elif e.response.status_code == 404:
                raise Exception("请求的用户不存在，请检查用户名是否正确")
            else:
                raise Exception(f"Gitea服务器返回错误：HTTP {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求Gitea API时发生错误：{str(e)}")
        except Exception as e:
            raise Exception(f"处理Gitea数据时发生未知错误：{str(e)}")

        if not activities:
            break

        for act in activities:
            # 仅处理指定用户的活动
            if act.get('act_user', {}).get('username') != username:
                continue

            created = act.get('created', '')
            if not created:
                continue

            # 实时显示进度
            sys.stdout.write(f"\r⏳ 正在获取... 已收集: {len(report_data)} 条 | 当前日期: {created[:10]}")
            sys.stdout.flush()

            # 如果活动时间早于起始时间，停止处理
            if created < since_date:
                has_more = False
                break

            op_type = act.get('op_type', '')
            repo_name = act.get('repo', {}).get('full_name', '')
            date = created[:10]

            # 1) 代码提交 (push)
            if op_type == 'commit_repo':
                try:
                    content = json.loads(act.get('content', '') or '{}')
                    for c in content.get('Commits', []):
                        full_msg = c.get('Message', '').strip()
                        if full_msg:
                            _add_entry(repo_name, date, "commit", full_msg)
                except Exception:
                    continue

            # 2) Issue / PR 相关活动
            elif op_type in _ISSUE_PR_LABELS:
                act_type, label = _ISSUE_PR_LABELS[op_type]
                idx, text = _parse_issue_content(act.get('content', ''))
                ref = f"#{idx}" if idx else ""
                msg = f"[{label} {ref}] {text}".rstrip()
                _add_entry(repo_name, date, act_type, msg)

        page += 1
        # 速率限制：请求间隔 0.5 秒
        time.sleep(0.5)
        # 防止无限循环
        if page > 20:
            break

    print() # 换行，结束进度显示

    return report_data

def build_prompt(commits_data, report_type="日报", manual_input=""):
    """构造喂给 AI 的完整 prompt 文本。

    这段文本既用于 API 调用，也用于"复制给网页版 AI"的场景，
    保证两种方式喂给 AI 的内容完全一致。
    """
    # 按活动类型分组，让 AI 清楚区分代码提交 / Issue / PR / 评论
    type_groups = {
        "commit": "代码提交",
        "issue": "Issue 相关",
        "pull_request": "PR 相关",
        "comment": "评论/评审",
    }
    grouped = {key: [] for key in type_groups}
    for item in commits_data:
        act_type = item.get('type', 'commit')
        grouped.setdefault(act_type, [])
        grouped[act_type].append(item)

    activity_text = ""
    for act_type, group_title in type_groups.items():
        items = grouped.get(act_type, [])
        if not items:
            continue
        activity_text += f"【{group_title}】\n"
        for item in sorted(items, key=lambda x: (x['repo'], x['date'])):
            activity_text += f"[{item['date']}] {item['repo']}: {item['msg']}\n"
        activity_text += "\n"

    if not activity_text:
        activity_text = "（无活动记录）"

    prompt = f"""
你是一个专业的软件工程师。请根据以下我{'本周' if report_type == '周报' else '今天'}的 Gitea 活动记录以及手动补充的工作内容，写一份高质量的工作{report_type}。

活动记录已按类型分组（代码提交、Issue、PR、评论等），请综合这些维度总结工作。

要求：
1. **体现工作量与质量**：不要仅仅罗列记录，要将技术细节转化为有价值的工作成果描述。使用专业的术语，体现解决问题的深度和复杂度。
2. **结构清晰**：
   - **核心产出**：按项目或功能模块分类，总结完成的核心任务（涵盖代码提交、Issue 处理、PR 合并/评审等）。
   - **技术亮点/难点攻克**：(如果有) 描述遇到的挑战及解决方案，体现技术能力。
   - **明日/下周计划**：基于当前进度规划后续工作。
3. **语气专业**：自信、简洁、条理分明。

Gitea 活动记录：
{activity_text}

手动补充工作内容：
{manual_input if manual_input else "（无手动补充）"}

请生成一份格式美观、内容充实的{report_type}。
"""
    return prompt


def generate_ai_summary(commits_data, report_type="日报", manual_input="", api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL, model=OPENAI_MODEL):
    if not api_key:
        return None

    print(f"\n🤖 正在请求 AI 生成{report_type}总结...")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    prompt = build_prompt(commits_data, report_type, manual_input)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"你是一个能够通过 Gitea 活动记录生成{report_type}的助手。行文清晰，语气专业，简单排版，不要使用markdown语法。"},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 生成失败: {e}"

if __name__ == "__main__":
    # 检查必要配置是否存在（仅在作为脚本运行时）
    if not all([GITEA_URL, TOKEN, USERNAME]):
        print("错误: 请确保 .env 文件或环境变量中配置了 GITEA_URL, GITEA_TOKEN 和 GITEA_USERNAME")
        sys.exit(1)

    if not OPENAI_API_KEY:
        print("警告: 未配置 OPENAI_API_KEY，将无法使用 AI 总结功能")

    parser = argparse.ArgumentParser(description="Gitea Commit Summary Generator")
    parser.add_argument("-week", action="store_true", help="Generate weekly report (default is daily)")
    args = parser.parse_args()

    now = datetime.now()

    if args.week:
        # 计算本周一
        start_date = now - timedelta(days=now.weekday())
        report_type = "周报"
    else:
        # 今天
        start_date = now
        report_type = "日报"

    since_date = start_date.strftime('%Y-%m-%dT00:00:00Z')
    print(f"📊 开始获取 {report_type} 数据 (起始日期: {since_date[:10]})...")

    try:
        data = get_activity_report(since_date)

        if not data:
            print(f"--- {USERNAME} 此时段没有活动记录 ---")
        else:
            print(f"### {report_type}数据提取成功 ###")

            # 按仓库+类型排序打印
            current_repo = ""
            for item in sorted(data, key=lambda x: (x['repo'], x['date'], x.get('type', ''))):
                if item['repo'] != current_repo:
                    current_repo = item['repo']
                    print(f"\n📂 项目: {current_repo}")

                # 格式化多行消息，增加缩进
                display_msg = item['msg'].replace('\n', '\n    ')
                print(f"  - [{item['date']}] {display_msg}")

            # 生成 AI 总结
            summary = generate_ai_summary(data, report_type)
            if summary:
                print("\n" + "="*50)
                print(f"📝 AI 自动生成{report_type}")
                print("="*50)
                print(summary)
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        sys.exit(1)
