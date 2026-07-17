# eos_bgp_agg_as_path

Arista cEOS lab that captures how EOS forms the AS_PATH of a
locally-generated BGP aggregate when its contributors arrive on
**different** AS_PATHs. Companion to `eos_bgp_agg_vrf` /
`eos_bgp_agg_vrf_summary_only`, which only exercise a single contributor
AS. Reference: batfish/batfish#10094.

## Topology

All eBGP, default VRF, no `as-set` / `summary-only` / `advertise-only`.

```
  c1 (AS 65001)  origin 10.1.1.0/24 ─┐
                                     ├─ c0 (AS 65000, transit) ─ c2 (AS 65002) ─ c3 (AS 65004)
  c4 (AS 65003)  origin 10.1.2.0/24 ─┘                          aggregate 10.1.0.0/16
```

Both contributors traverse transit AS 65000 and then diverge (65001 vs
65003), so at the aggregator c2 they carry a common leading AS followed
by different tails. c2 aggregates them into `10.1.0.0/16`.

## What it demonstrates

Observed on cEOS 4.36.0.1F (`show ip bgp`, default VRF):

| Router | Prefix          | AS_PATH         | Notes                                                          |
| ------ | --------------- | --------------- | -------------------------------------------------------------- |
| c2     | 10.1.1.0/24     | `65000 65001 ?` | contributor                                                    |
| c2     | 10.1.2.0/24     | `65000 65003 ?` | contributor                                                    |
| c2     | **10.1.0.0/16** | **`65000 ?`**   | aggregate, `local-aggregate`, **`atomic-aggregate`**           |
| c3     | 10.1.0.0/16     | `65002 65000 ?` | aggregate as received (c2 prepended 65002), `atomic-aggregate` |

**Finding:** without `as-set`, EOS builds the aggregate AS_PATH from the
**longest common leading AS_SEQUENCE** of its contributors (here `65000`),
**drops the divergent tail** (65001 and 65003 do not appear), and sets the
**ATOMIC_AGGREGATE** attribute. It does not form an AS_SET union of the
contributor ASes. This matches the RFC 4271 §9.2.2.2 aggregation algorithm
for the no-as-set case.

This is consistent with the single-origin-AS labs (`eos_bgp_agg_vrf`),
where both contributors shared the path `65001 ?`, so the common leading
sequence was the whole path `65001`, nothing was dropped, and
atomic-aggregate was not set.

### Relationship to batfish/batfish#10094

#10094 documented that the contributor AS is carried on a single-origin
aggregate (`65001` present), which Batfish had modeled as an empty AS_PATH.
This lab pinned down the multi-contributor case that #10094 left open: the
carried path is the common leading sequence, not a set union, and divergent
ASes are dropped under atomic-aggregate. Batfish now reproduces the
common-leading-sequence behavior (#10094 fixed); the remaining sickbay
covers only the aggregator's local-weight difference (#152).

## Rebuilding

Build inputs are under `source/`. See `infra/README.md` for the
lab_builder workflow (Arista cEOS, no KVM, ~1 min boot). `checks.yaml`
verifies all sessions are Established and both contributors reach the
aggregator on their distinct paths before collection.
