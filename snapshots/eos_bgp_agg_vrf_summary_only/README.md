# Arista `aggregate-address 0.0.0.0/0 summary-only` in a VRF

Reproduces the production scenario in batfish/batfish#10093: a pair of
Arista border leafs applied `aggregate-address 0.0.0.0/0 summary-only
advertise-only` inside a VRF. `summary-only` suppressed every contributing
more-specific VRF-wide, collapsing a downstream router's received routes to
just the default aggregate and causing a brief outage.

The companion lab `eos_bgp_agg_vrf` is identical but omits `summary-only`,
so the contributors are not suppressed.

## Topology

```
c1 (AS 65001)                c2 (AS 65166.10010, asdot)          c3 (AS 65002)
  redistribute static          vrf vxlan_public                    default vrf
  10.1.1.96/27 -> Null0        aggregate-address 0.0.0.0/0         peers c2 in asplain
  10.1.1.98/32 -> Null0          summary-only advertise-only       (4270728986)
  Et1 10.10.10.1/24 --- Et1 10.10.10.2/24  Et2 11.11.11.2/24 --- Et1 11.11.11.1/24
```

- All of c2's BGP sessions live in `vrf vxlan_public` under `router bgp`
  with an asdot AS (`65166.10010` = `4270728986`). c1 peers with it in
  asdot notation; c3 in asplain.
- c1 redistributes two static routes — a `/27` and a covered `/32` host
  route — into BGP and advertises both to c2.
- c2's VRF has `aggregate-address 0.0.0.0/0 summary-only advertise-only`, so
  the `0.0.0.0/0` aggregate makes every learned route a suppressed
  contributor.

## Building

```
lab_builder validate source/topology.clab.yml --checks source/checks.yaml
```

Built on Arista cEOS 4.36.0.1F (containerlab on EC2).

## Key Findings

The intended behavior is modeled correctly: c3 receives ONLY `0.0.0.0/0`.
On the device, c2's VRF learns both contributors, advertises only the
aggregate (PfxAdv 1), and c3's BGP RIB holds exactly `{0.0.0.0/0}` —
matching Batfish. This is the outage-reproducing suppression.

Sickbay entries in `validation/sickbay.yaml` track peripheral
route-attribute discrepancies that remain:

- **Aggregate AS_PATH** (batfish/batfish#10094): EOS builds the
  locally-generated aggregate's AS_PATH from contributor ASes (device
  `asPath "65001 ?"`), while Batfish leaves it empty. This cascades: c2's
  aggregate carries `(65001,)` vs `()`; c3 receives `(4270728986, 65001)`
  vs `(4270728986,)`; and c1 (AS 65001) rejects the re-advertised aggregate
  as an AS-path loop, while Batfish — modeling an empty as-path — installs
  it in c1's BGP and main RIBs. c2 also has the locally-originated weight
  divergence (32768 vs 0), batfish/lab-validation#152.

`advertise-only` local-RIB-install semantics are modeled correctly since
batfish/batfish#10096: the device does not install the aggregate in the VRF
main RIB, and Batfish now matches. The EOS `dropRoute` route type (how `ip
route <prefix> Null0` appears in `show ip route`) is matched to Batfish's
discard static route by the Arista validator.
