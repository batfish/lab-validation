# eos_bgp_agg_mixed_prefixlen

Arista cEOS lab that confirms a locally-generated BGP aggregate derives its
AS_PATH from **all** more-specific contributors, regardless of their prefix
length or count. Companion to `eos_bgp_agg_as_path` (which uses two
equal-length contributors). Reference: batfish/batfish#10094.

## Topology

All eBGP, default VRF, no `as-set` / `summary-only` / `advertise-only`.

```
  c1 (AS 65001)  origin 10.1.0.0/20 ────────────┐
                                                 ├─ c0 (AS 65000) ─ c2 (AS 65002) ─ c3 (AS 65004)
  c4 (AS 65003)  origin 10.1.16.0/24            /                  aggregate 10.1.0.0/19
                 + 10.1.17.1..8/32 (eight /32s) ┘
```

The aggregator c2 learns a **mixed** contributor set for its `10.1.0.0/19`
aggregate: one large `/20` from AS 65001, plus a `/24` and eight `/32`s from
AS 65003. All traverse transit AS 65000, then diverge (65001 vs 65003).

## What it demonstrates

Observed on cEOS 4.36.0.1F (`show ip bgp`, default VRF):

| Prefix                       | Contributor(s)       | AS_PATH at c2                      |
| ---------------------------- | -------------------- | ---------------------------------- |
| 10.1.0.0/20                  | large, AS 65001      | `65000 65001 ?`                    |
| 10.1.16.0/24, 10.1.17.1-8/32 | small, AS 65003      | `65000 65003 ?`                    |
| **10.1.0.0/19**              | **all of the above** | **`65000 ?`** + `atomic-aggregate` |

**Finding:** EOS forms the aggregate AS_PATH from the longest common leading
AS_SEQUENCE across the **entire** contributor set — not just the largest
prefix, and not weighted by contributor count. Here every contributor shares
leading AS 65000 and then diverges, so the aggregate is `65000` with the
divergent tail (65001 and 65003) dropped and ATOMIC_AGGREGATE set. Had EOS
used only the `/20`, the path would be `65000 65001`; only the `/32`s,
`65000 65003`. It is neither.

This complements `eos_bgp_agg_as_path` (two equal-length contributors) by
showing prefix length and count do not change the rule: contributors are
selected purely by prefix containment (strictly more specific than the
aggregate), and all participate equally.

### Relationship to batfish/batfish#10094

Same root cause as `eos_bgp_agg_as_path`: Batfish models the aggregate with
an empty AS_PATH, so it differs from the device on the aggregator, the
downstream neighbor, and the transit/contributor ASes (which reject the
re-advertised aggregate as an AS-path loop once it carries 65000).

## Rebuilding

Build inputs are under `source/`. See `infra/README.md` for the lab_builder
workflow (Arista cEOS, no KVM, ~1 min boot). `checks.yaml` verifies all
sessions are Established and that a large and a small contributor both reach
the aggregator before collection.
