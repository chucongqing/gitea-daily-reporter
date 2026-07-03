# Gitea Daily Reporter — Agent Notes

## Purpose
Auto-generate work daily/weekly reports from Gitea activity feeds. Collects commits, issues, PRs, and comments, then summarizes them via AI.

## Architecture

Two entry points share one core module:

- **`app.py`** — Flask web server. Two API endpoints:
  - `POST /api/generate` — fetch Gitea data + call AI API, return summary
  - `POST /api/prompt` — fetch Gitea data + build prompt text only (no AI call), for pasting into free web AI
  - `GET /` — serves `templates/index.html`
- **`gitea_summary.py`** — core logic, also runnable as CLI (`python gitea_summary.py [-week]`).
  - `get_activity_report()` — fetches & parses Gitea activity feeds
  - `build_prompt()` — constructs the AI prompt text (shared by both API and copy-to-web modes)
  - `generate_ai_summary()` — calls OpenAI-compatible API to generate report

### Data flow
```
Frontend (localStorage config)
  → POST /api/generate or /api/prompt
    → get_activity_report()  →  Gitea API (/api/v1/users/{user}/activities/feeds)
    → build_prompt()         →  groups by type (commit/issue/pull_request/comment)
    → generate_ai_summary()  →  OpenAI-compatible API (only for /api/generate)
```

## Key Gotchas

- **Gitea API path**: code uses `/api/v1/users/{username}/activities/feeds` — the `/api/v1` prefix is required; the `.env` `GITEA_URL` should be the root URL (e.g. `https://git.example.com`), not include `/api/v1`.
- **Anti-bot cookie**: requests must include `Cookie: i_like_gitea=1` or Gitea returns 302 to a JS challenge page that scripts cannot pass. This is hardcoded in `get_activity_report()`.
- **Issue/PR content format**: Gitea stores these as `"index|text"` pipe-delimited strings (not JSON). `commit_repo` is the only type with JSON content. See `_parse_issue_content()`.
- **Frontend config > server env**: `app.py` reads Gitea URL and AI config from the request body first, falls back to `.env`. The frontend sends everything from localStorage.
- **Clipboard in HTTP**: `navigator.clipboard` requires HTTPS/localhost. The frontend falls back to `document.execCommand('copy')` for LAN HTTP access.

## Build & Run

```bash
# Docker (arm64 or amd64, auto-detected by base image)
docker build -t gitea-reporter:latest .
docker compose up -d

# With pip proxy
docker build --build-arg PIP_PROXY=http://192.168.3.80:38201 -t gitea-reporter:latest .

# Local
pip install -r requirements.txt
python app.py          # web server on :5000
python gitea_summary.py       # CLI daily report
python gitea_summary.py -week # CLI weekly report
```

## Conventions

- Chinese UI text and comments throughout; keep new UI strings in Chinese.
- `.env` is gitignored — use `.env.example` for new required vars.
- `report_data` entries have `{repo, date, type, msg}` shape; `type` is one of `commit`/`issue`/`pull_request`/`comment`.
- `build_prompt()` is the single source of truth for prompt text — both API and web-copy modes use it.
