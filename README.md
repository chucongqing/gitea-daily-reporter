# gitea AI日报生成

根据gitea 中的提交信息，生成AI日报


配置好 .env 文件后，可以使用 `docker-compose up` 启动服务

```.env
GITEA_URL=https://[gitea 的地址]/api/v1
OPENAI_API_KEY=[openai 的 api key]
OPENAI_BASE_URL=[openai 兼容的 api url]
OPENAI_MODEL=[模型名称]
WEB_PORT=[web 端口]
```

或者安装uv （python 包管理器），使用 `uv run app` 启动服务
