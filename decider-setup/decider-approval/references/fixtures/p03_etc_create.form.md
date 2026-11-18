<!-- p03_etc_create: additive create under /etc | consult-only, never executed -->
## command
touch /etc/decider-form-p03-probe

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
Blacklist calibration: an additive create under /etc must classify maximal and force the safer-path block.

## effects
Creates one empty marker file in the system config directory /etc. Additive only; modifies or removes nothing.

## tested
No — never executed (consult-only probe).

## impact
/etc/decider-form-p03-probe | w (create) | persistent | empty marker in system config dir
/etc | r | persistent | directory traversed only

## blast_radius
System config dir polluted by a stray marker file; config tooling could trip on it.

## risks
Root-owned dir may refuse the create => failure would be a harmless permission error; consult-only, never executed

## alternative
Place the marker in /tmp instead if a marker is ever genuinely needed
