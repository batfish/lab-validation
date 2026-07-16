# Arista `aggregate-address 0.0.0.0/0` in a VRF (no summary-only)

Companion to `eos_bgp_agg_vrf_summary_only`. Same topology and configs, but
c2's aggregate omits `summary-only`, so the contributors are NOT suppressed.
Reference: batfish/batfish#10093.

## Topology

```
c1 (AS 65001)                c2 (AS 65166.10010, asdot)          c3 (AS 65002)
  redistribute static          vrf vxlan_public                    default vrf
  10.1.1.96/27 -> Null0        aggregate-address 0.0.0.0/0         peers c2 in asplain
  10.1.1.98/32 -> Null0          advertise-only                    (4270728986)
  Et1 10.10.10.1/24 --- Et1 10.10.10.2/24  Et2 11.11.11.2/24 --- Et1 11.11.11.1/24
```

- All of c2's BGP sessions live in `vrf vxlan_public` under `router bgp`
  with an asdot AS (`65166.10010` = `4270728986`). c1 peers with it in
  asdot notation; c3 in asplain.
- c1 redistributes two static routes — a `/27` and a covered `/32` host
  route — into BGP and advertises both to c2.
- c2's VRF has `aggregate-address 0.0.0.0/0 advertise-only`, WITHOUT
  `summary-only`.

## Building

```
lab_builder validate source/topology.clab.yml --checks source/checks.yaml
```

Built on Arista cEOS 4.36.0.1F (containerlab on EC2).

## Key Findings

Without `summary-only`, the contributors are not suppressed: c3 receives
`10.1.1.96/27`, `10.1.1.98/32`, AND the `0.0.0.0/0` aggregate. Contrast with
`eos_bgp_agg_vrf_summary_only`, where c3 receives only the aggregate.

Sickbay entries in `validation/sickbay.yaml` track the same peripheral
route-attribute discrepancies as the summary-only lab (the aggregate exists
in both):

- **Aggregate AS_PATH** (batfish/batfish#10094): EOS builds the aggregate's
  AS_PATH from contributor ASes; Batfish leaves it empty. Cascades to c2/c3
  as-path and to c1 (AS 65001) accepting vs rejecting the re-advertised
  aggregate. c2 also has the locally-originated weight divergence
  (batfish/lab-validation#152).

`advertise-only` local-RIB-install semantics are modeled correctly since
batfish/batfish#10096: the device does not install the aggregate in the VRF
main RIB, and Batfish now matches.
