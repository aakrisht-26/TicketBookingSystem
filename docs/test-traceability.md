# Test traceability

Every invariant this system claims, and the test that proves it. A claim
without a row here is a claim nobody checks.

Filled in as steps land. The Definition of Done in `CLAUDE.md` requires a new
row for every new invariant, in the same step that introduces it.

## How to read a row

- **Invariant** - the guarantee, stated so it can be false.
- **Enforced by** - the mechanism that makes it true. A database constraint, a
  lock ordering, a transaction boundary. Not a code comment.
- **Proven by** - the test that fails if the mechanism is removed. Removal, not
  reformulation: a test that passes against a gutted implementation proves
  nothing.
- **Step** - the roadmap step that introduced it.

The eight data invariants named in `docs/DATA-MODEL.md` are added as their
steps land, alongside the concurrency guarantees from steps 7 and 9 and the
offer cascade from step 13.

## Invariants

| # | Invariant | Enforced by | Proven by | Step |
|---|---|---|---|---|
| TC1 | The backend package installed in the environment is the one in this tree, at the version declared in `backend/pyproject.toml`, so the version has one source of truth. | Editable install of `backend/pyproject.toml`; `app.__version__` read from installed distribution metadata rather than duplicated in source. | `backend/tests/test_toolchain.py::test_package_version_matches_pyproject` | 0 |
| TC2 | The backend runs on Python 3.11, the version `CLAUDE.md` commits to. A runner on any other version fails the build rather than passing quietly on untested behaviour. | `requires-python = ">=3.11,<3.12"` in `backend/pyproject.toml`; `python-version: "3.11"` in the CI workflow. | `backend/tests/test_toolchain.py::test_runs_on_python_311` | 0 |
