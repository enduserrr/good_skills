---
name: development-safety
description: "Avoid impacting live systems; develop on copies first."
version: 1.1.0
author: NoSleepHermes (user rule, Sep 2026)
license: MIT
metadata:
  hermes:
    tags: [safety, development-workflow, live-systems, integrity, isolation, file-hygiene]
    related_skills: [systematic-debugging, test-driven-development]
---

# Development Safety — never impact live systems

## Hard rule (user-stated, Sep 2026 — 'remember and internalize this deep')

> NEVER let development impact anything that is in active use or otherwise
> being depended on by anything — including Hermes (you) and the OS itself.
> ALWAYS develop, test, and verify using mock/scrap files. If needed, make a
> copy of a real existing file to use during development, and only once
> verified let new or modified code interact with outside resources. The
> most valuable goal is always to preserve system functionality and
>integrity, and to prevent accidental, unexpected, and/or irreversible damage.

## Procedure

- Develop and test ONLY on mocks/scrap files; for real data, work on a COPY and
  let modified code touch live resources only after verification passes.
- Set output redirections / target state BEFORE executing anything that writes
  (a redirect set after `exec_module` is overwritten by the import).
- Before touching a live resource, state what it is and why the operation is
  safe; if unsure, stop and verify first.

### Approval gates & user participation (install-heavy tasks)

- Preflight the consent list at task start: before running the pipeline,
  enumerate every step that needs user approval (curl|sh installers, sudo,
  inline-interpreter invocations) and get one go-ahead covering them. An
  approval prompt that fires mid-run on an unattended step burns ~5 minutes
  and blocks; a silent timeout is NOT consent — never rephrase-and-retry a
  blocked command, surface it to the user instead.
- Run long installs (rustup, cargo install, image pulls) as background
  terminal jobs with notify=true; a foreground call that waits on a pending
  approval is the failure mode above.
- When the user opts in to hands-on participation mid-task, stop executing
  gated steps autonomously: hand exact commands for the parts he runs himself
  (per his admin/sudo rule), summarize verified state, and propose a split
  (docs/research by agent, installs/elevated actions by user) — do not keep
  driving interactive steps solo.
- **Do not work around a denied command.** When a command is blocked (user
  denial or approval layer), the attempted OUTCOME is off the table, not just
  the phrasing: rephrasing it, moving it to a script file, extracting the
  value via a different tool, or a python one-liner that reads the same file
  are all retries of the same outcome. The block usually marks a deliberate
  boundary (e.g. redacted secrets/hosts in a repo) — circumventing it silently
  overrides the user's consent. If the underlying goal is still legitimate,
  stop, disclose exactly what ran and what did not, and ask the user for an
  alternative route (e.g. he pastes the command or credentials himself).

### Derived-copy variants (patches, candidate code)

- When a candidate modification is a PATCH against a live component, build
  the variant as fresh copy + reapply patch at setup time (derived, never
  hand-edited) — a hand-patched copy silently diverges from the live source
  it claims to test, and a stale patch mis-applies. Prefer a deterministic
  generator script (exact-anchor replaces + apply-check + compile-check) over
  hand-built diffs; it fails loudly at a drifted anchor instead of
  mis-applying. Keep the patch file in version control next to its offline
  tests.
- Validate the variant OFFLINE first (no live traffic, no API cost) — drive
  it through the same loader the live flow uses, on fixtures shaped like the
  REAL traffic (raw persisted messages, not idealized forms the flow never
  produces; a re-write keyed on an intermediate form is dead code when the
  live flow re-derives from raw inputs each time).
- An offline test can pass while the mechanism is still dead in the live
  flow — after any variant run, confirm the mechanism actually fired (engine
  accounting / explicit event labels) BEFORE reading the headline numbers; a
  performance delta with zero mechanism events is path variance, not the
  variant's effect. Report invalid runs as invalid with the reason — never
  fold them into results.

*Note: this file was found truncated on disk (2026-09-08); the tail was
reconstructed 2026-09-09 from the user's original hard-rule text.
Reconstruction by `ais (enduserrr) + NoSleepHermes` — confirm or correct.*
