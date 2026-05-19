# Junos Policy-Chain Visibility Lab

When a BGP neighbor has `import [ POLICY-A POLICY-B POLICY-C ];`, can a
later policy `from`-match on attributes that an earlier policy wrote?
This is the Junos analog of the combined export-import policy case
discussed in `working/intermediateAttributes.md`
(`CiscoConversions.vrfExportImportPolicy` and the Cisco-XR / ASA
variants), where Batfish currently emits intermediate-attribute flags
to make the import side see export-side writes.

## Hypothesis

Either:

- **Junos chains see writes.** A modification by POLICY-A is visible
  to POLICY-B's `from` clauses. Then Batfish's Junos conversion would
  need to set `ReadIntermediate` between policies (or use output
  attributes) for chained imports to model correctly.

- **Junos chains do not see writes.** Each policy in the chain
  evaluates `from` clauses against the original attributes that
  arrived from the protocol. Then the current Batfish behavior (no
  intermediate flag on Junos) likely matches the device for chains.

The answer is empirical and may differ per attribute (community vs.
local-preference vs. as-path).

## Topology

```
sender (AS 65001) --- dut (AS 65002)
       ge-0/0/0  <->  ge-0/0/0
       10.0.12.0      10.0.12.1
```

No collector — observation is on `dut`.

## Method

`dut`'s BGP session from `sender` carries `import [ POLICY-A-WRITE
POLICY-B-READ POLICY-C-DEFAULT ];`. The three policies are layered:

1. **POLICY-A-WRITE**: per prefix, modify a single attribute and fall
   through (no `accept`/`reject`).
2. **POLICY-B-READ**: per prefix, attempt to `from`-match on the
   modified value. If matched, tag the route `MATCHED-*` and accept.
3. **POLICY-C-DEFAULT**: per prefix, tag the route `UNMATCHED-*` and
   accept.

The marker community on each route reveals the path taken.

## Test Routes

| Prefix       | Attribute        | POLICY-A write           | POLICY-B read condition |
| ------------ | ---------------- | ------------------------ | ----------------------- |
| 10.40.1.0/24 | community        | `community add RED;`     | `community RED;`        |
| 10.40.2.0/24 | local-preference | `local-preference 250;`  | `local-preference 250;` |
| 10.40.3.0/24 | as-path          | `as-path-prepend 65099;` | `as-path WITH-65099`    |

Marker decoder (same as `junos-cross-term-match`):

| Community    | Meaning               |
| ------------ | --------------------- |
| `65002:1001` | `MATCHED-COMMUNITY`   |
| `65002:1002` | `UNMATCHED-COMMUNITY` |
| `65002:2001` | `MATCHED-LOCALPREF`   |
| `65002:2002` | `UNMATCHED-LOCALPREF` |
| `65002:3001` | `MATCHED-ASPATH`      |
| `65002:3002` | `UNMATCHED-ASPATH`    |

## What to Observe

On `dut`:

```
show route 10.40.0.0/22 detail | display json
```

For each prefix, exactly one of the `MATCHED-*` / `UNMATCHED-*` marker
communities (per attribute) should be present.

## Companion Lab

`junos-cross-term-match` asks the same question for _terms within one
policy_. Reading the two together gives the Junos picture:

| Setting        | Cross-term                         | Cross-policy |
| -------------- | ---------------------------------- | ------------ |
| Junos behavior | (this lab and its sibling tell us) | (this lab)   |

## Running

```
lab_builder validate topology.clab.yml --checks checks.yaml
```

## Results

Deployed 2026-05-19 on vJunos-router 25.4R1.12 (containerlab on EC2).
All 5 checks passed. Substantive observations from
`show route protocol bgp 10.40/16 detail` on `dut`:

| Prefix       | Communities           | Localpref | AS path           | Decode                  |
| ------------ | --------------------- | --------- | ----------------- | ----------------------- |
| 10.40.1.0/24 | `65002:1, 65002:1001` | 100       | 65001 I           | RED + MATCHED-COMMUNITY |
| 10.40.2.0/24 | `65002:2001`          | **250**   | 65001 I           | MATCHED-LOCALPREF       |
| 10.40.3.0/24 | `65002:3001`          | 100       | **65099 65001 I** | MATCHED-ASPATH          |

### Interpretation

For all three attribute types tested, the **MATCHED-\* marker fired**
across the policy chain. POLICY-B in `import [ POLICY-A POLICY-B
POLICY-C ];` **does see** the writes that POLICY-A made for the same
route. Junos chain visibility is the same as within-policy term
visibility: writes propagate to downstream policies in the chain.

This matches the semantics that `CiscoConversions.vrfExportImportPolicy`
emulates via `SetReadIntermediateBgpAttributes` between the two
combined policies.

### Batfish triage

`pytest lab_tests/test_labs.py --labname=junos_policy_chain_visibility`:
**13 passed, 0 skipped, no sickbay**. Batfish's BGP-rib local-preference
/ as-path predictions match the device for all three prefixes.

The richer probe is `bgpRib` against the dataplane, which exposes
the predicted communities. Querying it produced:

| Prefix       | Device communities    | Batfish bgpRib communities |
| ------------ | --------------------- | -------------------------- |
| 10.40.1.0/24 | `65002:1, 65002:1001` | `65002:1, 65002:1001`      |
| 10.40.2.0/24 | `65002:2001`          | `65002:2001`               |
| 10.40.3.0/24 | `65002:3001`          | `65002:3001`               |

**No discrepancy.** Batfish's modeling of Junos `import [ A B C ]`
chains correctly gives B visibility into A's writes, exactly as the
device does.

For curiosity: testRoutePolicies on each policy in isolation yields
DENY for A and B (no terminating accept; Junos default is reject), and
PERMIT with the UNMATCHED-\* markers for C (because in isolation there
is no prior write to read). It is only the _chain_ execution that
produces the MATCHED-\* result, and Batfish gets that right.

### Companion data

- Snapshot: `snapshots/junos_policy_chain_visibility/`
