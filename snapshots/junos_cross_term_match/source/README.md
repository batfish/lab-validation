# Junos Cross-Term Match Lab

Within a single Junos `policy-statement`, when an earlier term writes a
route attribute and falls through (no `accept`/`reject`), can a later
term `from`-match on that updated value? Or do later terms always match
against the original attribute as it arrived from the protocol?

This is the Junos analog of the FRR/Cumulus/Quagga "always-on
intermediate attributes" concern in `working/intermediateAttributes.md`:
those vendors are converted with `SetReadIntermediateBgpAttributes` so
later route-map entries see the updates from earlier ones. For Junos,
the question is empirical — and the answer drives whether the Junos
conversion needs the same flag set.

## Topology

```
sender (AS 65001) --- dut (AS 65002)
       ge-0/0/0  <->  ge-0/0/0
       10.0.12.0      10.0.12.1
```

No collector — observation is on `dut`.

## Method

Each test prefix is sent vanilla from `sender`. On `dut`, a single
`policy-statement CROSS-TERM-IMPORT` contains, for each prefix:

1. A "write" term that modifies the attribute and falls through.
2. A "read" term that `from`-matches on the modified value and tags the
   route with a marker community `MATCHED-*` if the match succeeded.
3. A "default" term that runs only if the read term did not match, and
   tags the route with `UNMATCHED-*`.

The marker community on each route on `dut` reveals which path was taken.

## Test Routes

| Prefix       | Attribute under test | Write action                            | Read condition          |
| ------------ | -------------------- | --------------------------------------- | ----------------------- |
| 10.30.1.0/24 | community            | `community add RED;`                    | `community RED;`        |
| 10.30.2.0/24 | local-preference     | `local-preference 250;`                 | `local-preference 250;` |
| 10.30.3.0/24 | as-path              | `as-path-prepend 65099;`                | `as-path WITH-65099`    |
| 10.30.4.0/24 | (control)            | `community add CONTROL-MARKER; accept;` | n/a                     |

Marker community decoder:

| Community    | Meaning                                              |
| ------------ | ---------------------------------------------------- |
| `65002:1001` | `MATCHED-COMMUNITY` — term 2 saw the community write |
| `65002:1002` | `UNMATCHED-COMMUNITY`— term 2 did NOT see the write  |
| `65002:2001` | `MATCHED-LOCALPREF`                                  |
| `65002:2002` | `UNMATCHED-LOCALPREF`                                |
| `65002:3001` | `MATCHED-ASPATH`                                     |
| `65002:3002` | `UNMATCHED-ASPATH`                                   |
| `65002:9999` | `CONTROL-MARKER` — confirms tagging mechanism works  |

## What to Observe

On `dut`:

```
show route 10.30.0.0/22 detail | display json
```

For each test prefix, read the `communities` field. Exactly one of the
`MATCHED-*` / `UNMATCHED-*` markers (per attribute) should be present.

Interpretation:

- All `MATCHED-*` markers → Junos lets later terms see prior-term writes.
  Batfish's Junos conversion likely needs `SetReadIntermediateBgpAttributes`
  emitted between terms (or `useOutputAttributes` enabled).
- All `UNMATCHED-*` markers → Junos terms read the original attribute.
  Current Batfish behavior (no intermediate flag) matches the device.
- Mixed → attribute-specific behavior. Worth filing per attribute.

The control prefix (10.30.4.0/24) must show `CONTROL-MARKER`. If it
doesn't, the marker mechanism itself has a problem and the rest of the
results can't be trusted.

## Running

```
lab_builder validate topology.clab.yml --checks checks.yaml
```

## Results

Deployed 2026-05-19 on vJunos-router 25.4R1.12 (containerlab on EC2).
All 6 checks passed. Substantive observations from
`show route protocol bgp 10.30/16 detail` on `dut`:

| Prefix       | Communities           | Localpref | AS path           | Decode                  |
| ------------ | --------------------- | --------- | ----------------- | ----------------------- |
| 10.30.1.0/24 | `65002:1, 65002:1001` | 100       | 65001 I           | RED + MATCHED-COMMUNITY |
| 10.30.2.0/24 | `65002:2001`          | **250**   | 65001 I           | MATCHED-LOCALPREF       |
| 10.30.3.0/24 | `65002:3001`          | 100       | **65099 65001 I** | MATCHED-ASPATH          |
| 10.30.4.0/24 | `65002:9999`          | 100       | 65001 I           | CONTROL-MARKER          |

### Interpretation

For all three attribute types tested (community, local-preference,
as-path), the **MATCHED-\* marker fired**, not UNMATCHED-\*. Junos terms
within a single `policy-statement` **do see writes from earlier terms
in the same policy**. This is the same semantics that Batfish currently
emulates for FRR / Cumulus / Quagga via the always-on
`SetReadIntermediateBgpAttributes` flag.

The CONTROL-MARKER fired on the control prefix (10.30.4.0/24),
confirming the marker mechanism itself is sound — so the matched / not-
matched distinction in the other rows is meaningful evidence.

### Batfish triage

`pytest lab_tests/test_labs.py --labname=junos_cross_term_match`:
**13 passed, 0 skipped, no sickbay**. Batfish's BGP-rib local-preference
/ as-path predictions match the device for all four prefixes.
Communities are not compared by the standard validator, so a separate
probe was needed:

`testRoutePolicies` against `dut`/`CROSS-TERM-IMPORT` with vanilla
input routes for each test prefix produced these output communities:

| Prefix       | Device communities    | Batfish communities   |
| ------------ | --------------------- | --------------------- |
| 10.30.1.0/24 | `65002:1, 65002:1001` | `65002:1, 65002:1001` |
| 10.30.2.0/24 | `65002:2001`          | `65002:2001`          |
| 10.30.3.0/24 | `65002:3001`          | `65002:3001`          |
| 10.30.4.0/24 | `65002:9999`          | `65002:9999`          |

Batfish's modeling of within-policy cross-term visibility for Junos
matches the device exactly. **No bug here.** Batfish's Junos
conversion already produces the correct cross-term-readable behavior,
either via output-attribute writes or via implicit semantics of the
policy evaluator (a Java-side detail this lab does not need to
distinguish).

### Companion data

- Snapshot: `snapshots/junos_cross_term_match/`
