<!-- r06: contradictory removal refuses | consult-only, never executed -->
## command
rm -rf ~/tmp/r06-target

## permanent_state_change
yes

## irreversible
yes

## touches_persistent_or_live
yes

## affects_live_process
no

## can_restore_easily
yes

## why
Gate test: removal marked irreversible=yes yet can_restore_easily=yes must refuse as contradictory.

## effects
Consult-only: recursive removal of a hypothetical ~/tmp target.

## tested
Yes — plain cp between two existing cache paths.

## impact
~/tmp/r06-target | remove | persistent | hypothetical target removed

## blast_radius
None — never executed; the contradiction itself is the test.

## risks
Scratch litter => single namespaced file in auto-pruned cache dir

## alternative
none — refusal itself is the expected outcome
