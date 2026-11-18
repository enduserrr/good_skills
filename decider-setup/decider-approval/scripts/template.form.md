# DECIDER PERMISSION REQUEST FORM — fill the sections below only.
<!-- Fixed text (GOAL, standing policy, questions) is hardcoded in consult.py and never retyped.
     Fill rules:
  - command: the EXACT command/action string, verbatim. Never paraphrase.
  - BINARY FIELDS (permanent_state_change, irreversible, touches_persistent_or_live,
    affects_live_process, can_restore_easily): answer with exactly one word, yes or no.
    Sentences, "n/a", or any other token are refused before consult.
      permanent_state_change: does the action change state that persists beyond this
        agent run (files, configs, DBs, installs — even regenerable ones)?
      irreversible: is that change undoable? no existing backup/regeneration path => yes.
      touches_persistent_or_live: is any target of persistent purpose beyond the agent's
        lifetime — system/program critical files, configs, live services, user data?
      affects_live_process: does it start/stop/signal/restart a running process or service?
      can_restore_easily: if it goes wrong, restorable in minutes from a backup or
        regeneration that EXISTS right now?
  - why: max 400 chars, THIS probe only ("to run X to verify Y"). No project backstory.
  - effects: neutral and complete — include effects that argue against running.
  - tested: "Yes — <where/how validated>" or "No — <why not>".
  - impact: one line per touched file/dir/env/service/port:
            "path | perms (r/w/x/remove/copy) | temporary|persistent | note".
            Must be exhaustive; a missing entry invalidates the consult.
  - blast_radius: what breaks if this goes wrong.
  - risks: one line per risk: "risk => mitigation".
           Only if genuinely none: "none because: <reason>".
  - alternative: safer path, or "none".
  Extreme-caution rule (enforced mechanically in consult.py, never by rewording):
  a permanent/irreversible change landing on a persistent-or-live target — or any
  impact path on the MAXIMAL-caution list — can never be approved as-is; a decider
  RUN is forced to the safer-path block. Paths ONLY under the MINIMAL-caution list
  stay lenient even with paranoid flags.
-->

## command

## permanent_state_change
<yes|no>

## irreversible
<yes|no>

## touches_persistent_or_live
<yes|no>

## affects_live_process
<yes|no>

## can_restore_easily
<yes|no>

## why

## effects

## tested

## impact

## blast_radius

## risks

## alternative
