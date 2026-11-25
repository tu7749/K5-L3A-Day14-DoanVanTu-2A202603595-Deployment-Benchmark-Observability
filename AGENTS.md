# Repository Guidelines

## Project Structure

This Day 14 lab uses FastAPI and a mock LLM. Parts `01-localhost-vs-production/` through `05-scaling-reliability/` contain examples for local development, Docker, cloud deployment, API gateways, and scaling. Preserve the teaching progression between `develop/` and `production/`. Go examples live under `02-docker/`.

Complete Part 6 in the fork’s `06-lab-complete/`, including `app/` and the deployment files. Part 7 lives under `06-lab-complete/benchmark-observability/`, with load and eval scripts in `develop/` and Compose, Prometheus rules, and Grafana dashboards in `production/`.

For K5, follow the root `README.md` notes and `CHECKPOINTS.md` when examples differ. Use `RUBRIC.md` for scoring and `SUBMISSION.md` for deliverables. CP6 deploys the Part 6 agent with Redis to Railway or Render and provides the endpoint checks.

## Build and Run

- Use Python 3.11+ and Docker Compose. Install dependencies with `python -m pip install -r requirements.txt` in the exercise directory.
- In `06-lab-complete/`, use `AGENT_API_KEY=dev-key uvicorn app.main:app --reload` for local development or `docker compose up --build` to run the container setup. The starter Compose file defines only the agent. Add Redis as part of Part 6.
- Build the Part 2 development image from the root with `docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .`. Create `.env.local` in the Part 2 and Part 5 `production/` directories before starting Compose. Use distinct `-p` names for the Part 2, 5, and 7 stacks and reuse each name for `logs` and `down`.

## Coding Style

Follow PEP 8. Use four spaces in Python, `snake_case` for modules and functions, and `PascalCase` for classes. Format Go with `gofmt`. Keep secrets in local environment files or deployment settings. Commit safe defaults and placeholders in `.env.example`.

## Testing

- In `06-lab-complete/`, run `python check_production_ready.py` with Docker for `PASS 12/12`. Use `--static-only` or `--skip-docker` during development. On Windows, use WSL2 for the shutdown check.
- Run `python test_stateless.py` in `05-scaling-reliability/production/` after starting the three-replica stack. Follow CP7–CP8 for Part 7 benchmarks and use `--out` to save JSON. Use `promtool` for alert rule tests. The lab uses exercise-specific checks and has no repository-wide coverage target.
- Preserve `check_production_ready.py` and `golden_dataset.jsonl` per `RULES.md`.

## Commits and Pull Requests

Recent documentation commits use short `docs:` subjects. In pull requests, summarize the affected exercise, record verification, and link any related issue. Submit the fork’s link on LMS with measured reports and screenshots per `SUBMISSION.md`. Log AI use for Part 6 code or lab answers in `MISSION_ANSWERS.md`.
