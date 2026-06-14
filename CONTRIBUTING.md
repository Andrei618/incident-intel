# Contributing

This document describes how the project is developed: the branching model, commit
conventions, and the checks every change must pass. Full setup and run instructions
live in the [README](README.md#quick-start).

## Branching model

Work flows **feature branch → `develop` → `main`**:

- `main` — production; what's deployed to the live demo.
- `develop` — integration branch; features land here first.
- `feat/*`, `fix/*`, `docs/*`, `chore/*` — short-lived branches, one per change.

`main` and `develop` are **protected mirrors of the remote** — never commit to them
directly. They move only by fast-forward `git pull` (from a merged PR) or the GitHub
merge button. Every change goes through a pull request.

### Daily workflow

```bash
# start a change from an up-to-date develop
git checkout develop && git pull
git checkout -b feat/<short-name>

# ...commit, push, open a PR targeting develop...

# after the PR is merged on GitHub, sync and clean up
git checkout develop && git pull
git branch -d feat/<short-name>
```

One-time guardrails so local and remote never drift:

```bash
git config --global pull.ff only      # pull only fast-forwards; errors on drift instead of silently merging
git config --global fetch.prune true  # drop tracking refs for branches deleted on the remote
```

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/), enforced by a `commit-msg`
hook. Format `<type>: <summary>`, where `<type>` is one of:

`feat` · `fix` · `docs` · `style` · `refactor` · `test` · `chore` · `ci` · `security` · `perf`

Examples: `feat(search): add hybrid RRF ranking`, `fix(chat): suppress citation when no sources`.

## Local development

Full setup (Docker, env, migrations, seed data) is in the
[README](README.md#quick-start). Once set up:

### Backend — Python 3.13, [uv](https://github.com/astral-sh/uv)

```bash
uv sync                          # install dependencies
pre-commit install               # enable the pre-commit + commit-msg hooks
uv run alembic upgrade head      # apply migrations

uv run ruff check .              # lint
uv run ruff format .             # format
uv run mypy src/                 # type-check (strict)
uv run pytest                    # tests
```

### Frontend — Node 20, in `ui/`

```bash
cd ui
npm install
npm run dev          # dev server
npm run lint         # eslint
npm run type-check   # tsc --noEmit
npm run test         # vitest
npm run build        # production build (tsc -b && vite build)
```

## Before opening a PR

CI must be green to merge. It runs on every push and PR to `develop`/`main` and mirrors
the local checks, so run them first:

- **Backend** (`ruff check`, `ruff format --check`, `mypy src/`, `pytest`) — runs when
  `src/`, `pyproject.toml`, or `migrations/` change.
- **Frontend** (`npm run lint`, `npm run type-check`, `npm run test`) — runs when `ui/` changes.

Open the PR against `develop` (not `main`), and keep it focused — one concern per branch.
