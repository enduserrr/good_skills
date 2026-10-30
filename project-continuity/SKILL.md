---
name: project-continuity
description: Use when entering any repo to develop or modify code.
version: 0.1.0
author: ais (enduserrr), NoSleepHermes
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [sessions, logging, continuity, questbook]
    related_skills: []
---

# Project Continuity (QUESTBOOK)

Every project repo keeps a `QUESTBOOK.md` at its root: an append-only log of who
worked in the repo, what they changed, and which skills helped. Goal: anyone
(agent or human) entering the repo sees the previous session's state in 30
seconds. Rule of thumb: **if you will touch anything, log it; if you only read,
don't.**

## When to Use

- Trigger: you are about to create, modify, or delete any file in a repo, or run
  any state-changing command there (installs, chmod, DB writes, builds that
  write artifacts).
- Read-only sessions (browsing, searching, reading code, answering questions)
  log NOTHING. No entry, no status.
- Don't use for: scratch directories outside any real project.

## Procedure

1. **On entry — before your first non-read action:**
   - If `QUESTBOOK.md` does not exist, create it with the header
     `# QUESTBOOK OF PROJECT CONTINUITY` plus the format note below.
   - Read the last 1-2 entries: they may carry unfinished state that affects
     your task.
   - Append one ENTRY:
     ```
     ### ENTRY - <agent_name>, <session_id>, <YYYY-MM-DD>
     * Model: <model name>
     * Skills: <comma-separated names currently in context>
     * Task: <one line describing the task>
     ```
   - Completion criterion: the ENTRY is on disk before any file is modified.
2. **On exit — task done, or session ending:**
   - Append one STATUS directly under your ENTRY:
     ```
     ### STATUS - <agent_name>, <session_id>, <YYYY-MM-DD>
     * Skills: <names used, with [+] if extremely useful / [-] if useless>
     * Files: <every file created, modified, deleted, chmod'd, or otherwise
       impacted — anything beyond read-only; write "none" if none>
     ```
   - Completion criterion: every file you touched is listed, including files
     you only created.

## Rules

- One ENTRY + one STATUS per session per repo.
- Append-only: never edit or delete past entries.
- Log facts, not intent: "modified db.py schema init" beats "will look into db".
- Subagents/delegated children: the parent logs one entry covering the delegated
  work, listing the files the children touched.
- Found a repo without QUESTBOOK.md? Create it — that IS the protocol.
- An explicit user instruction limiting changes ("only create X.md", "do not make other changes") overrides the logging protocol for that session: honor the restriction and log nothing rather than writing QUESTBOOK.md against it.
- Commit QUESTBOOK.md along with your work when the repo tracks docs; otherwise
  leave it untracked.

## Pitfalls

- Session ended abruptly with no STATUS (crash, interruption, user stopped it):
  next session in that repo appends the missing STATUS marked "(late)".
- Multi-repo task: each repo gets its own ENTRY/STATUS in its own QUESTBOOK.md.
- QUESTBOOK.md is context, not a substitute for a plan file or commit messages.
