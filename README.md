# Base-Project

Template for new Claude Code projects on Windows + VS Code.

## New project

```powershell
python scripts\init_project.py C:\code\my-new-app
```

This copies the template into the folder, runs `git init` with an initial commit, and installs the **Claude Grid** VS Code extension. It's safe to rerun, and it never overwrites existing files.

Options: `--skip-extension` skips the extension install. `--grid-only` only (re)installs the extension.

You can also run it from VS Code with **Terminal → Run Task → Init project**.

## 4 Claude sessions in a 2x2 grid

Open the project folder in VS Code, then **Ctrl+Shift+P → "Claude: Open 2x2 Terminal Grid"**.

This opens four editor terminals (top-left, top-right, bottom-left, bottom-right). Each one runs `claude --worktree`, so every session gets its own git worktree under `.claude\worktrees\`.

To change each terminal's folder or command, edit `claude-grid.json`:

```json
{
  "command": "claude --worktree",
  "terminals": [
    { "name": "Top-left",     "folder": "." },
    { "name": "Top-right",    "folder": "frontend" },
    { "name": "Bottom-left",  "folder": "C:\\code\\other-repo" },
    { "name": "Bottom-right", "folder": ".", "command": "claude" }
  ]
}
```

Relative folders are resolved from the workspace root. The file is read every time the grid opens, so you don't need to reinstall anything after editing it.

## Security audit

`SECURITY_AUDIT.md` is a step-by-step runbook an agent follows to audit the repo and fix what it finds. It covers secrets, auth, database/RLS rules, injection, dependencies and CI, and platform config, and it ends with a report at `docs/security/audit-YYYY-MM-DD.md`.

Run it with `/security-audit` for all phases, or `/security-audit phase 3` for a single phase. You can also tell any agent: "Follow SECURITY_AUDIT.md."

The agent fixes code on its own. It asks before rewriting git history or touching a remote database. It lists keys you need to rotate yourself.
