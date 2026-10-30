---
name: test-driven-development
description: "TDD: enforce RED-GREEN-REFACTOR, tests before code."
version: 2.0.0
author: NoSleepHermes (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [testing, tdd, development, quality, red-green-refactor]
    related_skills: [systematic-debugging, subagent-driven-development]
---

# Test-Driven Development (TDD)

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

If you didn't watch the test fail, you don't know if it tests the right thing.
**Violating the letter of the rules is violating the spirit of the rules.**

Wrote code before the test? **Delete it. Start over.**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from tests. Period.

**Always applies:** new features, bug fixes, refactoring, behavior changes.
**Exceptions (ask the user first):** throwaway prototypes, generated code, config files.

Thinking "skip TDD just this once"? Stop. That's rationalization.

## Red Flags — STOP and Start Over

If you catch yourself doing or saying any of these, **delete the code and restart with TDD**:

- Code before test
- Test after implementation
- Test passes immediately on first run
- Can't explain why the test failed
- Tests added "later"
- "Just this once"
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "Keep as reference" / "adapt existing code"
- "Already spent X hours, deleting is wasteful"
- "TDD is dogmatic, I'm being pragmatic"
- "This is different because…"

**All of these mean: Delete code. Start over with TDD.**

## Red-Green-Refactor

### 1. RED — write one minimal failing test

- One behavior per test; "and" in the name → split it
- Clear name describing behavior, not implementation
- Real code, not mocks (unless truly unavoidable)
- Expected values: write the expression that computes them (`32768/65535`), never hand-transcribed decimals — transcription rounding makes correct code fail

```python
# GOOD: clear name, real behavior, one thing
def test_retries_failed_operations_3_times():
    attempts = 0
    def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3: raise Exception('fail')
        return 'success'
    result = retry_operation(operation)
    assert result == 'success'
    assert attempts == 3

# BAD: vague name, tests the mock not the code, ignores retry count/timing
def test_retry_works():
    mock = MagicMock(side_effect=[Exception(), Exception(), 'success'])
    assert retry_operation(mock) == 'success'
```

### 2. Verify RED — MANDATORY, NEVER SKIP

```python
terminal("pytest tests/test_feature.py::test_name -v")
```

Confirm:
- Test **fails** (not errors from typos)
- Failure message is what you expected
- It fails **because the feature is missing**

**Passes immediately?** You're testing existing behavior. Fix the test.
**Errors out?** Fix the error, re-run until it fails correctly.

> You must actually watch this fail. A test you never saw fail proves nothing.

### 3. GREEN — simplest code that passes, nothing more

```python
def add(a, b): return a + b          # GOOD: nothing extra

def add(a, b):                       # BAD: logging is beyond the test
    result = a + b
    logging.info(f"Adding {a} + {b} = {result}")
    return result
```

**Cheating is OK in GREEN:** hardcode return values, copy-paste, duplicate code,
skip edge cases. We'll fix it in REFACTOR.

Don't add features, refactor other code, or "improve" beyond the test.

### 4. Verify GREEN — MANDATORY

```python
terminal("pytest tests/test_feature.py::test_name -v")  # this test
terminal("pytest tests/ -q")                            # regressions
```

Confirm: test passes, other tests still pass, output pristine (no errors/warnings).

**Never gate a commit on a piped test command** (`pytest … | tail && git commit`)
— the pipeline's exit code is the pipe's, so a failing suite still commits. Run
the suite unpiped (the terminal auto-truncates display and saves the full
output) or check `${PIPESTATUS[0]}`.

**Test fails?** Fix the code, not the test.
**Other tests fail?** Fix regressions now.

### 5. REFACTOR — after green only

Remove duplication, improve names, extract helpers, simplify expressions.
Keep tests green throughout. Add no behavior.

**Tests fail during refactor?** Undo immediately. Take smaller steps.

### 6. Repeat — one cycle per behavior

## Avoid Horizontal Slices

Do **not** write all tests first and then all implementation. That's horizontal
slicing: RED becomes "write a pile of imagined tests," GREEN becomes "make the
pile pass." It produces brittle tests, because they're designed before the
implementation has taught you what behavior and interface actually matter.

```text
WRONG: RED: test1, test2, test3, test4  →  GREEN: impl1, impl2, impl3, impl4
RIGHT: RED→GREEN test1→impl1
       RED→GREEN test2→impl2
       RED→GREEN test3→impl3
```

Each cycle is a vertical tracer bullet: one end-to-end behavior slice that proves
the path works, teaches you the interface, and keeps the next test grounded in
what you just learned.

## Rationalizations → Reality

| Excuse | Reality |
|---|---|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests-after pass immediately, proving nothing: may test the wrong thing, test implementation not behavior, miss forgotten edge cases. You never saw it catch a bug. |
| "Tests after achieve same goals — spirit not ritual" | No. Tests-after ask "what does this do?" (biased by your implementation — you test what you built, not what's required). Tests-first ask "what *should* this do?" and force edge-case discovery before implementing. |
| "Already manually tested" | Ad-hoc ≠ systematic: no record of what you tested, can't re-run when code changes, easy to forget cases under pressure. "It worked when I tried it" ≠ comprehensive. |
| "Deleting X hours is wasteful" | Sunk cost fallacy — the time is already gone. Your choice: delete and rewrite with TDD (high confidence), or keep it and add tests after (low confidence, likely bugs). The waste is keeping code you can't trust. |
| "Keep as reference, write tests first" | You'll adapt it. That's testing after. **Delete means delete.** |
| "Need to explore first" | Fine. Throw away the exploration, then start with TDD. |
| "Test hard = design unclear" | Listen to the test. Hard to test = hard to use. |
| "TDD is dogmatic; I'm pragmatic" | TDD *is* pragmatic: finds bugs before commit (faster than debugging after), prevents regressions, documents behavior, enables fearless refactoring. "Pragmatic" shortcuts = debugging in production = slower. |
| "Manual test faster" | Manual doesn't prove edge cases. You'll re-test every change. |
| "Existing code has no tests" | You're improving it. Add tests for the code you touch. |

## When Stuck

| Problem | Solution |
|---|---|
| Don't know how to test | Write the wished-for API. Write the assertion first. Ask the user. |
| Test too complicated | Design too complicated. Simplify the interface. |
| Must mock everything | Code too coupled. Use dependency injection. |
| Test setup huge | Extract helpers. Still complex? Simplify the design. |

## Testing Anti-Patterns

- **Testing mock behavior instead of real behavior** — mocks verify interactions, not replace the system under test
- **Testing implementation details** — test behavior/results, not internal method calls
- **Happy path only** — always test edge cases, errors, and boundaries
- **Brittle tests** — verify behavior, not structure; refactoring shouldn't break them

## Hermes Integration

**Running tests** — use the `terminal` tool at each step:

```python
terminal("pytest tests/test_feature.py::test_name -v")  # RED: verify failure
terminal("pytest tests/test_feature.py::test_name -v")  # GREEN: verify pass
terminal("pytest tests/ -q")                            # full suite: no regressions
```

**delegate_task** — enforce TDD in the goal when dispatching subagents:

```python
delegate_task(
    goal="Implement [feature] using strict TDD",
    context="""Follow test-driven-development skill:
    1. Write failing test FIRST
    2. Run test to verify it FAILS
    3. Write minimal code to pass
    4. Run test to verify it passes
    5. Refactor if needed
    6. Report the RED and GREEN command output (do not commit — see fan-out rules below)

    Project test command: pytest tests/ -q
    Project structure: [describe relevant files]""",
    toolsets=['terminal', 'file'])
```

### Parallel TDD fan-out (many agents, one repo)

- **Write the shared contract first.** Commit a types-only module (e.g. `src/core/types.ts`) before dispatching; every child imports it instead of redefining shapes. Parallel agents that each invent their own interfaces produce code that typechecks alone and fails at the seams.
- **One owner per file.** List the exact paths each child may create and forbid everything else — config, lockfile, and the other children's modules.
- **Children never commit.** Concurrent `git add`/`commit` in one worktree races on `index.lock`; have the parent verify and commit once per wave.
- **Children run only their own test file** (`npx vitest run tests/unit/x.test.ts`), never the whole suite or a build: a sibling module that has not landed yet turns the suite red for reasons the child cannot fix.
- **Pre-install dependencies before dispatching.** A child running `npm install` mid-wave rewrites the lockfile under its siblings.
- **Wave by dependency order:** pure leaf modules in parallel → consumers → integration/E2E. Four to five agents per wave is the practical ceiling before review cost exceeds the parallelism win.
- **Check `delegation.model` in `~/.hermes/config.yaml` before dispatching.** A pinned value silently overrides the parent model, so children run on a different model than the user asked for. Align it with `hermes config set delegation.model <model>` (and `delegation.provider`).

**systematic-debugging** — bug found? Write a failing test reproducing it, then
follow the TDD cycle. The test proves the fix and prevents regression.
**Never fix bugs without a test.**

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] **Watched each test fail before implementing**
- [ ] Each test failed for the expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered

Can't check all boxes? You skipped TDD. Start over.

## Final Rule

```
Production code → test exists and failed first
Otherwise → not TDD
```

No exceptions without the user's explicit permission.
