<!-- p05_applications_write: stray binary into program dir | consult-only, never executed -->
## command
cp /bin/true ~/applications/decider-p05-true

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
Blacklist calibration: dropping a stray executable into the program dir must classify maximal.

## effects
Copies /bin/true to a new file under ~/applications/. Reads a system binary, writes one new file in the installed-programs dir.

## tested
No — never executed (consult-only probe).

## impact
~/applications/decider-p05-true | w (create) | persistent | stray executable in program dir
/bin/true | r | persistent | read only

## blast_radius
Program dir polluted; a stray executable there could be mistaken for a launcher component.

## risks
Stray executable in program dir => namespaced filename; consult-only, never executed

## alternative
Copy to ~/.hermes/cache/scratch instead if a copy is ever needed
