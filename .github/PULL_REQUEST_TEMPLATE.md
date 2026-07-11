## What & why

<!-- The problem this solves, then the change. For rule changes: the rationale
     is part of the rule file itself — summarize it here. -->

## How verified

<!-- Commands you ran and their outcome. -->

- [ ] `ruff check .` clean
- [ ] `mypy app perfect_brief` clean
- [ ] `pytest` green (fixtures are the CI gate — a change that moves numbers
      updates fixtures **in the same PR**, with the reason in the message)

## Checklist

- [ ] No secrets, keys, or personal data anywhere in the diff
- [ ] The seam holds: the LLM only judges; code owns every number, the gate,
      and the decision (GOVERNANCE.md — PRs that blur this are declined)
- [ ] Rule PRs: references are authored and checked by me, not model-generated
- [ ] Console changes: `app/static/index.html` and `site/console.html` stay
      identical; surgical edits only
