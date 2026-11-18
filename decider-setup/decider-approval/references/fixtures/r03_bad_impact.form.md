<!-- r03: pipeless impact refuses | consult-only, never executed -->
## command
cp ~/.hermes/cache/scratch/decider-form/template.form.md ~/.hermes/cache/scratch/decider-form/r_copy.form.md

## permanent_state_change
no

## irreversible
no

## touches_persistent_or_live
no

## affects_live_process
no

## can_restore_easily
yes

## why
Gate test: this form must be refused mechanically before any POST.

## effects
Scratch-to-scratch file copy; nothing outside the cache dir.

## tested
Yes — plain cp between two existing cache paths.

## impact
one scratch file, no pipes here

## blast_radius
None beyond scratch litter.

## risks
Scratch litter => single namespaced file in auto-pruned cache dir

## alternative
none — refusal itself is the expected outcome
