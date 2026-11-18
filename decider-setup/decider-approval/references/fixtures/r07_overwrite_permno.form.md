<!-- r07: overwrite marked permanent=no must refuse | consult-only -->
## command
printf 'r7' > ~/.hermes/cache/scratch/decider-form/p02_copy.form.md

## permanent_state_change
no

## irreversible
no

## touches_persistent_or_live
yes

## affects_live_process
no

## can_restore_easily
yes

## why
Gate test: an OVERWRITE of an existing file marked permanent_state_change=no must refuse as contradictory.

## effects
Replaces the content of an existing scratch file. Not additive: the previous bytes are gone.

## tested
No — never executed; consult-only.

## impact
~/.hermes/cache/scratch/decider-form/p02_copy.form.md | w (overwrite) | temporary | existing file content replaced

## blast_radius
Scratch-only file content lost; regenerable.

## risks
Content loss => target is scratch junk, regenerable; consult-only, never executed

## alternative
Write to a brand-new name instead.
