## Step

<!-- Which numbered step from docs/ROADMAP.md does this PR complete? One step per PR. -->

Step NN -

## What changed

<!-- Files touched and why. -->

## Verification

<!-- The verification command from the roadmap step, with its real pasted output.
     A step is never complete on the basis of "the code looks correct". -->

```
```

## Decisions made alone

<!-- Anything decided without asking, and the reasoning. New ADRs go in docs/adr/. -->

## Definition of Done

- [ ] `ruff check` and `ruff format --check` clean
- [ ] `mypy --strict` clean on backend, `tsc --noEmit` clean on frontend
- [ ] New code has tests, and those tests would fail if the feature were removed
- [ ] CI green on this PR
- [ ] No `TODO`, no commented-out code, no debug prints, no unused imports
- [ ] Any new error condition has a registered code in `app/errors.py`
- [ ] Any new env var is in `.env.example` with a comment
- [ ] Any non-obvious decision written into `docs/adr/` as a short ADR
- [ ] Any new invariant added to `docs/test-traceability.md`
- [ ] Any brief requirement newly satisfied ticked in `docs/COMPLIANCE.md`
- [ ] No silent degradation: every new signal has a consumer and a test asserting on it
