# Junos Read-Modify-Write Local-Preference Lab

When a Junos `then` block contains both a `set` and an arithmetic
(`add`/`subtract`) action on the same attribute, what does the device
actually do? The original framing of this lab — "does a later action
read the running value or the original?" — turns out to be the wrong
question. Junos resolves the conflict at config time, not at policy
evaluation time.

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

## Running

```
lab_builder validate topology.clab.yml --checks checks.yaml
```

## Results

Deployed 2026-05-19 on vJunos-router 25.4R1.12 (containerlab on EC2).
All 8 checks passed.

### What Junos kept after commit

The first thing to notice is the diff between the configured policy
(`infra/examples/junos-rmw-localpref/configs/dut.cfg`) and what the
device's `show configuration | display set` actually retained
(`snapshots/junos_rmw_localpref/configs/dut/show_configuration_|_display_set.txt`).
For each term that combined a `set` with an arithmetic action, the
`set` is gone:

| Term                | Configured                                            | Retained after commit           |
| ------------------- | ----------------------------------------------------- | ------------------------------- |
| `BASELINE`          | (accept only)                                         | (accept only)                   |
| `TWO-ADDS`          | `local-preference add 50; local-preference add 50;`   | `local-preference add 50`       |
| `SET-THEN-ADD`      | `local-preference 300; local-preference add 50;`      | `local-preference add 50`       |
| `SET-THEN-SUBTRACT` | `local-preference 300; local-preference subtract 50;` | `local-preference subtract 50`  |
| `METRIC-SET-ADD`    | `metric 200; metric add 50;`                          | `metric add 50`                 |
| `DOUBLE-PREPEND`    | `as-path-prepend "65002 65002";`                      | `as-path-prepend "65002 65002"` |

`TWO-ADDS` collapses two identical statements into one (standard
Junos config dedup). The other three rows are the substantive
observation: when an `add`/`subtract` action and a plain `set` action
target the same attribute in the same `then` block, **Junos silently
drops the `set` at commit time and keeps only the arithmetic
action**. The configured `local-preference 300` and `metric 200`
never make it into the running config; the policy evaluator never
sees them.

### Resulting BGP attributes

With those configs in place, observations from `show route <prefix>
extensive | display json` on `dut`:

| Prefix       | Effective action  | localpref | metric | AS path                                            |
| ------------ | ----------------- | --------- | ------ | -------------------------------------------------- |
| 10.20.0.0/24 | (none)            | 100       | —      | 65001 I                                            |
| 10.20.1.0/24 | `add 50`          | **150**   | —      | 65001 I                                            |
| 10.20.2.0/24 | `add 50`          | **150**   | —      | 65001 I                                            |
| 10.20.3.0/24 | `subtract 50`     | **50**    | —      | 65001 I                                            |
| 10.20.4.0/24 | `metric add 50`   | 100       | **50** | 65001 I                                            |
| 10.20.5.0/24 | `as-path-prepend` | 100       | —      | 65002 65002 65001 I (Looped: 65002 — still active) |

Each result is exactly what you'd expect from applying the _retained_
action to the original attribute value (localpref=100, metric=0).
There's no compound semantics to investigate at policy-evaluation
time, because the conflicting actions never coexist by the time the
policy runs.

### Implication for the original question

The "Suspicious Omission" framing in
`working/intermediateAttributes.md` asked whether Junos chains reads
across compound `set`/`add` actions or reads the original each time.
This lab's answer: **the question is moot for Junos**. The device's
config system enforces that the two action types can't coexist on the
same attribute in the same `then` block — only the arithmetic action
survives — so there is no runtime semantics to disagree about.

(Whether the IOS-side bug Todd identified for compound writes still
exists is a separate question; that's a different vendor with a
different config syntax that does not have this commit-time
collapsing behavior.)

### Multi-ASN as-path-prepend

The `DOUBLE-PREPEND` term is unaffected by the collapse — it has only
one action, `as-path-prepend "65002 65002"`. The prepend produced
`65002 65002 65001` as expected. (Junos flagged the loop but kept the
route active since the prepend was self-applied at import.)

### Batfish triage

`pytest lab_tests/test_labs.py --labname=junos_rmw_localpref` against
local Batfish: **13 passed, 0 skipped, no sickbay**. The BGP-rib-routes
test compares Batfish-predicted local_preference / MED / as-path
against the device's actual values per prefix; all match. Batfish
parses the `display set` output, which is post-commit, so it never
sees the dropped `set` statements either — both Batfish and the
device agree because they're operating on the same retained config.

### Companion data

- Source policy: `infra/examples/junos-rmw-localpref/configs/dut.cfg`
- Retained-config snapshot:
  `snapshots/junos_rmw_localpref/configs/dut/show_configuration_|_display_set.txt`
