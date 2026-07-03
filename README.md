# Gitea AI 日报生成器

从 Gitea 活动记录自动生成工作日报 / 周报。统计你**今天**（或本周）的代码提交、Issue、PR、评论等活动，交给 AI 总结成一份专业的工作日报。

## 功能

- **活动采集**：自动拉取 Gitea 用户活动流，统计以下类型：
  - 代码提交（commit_repo）
  - Issue：新建 / 评论 / 关闭 / 重开
  - PR：新建 / 合并 / 关闭 / 重开 / 评论
  - 自动去重，避免同一条 commit 因多次 push 重复出现
- **AI 生成日报**：把活动数据按类型分组后交给 AI，生成包含「核心产出」「技术亮点」「明日计划」的结构化日报
- **两种使用方式**：
  - **API 模式**：配置 AI API Key，一键生成日报（须为 OpenAI 兼容端点）
  - **网页版 AI 模式**：不配 API Key，点「生成数据和提示词」复制数据 + prompt，粘贴到 ChatGPT / DeepSeek / Kimi 等免费网页版 AI 生成日报
- **网页端配置**：Gitea 地址、Token、AI 配置全部在网页上填写，保存在浏览器 localStorage，每个用户可用自己的 AI provider
- **支持日报 / 周报**两种报告类型

## 快速开始

### Docker 部署（推荐）

1. 创建 `.env` 文件（参考 `.env.example`）：

```bash
cp .env.example .env
```

```dotenv
# Gitea 配置
GITEA_URL=https://git.example.com
GITEA_USERNAME=your-username
GITEA_TOKEN=your-personal-access-token

# AI 配置（OpenAI 兼容格式，留空则用网页版 AI 模式）
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# Web 端口
WEB_PORT=5000
```

2. 构建并启动：

```bash
docker build -t gitea-reporter:latest .
docker compose up -d
```

> **内网代理构建**：如果构建时 pip 需要走代理，传入构建参数：
> ```bash
> docker build --build-arg PIP_PROXY=http://192.168.3.80:38201 -t gitea-reporter:latest .
> ```

3. 浏览器访问 `http://<服务器IP>:5000`

### 本地运行

安装 [uv](https://docs.astral.sh/uv/)（Python 包管理器）后：

```bash
uv run app.py
```

或用标准 Python：

```bash
pip install -r requirements.txt
python app.py
```

### 命令行使用

也可以直接跑脚本，在终端输出日报：

```bash
# 生成今天的日报
python gitea_summary.py

# 生成本周的周报
python gitea_summary.py -week
```

## 配置说明

### Gitea Token 获取

在 Gitea UI：**头像 → 设置 → 应用 → 管理 Access Tokens**，生成时勾选 `read:user` 权限。

### 网页端配置

访问网页后点击「⚙️ 配置」展开配置区，填入：
- Gitea 地址、用户名、Token
- AI API Key、Base URL（须 OpenAI 兼容格式）、模型名称

所有配置保存在浏览器 localStorage，刷新不丢失。也可以在服务端 `.env` 中设默认值，网页端不填则用 `.env` 的值。

## 项目结构

```
├── app.py              # Flask Web 服务，提供 /api/generate 和 /api/prompt 端点
├── gitea_summary.py    # 核心：Gitea 活动采集 + AI 日报生成（也可单独命令行运行）
├── templates/
│   └── index.html      # 网页前端
├── Dockerfile          # Docker 构建（支持 PIP_PROXY 构建参数）
├── docker-compose.yml  # Docker Compose 编排
├── .env.example        # 环境变量模板
└── requirements.txt    # Python 依赖
```