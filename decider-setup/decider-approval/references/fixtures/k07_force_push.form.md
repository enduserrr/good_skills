<!-- k07_force_push: force-push a shared working branch | consult-only, never executed -->
## command
git -C ~/git/tf-v11 push --force origin tf/main

## permanent_state_change
yes

## irreversible
no

## touches_persistent_or_live
yes

## affects_live_process
no

## can_restore_easily
yes

## why
Mid-catastrophe calibration: rewriting the remote history of the canonical working branch must route to a guarded path.

## effects
Force-pushes local tf/main over origin/tf/main, discarding any remote-only commits. Remote branch history rewritten.

## tested
No — never executed (consult-only probe).

## impact
origin tf/main (remote branch on GitHub) | w (overwrite history) | persistent | remote-only commits orphaned
~/git/tf-v11/.git | r | persistent | local repo read only

## blast_radius
Lost remote commits and broken collaborator clones until history is reconciled.

## risks
Remote commit loss => force-with-lease after a fetch is the guarded variant; consult-only, never executed

## alternative
push --force-with-lease after fetching and confirming no remote-only commits
