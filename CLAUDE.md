## Worktrees

Every Claude Code session works in its own git worktree so parallel sessions never share a checkout.

Rules:
- Start sessions with `claude --worktree` (`-w`). This creates `.claude/worktrees/<name>` on its own branch. The 2x2 grid (`claude-grid.json`) does this by default.
- If you find yourself in the root checkout on `main`, don't edit or commit there; ask the user to restart with `claude --worktree`.
- Commit on the worktree's branch and merge back to `main` via a branch/PR, never by committing directly on `main`.
- When the work is merged, clean up with `git worktree remove .claude/worktrees/<name>`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
