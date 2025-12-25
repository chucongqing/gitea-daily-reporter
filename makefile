ifeq ($(OS), Windows_NT)
SHELL := pwsh.exe
.SHELLFLAGS := -NoProfile -Command
endif


setup:
	uv pip install -r requirements.txt

run:
	uv run app.py

build:
	docker build . -t gitea-reporter:latest

up:
	docker compose up -d

down:
	docker compose down


test-ai:
	uv run test_ai_connection.py

r: down up
