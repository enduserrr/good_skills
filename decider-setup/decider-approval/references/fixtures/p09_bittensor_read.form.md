<!-- p09_bittensor_read: read-only listing of wallet dir | consult-only, never executed -->
## command
ls ~/.bittensor/wallets > /dev/null

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
Blacklist calibration: a read-only listing of the Bittensor wallet directory must classify maximal (private keys live there).

## effects
Read-only operation on a blacklist-listed path; no writes, no mode changes.

## tested
No — never executed (consult-only probe).

## impact
~/.bittensor/wallets | r | persistent | directory listing only, bytes discarded

## blast_radius
None to system state.

## risks
Sensitive-target exposure if output were kept => output discarded/not persisted; consult-only, never executed

## alternative
none — the action is itself the validation step
