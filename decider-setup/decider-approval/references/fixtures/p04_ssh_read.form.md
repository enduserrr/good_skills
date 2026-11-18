<!-- p04_ssh_read: read-only cat of SSH trust store | consult-only, never executed -->
## command
cat ~/.ssh/authorized_keys > /dev/null

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
Blacklist calibration: a read-only touch of the SSH trust store must still classify maximal (privacy-sensitive target).

## effects
Reads the authorized_keys file and discards the bytes to /dev/null. No write, no mode change, no network.

## tested
No — never executed (consult-only probe).

## impact
~/.ssh/authorized_keys | r | persistent | read-only, bytes discarded

## blast_radius
None to system state; contents would be exposed only to the reading process.

## risks
Sensitive-data exposure if output were redirected => command hardcodes /dev/null; consult-only, never executed

## alternative
Inspect via sshd config tooling only if a real key audit is ever needed
