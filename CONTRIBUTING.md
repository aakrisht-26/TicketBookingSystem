# Contributing

## Local setup

Requires Python 3.11, Node 22 and Docker.

```bash
cp .env.example .env
docker compose up -d postgres

cd backend
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cd ..
pre-commit install
```

## Checks

Run from `backend/`. CI runs exactly these, so a clean local run is a green
pull request.

```bash
ruff check .
ruff format --check .
mypy
pytest -q
```

`pre-commit run --all-files` runs the same lint, format and type checks across
the repository, plus the file hygiene hooks.

## Working protocol

The protocol in `CLAUDE.md` governs. Three parts of it matter most:

**One step per branch, one step per pull request.** Branch off `main` as
`step-NN-short-name`. Never commit to `main`. Something worth fixing that is
outside the current step goes in `docs/backlog.md`, not into the diff.

**Verification is not optional.** Every step in `docs/ROADMAP.md` names a
verification command. Run it and paste the real output into the pull request.
A step is never complete because the code looks correct.

**No silent degradation.** If a change introduces a signal, something must read
it and a test must assert on it. A field nobody reads, a status nobody
branches on, an event nobody subscribes to and an error code nobody returns are
all bugs, not future-proofing.

The full Definition of Done is in `CLAUDE.md` and is reproduced as a checklist
in the pull request template.

## Commits

Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`,
`ci:`. The scope is optional and is usually `backend`, `frontend` or `ci`.

## Prose

Plain hyphens, not em dashes, in the README, the ADRs and the write-up.
