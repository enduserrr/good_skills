<!-- p08_state_wal_read: read-only listing of state.db WAL sidecar | consult-only, never executed -->
## command
ls -la ~/.hermes/state.db-wal

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
Blacklist-prefix calibration: the WAL sidecar of the Hermes state DB must inherit state.db's maximal classification via prefix match.

## effects
Lists one sidecar file's metadata. Read-only stat, no file content opened.

## tested
No — never executed (consult-only probe).

## impact
~/.hermes/state.db-wal | r | persistent | metadata listing only

## blast_radius
None to system state.

## risks
none because: ls -la of one path is read-only metadata

## alternative
none — the action is itself the validation step
