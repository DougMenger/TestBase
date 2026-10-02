# Security Audit Runbook

**Agent instructions:** this file is your task. Run Phase 0 through Phase 7 **in order**. In each phase: find → fix → verify → record. Then move to the next phase. Don't skip a phase silently. If one doesn't apply to this stack, record `N/A — <reason>` and continue.

Invoke with `/security-audit` (all phases) or `/security-audit phase 3` (one phase; still run Phase 0 first for context).

---

## Operating rules (apply to every phase)

1. **Evidence or it didn't happen.** Every finding cites a location: `file:line`, commit SHA, table name, bucket name, or config key. Don't report "might be vulnerable" without pointing at code. If you can't confirm a finding, label it `UNVERIFIED` and say what would confirm it.
2. **Never reproduce a secret value.** In chat, the report, commit messages, and code comments, redact secrets to the first 4 characters + `…` (e.g. `sk_l…`).
3. **Exploit only what you own.** Run attack steps only against local or dev instances (local server, `supabase start`, test accounts you create). **Never send exploit traffic to production or third-party systems.** If no local target exists, write the exact exploit steps but don't run them.
4. **Corrective-action tiers:**

   | Tier | What | Agent behavior |
   |---|---|---|
   | **Auto-fix** | Code and config changes inside the repo: parameterize queries, add auth/ownership checks, escape output, add validation, add `.gitignore` entries, write new RLS migration files, add security headers, pin dependencies (patch/minor). | Apply the fix. Add a regression test, or a reproduction check that now fails, where feasible. Re-run the detection to confirm. |
   | **Ask first** | Git history rewrites (`git filter-repo`, BFG) and force-pushes; applying migrations to any shared, staging, or prod DB; major-version dependency upgrades; changes in a provider dashboard (Supabase, Auth0, Clerk, Vercel…); deleting data or files the app may rely on. | Prepare the exact command or patch. Stop and ask. Record it as `Awaiting approval`. |
   | **Human-only** | Rotating and revoking keys, tokens, and passwords; anything needing account access you don't have. | List it with exact steps. Record it as `Needs human`. |

5. **Commits.** Work on the session's worktree branch (see `CLAUDE.md`), never directly on `main`. Make one commit per phase that has fixes: `security(phaseN): <summary>`. Run the project's tests and linter before each commit. A fix that breaks the build isn't a fix.
6. **Severity scale.** Use it consistently:
   - **CRITICAL**: exploitable now by an unauthenticated or any logged-in user. Leads to account takeover, data of other users, admin access, RCE, or a live secret.
   - **HIGH**: exploitable with modest effort or one precondition. Significant data or privilege impact.
   - **MEDIUM**: defense-in-depth gap, or exploitable only in narrow conditions.
   - **LOW**: hardening or hygiene. No direct exploit path.
7. **Running log.** Keep findings in a working list as you go. Phase 7 turns it into the report.

---

## Phase 0: Recon

Build the map the later phases depend on.

1. **Stack:** languages, frameworks (Next.js, Express, FastAPI, Django, Rails…), auth provider (Supabase Auth, Auth0, Clerk, NextAuth, Firebase, custom), database/BaaS (Supabase, Firebase, Postgres via an ORM, Mongo…), file storage, hosting, CI.
2. **Entry points:** every route, API handler, server action, RPC, edge/serverless function, webhook receiver, cron/queue job, and CLI script that takes external input.
3. **Trust boundaries:** what runs in the browser vs. on the server; which keys exist and where each is used (public/anon vs. service/secret).
4. **Tools available:** check for `gitleaks`, `trufflehog`, `semgrep`, `npm`/`pnpm`/`pip-audit`/`osv-scanner`, and the `supabase` CLI. Use them when present; fall back to grep and manual review when not.

**Output:** a short inventory (stack, entry-point list, key inventory, applicable phases). Every later phase uses it.

---

## Phase 1: Exposed secrets

Act as a security researcher hunting for leaked credentials.

1. **Hardcoded secrets** in any tracked file: API keys, tokens, passwords, private keys, connection strings, webhook secrets, JWT signing secrets.
   - Run `gitleaks detect --no-banner` and/or `trufflehog filesystem .` if available. Otherwise, grep for known key prefixes (`sk_live_`, `sk-`, `AKIA`, `ghp_`, `xox`, `AIza`, `-----BEGIN`, `postgres://`, `mongodb+srv://`, `eyJ` JWTs) and high-entropy strings.
   - Also check: CI workflow files, `Dockerfile`/`docker-compose*`, IaC (`*.tf`, `*.tfvars`), `.npmrc`/`.pypirc`, Jupyter notebook outputs, test fixtures, seed files, logs, `.claude/settings*.json`, and MCP server configs.
2. **`.env` files** that are committed or not ignored. `.gitignore` must cover `.env`, `.env.*` (except `.env.example`), `*.pem`, `*.key`, `*.p12`, and service-account JSON. `git ls-files` shows what's actually tracked.
3. **Git history**, even for deleted files: `gitleaks detect --log-opts="--all"` or `trufflehog git file://.`. Fallback: `git log --all -p | grep …`. Cover all branches, tags, and stashes (`git stash list`).
4. **Secrets shipped to the browser:**
   - Client-exposed env vars (`NEXT_PUBLIC_*`, `VITE_*`, `REACT_APP_*`, `EXPO_PUBLIC_*`, `PUBLIC_*`) holding anything secret.
   - Secrets imported into client components.
   - Build output (`dist/`, `build/`, `.next/static`), and source maps deployed to production.
5. **Public/anon keys doing privileged work:**
   - A service-role or secret key used in client code.
   - An anon key relied on for access that only RLS or server checks should grant.
   - Third-party keys (Stripe secret, OpenAI, etc.) callable from the browser.

**Corrective action:**
- *Auto-fix:* move each secret to an env var or secret manager; replace the literal with a lookup; add a `.env.example` with placeholder names; fix `.gitignore`; `git rm --cached` tracked env files; move server-only keys out of client code; disable production source maps. Add prevention: a gitleaks pre-commit hook and/or a CI secret-scan job.
- *Ask first:* purging history with `git filter-repo` plus a force-push. This is optional and secondary; **rotation is the actual fix.**
- *Human-only:* rotation (below).

**Output table:**

| File:line / commit | What leaked (redacted) | How an attacker finds it | Severity | Exact fix | Status |
|---|---|---|---|---|---|

**Rotation list.** A key that ever touched a commit or a client bundle is burned. Hiding it now isn't enough.

| Key (redacted) | Issuer / where to rotate | First exposed (commit/date) | Rotate + revoke steps | Status |
|---|---|---|---|---|

---

## Phase 2: Authentication & authorization

Attack auth like you want in. Walk every path from the Phase 0 entry-point list.

1. **Route coverage.** List every route and API endpoint with: does it verify a valid session server-side? Flag any that skip it.
   - Check middleware matchers for gaps (unmatched paths, trailing slashes, case differences, `/api` routes reachable directly).
   - Check server actions, RPCs, edge functions, and webhook handlers that bypass middleware.
2. **Authorization, not just authentication:**
   - **CRITICAL:** any endpoint that trusts a user ID, org ID, or role from the request (body, query, header, or path) instead of the session.
   - IDOR/BOLA: change the resource ID and see whether you get someone else's object.
   - Admin routes guarded only in the UI.
   - Mass assignment: can `role`, `is_admin`, `credits`, `plan`, or `org_id` be set via the request?
3. **Session handling:**
   - Where tokens live: cookie vs. localStorage. localStorage is readable by any XSS.
   - Cookie flags: `HttpOnly`, `Secure`, `SameSite`.
   - Expiry and refresh-token rotation.
   - Do logout, password change, and email change revoke existing sessions and refresh tokens?
   - CSRF protection on cookie-authenticated state-changing requests.
4. **Token verification:**
   - JWTs are verified, not just decoded (`jwt.decode` / `getSession()` without a server check is a red flag).
   - Algorithm pinned (no `none`, no HS/RS confusion).
   - Signing secret strength; `aud`/`iss` checked.
5. **Password rules:**
   - Minimum length (≥ 8, ideally ≥ 12), breached-password check (HIBP), max length cap (avoid hashing DoS).
   - Hashing algorithm if custom (argon2id/bcrypt/scrypt only).
   - Anything the auth provider offers that's switched off: leaked-password protection, MFA, CAPTCHA, secure email change.
6. **Brute force & enumeration:**
   - Rate limiting or lockout on login, signup, password reset, OTP/magic-link verify, and MFA.
   - Do error messages or response timing reveal whether an account exists?
7. **Password reset & email verification:**
   - Can I reset someone else's password? Check token entropy, single-use, expiry, binding to the user, and Host-header poisoning of the reset link.
   - Can I use the app, or claim an email or domain, with an unverified email?
8. **OAuth/SSO & redirects:**
   - Redirect-URI allowlist; `state`/PKCE present.
   - Open redirect via `?next=`/`?redirect=` after login.
   - Account linking or takeover through an unverified email from an OAuth provider.
9. **Webhooks:** signature verified with a constant-time compare; timestamp/replay window enforced.

**Corrective action:**
- *Auto-fix:* add server-side session checks; derive the user from the session, never from the request; add ownership checks; allowlist writable fields; set cookie flags; verify JWTs properly; add rate limiting; normalize auth error messages; validate redirect targets; verify webhook signatures. Add a test per fix, e.g. "user A gets 403 on user B's resource".
- *Ask first:* auth provider dashboard settings (password policy, leaked-password protection, MFA, session lifetime).

**Output table:**

| Flow / endpoint | Weakness | Exact exploit steps | Severity | Fix | Status |
|---|---|---|---|---|---|

---

## Phase 3: Database & storage access rules

Audit access rules table by table: Supabase RLS, Firebase rules, or the ORM/query layer equivalent.

1. **Inventory:** list every table/collection and whether RLS (or equivalent rules) is enabled.
   - **CRITICAL:** any table reachable with the public/anon key and no RLS.
   - Check grants to `anon`/`authenticated` too (`\dp`, `information_schema.role_table_grants`).
2. **Cross-user read/write test.** For each policy, write the exact query user A runs to read or modify user B's rows. Say whether it works, and test it when local Supabase is available (`supabase start`; create two test users; use each user's JWT with the anon key).
3. **Client-controlled filters:**
   - Flag policies that filter on values the client sends instead of `auth.uid()`.
   - Flag policies that trust `auth.jwt() -> 'user_metadata'`. **Users can edit their own user_metadata.** Use `app_metadata` or a server-owned table instead.
4. **INSERT & UPDATE, not just SELECT:**
   - Can I insert rows owned by another user?
   - Do UPDATE policies have a `WITH CHECK` clause? Without one, I can move a row to another owner.
   - Can I update columns I shouldn't own (`role`, `credits`, `plan`, `is_admin`, `owner_id`)? If so, add column-level privileges or a trigger.
   - Check DELETE too.
5. **RLS bypasses:**
   - `SECURITY DEFINER` functions/RPCs executable by `anon`/`authenticated`, especially those without a fixed `search_path` or an internal ownership check.
   - Views without `security_invoker = true`.
   - Realtime publications that broadcast rows to unauthorized subscribers.
   - Server code using the service-role key with user-controlled filters.
6. **Multi-tenant apps:** org/team membership is checked in every policy, and membership rows can't be self-inserted.
7. **Storage buckets:**
   - Public vs. private.
   - `storage.objects` policies scoped by owner/path (e.g. `(storage.foldername(name))[1] = auth.uid()::text`).
   - Can I list, overwrite, or delete another user's files?
   - Signed-URL expiry.

**Corrective action:**
- *Auto-fix:* write corrected policies as a **new migration file** (never edit applied migrations). Apply it to the local DB only. Re-run the attack queries to prove they now fail; add them as tests (pgTAP or app-level) where feasible.
- *Ask first:* applying the migration to any remote/shared/prod database.

**Output table:**

| Table / bucket | Policy state | Attack query (as user A) | What leaks | Severity | Corrected policy (real SQL) | Status |
|---|---|---|---|---|---|---|

---

## Phase 4: Injection & dangerous sinks

Trace every path where user input (body, query, path params, headers, cookies, uploaded files, webhook payloads, DB values originally written by users, LLM output) reaches something dangerous.

1. **SQL/NoSQL injection:** queries built with concatenation or template literals instead of parameters. Includes raw ORM escapes (`$queryRawUnsafe`, `.raw()`, `sequelize.literal`, `knex.raw` with interpolation) and Mongo operator injection (`{"$ne": null}` in a JSON body).
2. **Code/command execution:** input reaching `eval`, `new Function`, `vm`, `exec`/`execSync`/`spawn` with `shell: true`, `child_process`, `os.system`, `subprocess(..., shell=True)`, or template engines rendering user-supplied templates (SSTI).
3. **File uploads:**
   - Is the filename sanitized?
   - Is the type verified server-side by content, not the extension or the client's MIME type?
   - Is size capped?
   - Can I upload HTML/SVG/executables that are then served from the app origin?
   - Can I path-traverse with `../`, or zip-slip on extraction?
4. **File reads/downloads:** path traversal on any endpoint that reads files by a user-supplied name or path.
5. **XSS:** user content rendered as HTML without escaping. Includes `dangerouslySetInnerHTML`, `v-html`, `innerHTML`, `|safe`/`mark_safe`, markdown renderers without sanitization (check `rehype-raw`, `marked` without DOMPurify), `javascript:` URLs in `href`, and SVG uploads.
6. **SSRF:** server fetching a user-supplied URL (link previews, webhooks, image proxies, imports). Is there an allowlist, and are internal/metadata ranges blocked (`127.0.0.0/8`, `10.0.0.0/8`, `169.254.169.254`, `::1`), including after redirects and DNS rebinding?
7. **Open redirects:** user-controlled redirect targets.
8. **Unsafe deserialization / parsing:** `pickle`, `yaml.load` (non-safe), `Marshal`, Java/PHP deserialization, XML with external entities (XXE), prototype pollution via deep-merge of request bodies.
9. **Other injection:**
   - Header/CRLF injection.
   - Log injection.
   - ReDoS: user input into catastrophic-backtracking regexes.
   - Email header injection.
10. **LLM features (if any):** can prompt injection in user content or fetched pages make the model call tools, read secrets, write to the DB, or exfiltrate data via rendered links/images?
11. **Missing validation:** endpoints with no server-side schema validation (zod/pydantic/etc.) at all. Client-side validation doesn't count.

**Corrective action:**
- *Auto-fix:* parameterize queries; remove eval/shell usage or use argument arrays; sanitize filenames and generate server-side names; verify content type; cap sizes; serve uploads with `Content-Disposition: attachment` or from a separate origin; escape/sanitize HTML (DOMPurify); allowlist URLs and redirects; use safe loaders; add schema validation at every boundary.
- For each fix, add a test proving the example payload now fails.

**Output table:**

| File:line | Input source | What it reaches | Working example payload | Severity | Fix | Status |
|---|---|---|---|---|---|---|

---

## Phase 5: Dependencies & supply chain

1. **Known vulnerabilities:** run `npm audit` / `pnpm audit` / `yarn npm audit` / `pip-audit` / `osv-scanner` as applicable. Report only reachable or runtime dependencies as HIGH+; dev-only issues are MEDIUM at most unless they run in CI with secrets.
2. **Lockfile** committed and used in CI (`npm ci`, `pnpm install --frozen-lockfile`).
3. **Suspicious packages:** typosquats; unexpected `postinstall` scripts; unmaintained packages in auth or crypto paths.
4. **CI/CD (GitHub Actions etc.):**
   - Third-party actions pinned to a commit SHA.
   - Minimal top-level `permissions:`.
   - No `pull_request_target` combined with a checkout of PR code.
   - No secrets exposed to fork PRs.
   - No untrusted input (`github.event.*.title/body`) interpolated into `run:` scripts.
5. **Agent tooling:** `.claude/settings*.json` hooks and MCP server configs. Do they run commands from untrusted sources, auto-install unpinned packages, or grant broad permissions?

**Corrective action:**
- *Auto-fix:* patch/minor upgrades, pin actions to SHAs, tighten `permissions:`, fix script injection in workflows.
- *Ask first:* major-version upgrades and package replacements.

**Output table:**

| Package / file:line | Issue (CVE / misconfig) | Exploit path | Severity | Fix | Status |
|---|---|---|---|---|---|

---

## Phase 6: Platform & configuration hardening

1. **Security headers:**
   - `Content-Security-Policy` (no `unsafe-inline`/`unsafe-eval` for scripts where avoidable).
   - `Strict-Transport-Security`.
   - `X-Content-Type-Options: nosniff`.
   - `frame-ancestors` / `X-Frame-Options`.
   - `Referrer-Policy`.
2. **CORS:** no `*` with credentials; no blindly reflected `Origin`; allowlist only.
3. **Error handling:** no stack traces, SQL errors, or internal paths returned to clients. Debug or dev mode is off in production config.
4. **Logging:** no passwords, tokens, full card numbers, or unnecessary PII in logs or analytics events.
5. **Abuse & cost controls:** rate limits on expensive or costly endpoints (LLM calls, email/SMS sending, file processing, search) and on public forms.
6. **Exposed surfaces:** admin panels, debug endpoints, `/.git`, `.env`, source maps, API docs (Swagger) publicly reachable in production config.

**Corrective action:**
- *Auto-fix:* add headers and CORS allowlists in app/hosting config; add generic error responses; scrub log statements; add rate limiting.
- *Ask first:* hosting dashboard changes.

**Output table:**

| Location | Issue | Impact | Severity | Fix | Status |
|---|---|---|---|---|---|

---

## Phase 7: Verify & report

1. **Re-verify:** re-run every detection from Phases 1–6 (scanners, greps, attack queries, payload tests) and confirm each `Fixed` finding is actually gone. Run the full test suite, linter, and build. Anything that fails re-verification goes back to `Open`.
2. **Write the report** to `docs/security/audit-YYYY-MM-DD.md` (redacted, per rule 2):
   - **Summary:** counts by severity and by status (`Fixed` / `Awaiting approval` / `Needs human` / `Accepted risk` / `Open`).
   - **Phase 0 inventory.**
   - **Each phase's table**, with the commit SHA for every `Fixed` row and `N/A — reason` for skipped phases.
   - **Rotation list** (Phase 1).
   - **Awaiting approval:** each ask-first item with the exact command or patch ready to run.
   - **Residual risk and next steps.**
3. **Commit** the report as `security(report): audit YYYY-MM-DD`, then push the branch.
4. **Final message to the user.** Keep it short, in this order:
   - CRITICAL/HIGH findings still open;
   - keys they must rotate now;
   - items awaiting their approval;
   - what was fixed, with the commit range.
