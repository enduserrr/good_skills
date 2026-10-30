# Live data-trail hygiene — never write test values into a live JSONL

## The trap

When building/verifying a **read-only reporter** over a live append-only
data trail (e.g. a JSONL accounting log a plugin writes), it is tempting to
append a synthetic test line directly into the live file to "see the reader
handle it". Don't.

This session (Sep 2026): appended a junk test record to the live SOMA
`accounting.jsonl` to sanity-check a new savings reporter. Had to undo it
with `sed -i`; the append raced the plugin's own live writes and the revert
could have clobbered a real record.

## The rule

- Test an output reader against an **in-memory fixture** or a **scratch
  copy** (`cp` to /tmp, point the reader there), never the live file.
- Construct real-shaped objects in memory; don't write to the real path
  even momentarily.
- If you must touch a live file, revert by the exact recorded line and
  verify the count after — never assume append+revert is a no-op.
- Any append to a live file is a defect in the authoring process: fix the
  test setup first, not the live file.

## The non-obvious

When a reporter returns nothing, the bug is often NOT the reporter — it is
the fixture. A single-line oversized blob (e.g. `"x"*40000`) is
incompressible to a line-based compressor, surfacing as No-Change `None`
where `assert out is not None` legitimately fails. Q-qualified class names.
