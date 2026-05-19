# Junos Read-Modify-Write Local-Preference Lab

When a single Junos `then` block contains multiple arithmetic actions on
the same attribute, does each later action see the running (in-progress)
value, or does it always read the original attribute? This is the
"Suspicious Omission" raised in
`working/intermediateAttributes.md` for read-modify-write operations.

## Hypothesis

Junos composes within-term actions sequentially — i.e., later actions
read the value left by earlier actions. The TRP (Targeted Route Policy)
implementation in Batfish, on platforms where `useOutputAttributes` is
false and intermediate attributes are not enabled, instead reads the
_original_ attribute for each action. If that hypothesis is right, this
lab will show a divergence between Junos and the current Batfish model
for any policy that chains arithmetic operations.

## Topology

```
sender (AS 65001) --- dut (AS 65002)
       ge-0/0/0  <->  ge-0/0/0
       10.0.12.0      10.0.12.1
```

No collector is needed: local-preference and metric are both either
non-transitive across eBGP or not the question we're asking. The
observation is on `dut` only.

## Test Routes

`sender` originates these prefixes via static and exports all to `dut`
without modification (so they all arrive with localpref=100, metric=0,
AS-path `65001`).

| Prefix       | dut import term     | Compound action(s)                                    |
| ------------ | ------------------- | ----------------------------------------------------- |
| 10.20.0.0/24 | `BASELINE`          | (none — baseline)                                     |
| 10.20.1.0/24 | `TWO-ADDS`          | `local-preference add 50; local-preference add 50;`   |
| 10.20.2.0/24 | `SET-THEN-ADD`      | `local-preference 300; local-preference add 50;`      |
| 10.20.3.0/24 | `SET-THEN-SUBTRACT` | `local-preference 300; local-preference subtract 50;` |
| 10.20.4.0/24 | `METRIC-SET-ADD`    | `metric 200; metric add 50;`                          |
| 10.20.5.0/24 | `DOUBLE-PREPEND`    | `as-path-prepend "65002 65002";`                      |

## What to Observe

For each prefix, run on `dut`:

```
show route 10.20.X.0/24 extensive | display json
```

and read off `local-preference`, `metric`, and `as-path`. The expected
values under each interpretation are:

| Prefix       | If sequential RMW (Junos hypothesis) | If read-original each time                         |
| ------------ | ------------------------------------ | -------------------------------------------------- |
| 10.20.0.0/24 | localpref=100                        | localpref=100                                      |
| 10.20.1.0/24 | localpref=200                        | localpref=150                                      |
| 10.20.2.0/24 | localpref=350                        | localpref=150                                      |
| 10.20.3.0/24 | localpref=250                        | localpref=50                                       |
| 10.20.4.0/24 | metric=250                           | metric=50                                          |
| 10.20.5.0/24 | as-path `65002 65002 65001`          | as-path `65002 65002 65001` (same — single action) |

The `DOUBLE-PREPEND` row is included as a baseline: a multi-ASN
`as-path-prepend` is a single action (one read, one write), so both
interpretations agree. It is here to confirm that prepend itself
behaves as expected before we read into divergent results elsewhere.

If the actual values match the sequential-RMW column, that is empirical
evidence that Batfish should chain reads for these compound actions on
Junos (or, equivalently, set `useOutputAttributes` for Junos so that
output and intermediate become the same store).

## Running

```
lab_builder validate topology.clab.yml --checks checks.yaml
```

The checks confirm BGP comes up and all 6 routes land in `inet.0` on
`dut`. The substantive results live in `show route extensive` output;
see Results below for what was observed.

## Results

Deployed 2026-05-19 on vJunos-router 25.4R1.12 (containerlab on EC2).
All 8 checks passed. Substantive observations from
`show route <prefix> extensive | display json` on `dut`:

| Prefix       | Compound action(s)                                    | localpref | metric | AS path                                            |
| ------------ | ----------------------------------------------------- | --------- | ------ | -------------------------------------------------- |
| 10.20.0.0/24 | (none — baseline)                                     | 100       | —      | 65001 I                                            |
| 10.20.1.0/24 | `local-preference add 50; local-preference add 50;`   | **150**   | —      | 65001 I                                            |
| 10.20.2.0/24 | `local-preference 300; local-preference add 50;`      | **150**   | —      | 65001 I                                            |
| 10.20.3.0/24 | `local-preference 300; local-preference subtract 50;` | **50**    | —      | 65001 I                                            |
| 10.20.4.0/24 | `metric 200; metric add 50;`                          | 100       | **50** | 65001 I                                            |
| 10.20.5.0/24 | `as-path-prepend "65002 65002";`                      | 100       | —      | 65002 65002 65001 I (Looped: 65002 — still active) |

### Interpretation

Junos exhibits **read-original-each-action** semantics for the
arithmetic and set actions in this lab. Concretely:

- `add 50; add 50` produced **150**, not 200 — each `add` reads the
  original local-pref (100) rather than chaining off the running value.
- `set 300; add 50` produced **150**, not 350 — even when an explicit
  `set` writes 300, the later `add 50` still reads the _original_ 100
  and the result is 150 (effectively, the later write wins because it
  is also based on the original input).
- `set 300; subtract 50` produced **50**, not 250 — same shape as above.
- `metric 200; metric add 50` produced **50**, not 250 — same behavior
  on MED.

The multi-ASN `as-path-prepend "65002 65002"` worked as a single action,
producing `65002 65002 65001`. (Junos flagged the loop but kept the
route active since the prepend was self-applied at import.)

This empirical result aligns with the current Batfish TRP behavior for
platforms where `useOutputAttributes` is false and intermediate
attributes are _not_ enabled — i.e., the Junos conversion's current
default. So for these specific within-`then` compound writes, the
"Suspicious Omission" raised in `working/intermediateAttributes.md`
is **not actually a bug for Junos** (whatever it is for IOS, where
the same hypothesis was confirmed).

The absolute values match the read-original column in this README's
hypothesis table. There is no divergence between Junos and the
existing Batfish model for this case — Batfish's modeling appears
correct for Junos here.

### Batfish triage

`pytest lab_tests/test_labs.py --labname=junos_rmw_localpref` against
local Batfish: **13 passed, 0 skipped, no sickbay**. The BGP-rib-routes
test compares Batfish-predicted local_preference / MED / as-path
against the device's actual values per prefix; all match. So Batfish's
Junos conversion already produces the same 150 / 50 / 150 / 50 that the
device produces — there is no modeling discrepancy to file for this
case.

### Companion data

- Snapshot: `snapshots/junos_rmw_localpref/`
