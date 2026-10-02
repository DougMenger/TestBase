---
description: Run the agentic security audit in SECURITY_AUDIT.md — find, fix, verify, report
---

Read `SECURITY_AUDIT.md` at the repo root and follow it exactly.

Scope: $ARGUMENTS

- If the scope is empty, run every phase (0 → 7) in order.
- If the scope names a phase (e.g. "phase 3"), run Phase 0 for context, then that phase, then Phase 7 limited to it.

Obey its operating rules throughout:
- never print secret values;
- exploit only local/dev targets;
- auto-fix only within the auto-fix tier, and stop and ask before anything in the ask-first tier;
- commit per phase on the worktree branch.
