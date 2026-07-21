# eos_evpn_multiple_rts

Arista cEOS EVPN lab exercising a single VRF that declares **multiple**
`route-target import evpn` and `route-target export evpn` lines.

Reference: batfish/batfish#10113.

## What it tests

Arista EOS allows a VRF to list several import and several export EVPN
route-targets:

```
vrf RED
   route-target import evpn 65000:100
   route-target import evpn 65000:199
   route-target export evpn 65000:200
   route-target export evpn 65000:299
```

Batfish's Arista model stores a single import and a single export RT per
VRF (`AristaBgpVrf._importRouteTarget` / `_exportRouteTarget`), and the
extractor overwrites on each line, so only the last value survives. This
lab reproduces the resulting divergence end to end.

## Topology

Two directly-connected VTEPs, eBGP IPv4 underlay plus eBGP EVPN overlay
over Loopback0, symmetric-IRB L3VNI:

- `leaf1` AS 65101, VRF `RED` (L3VNI 15001), tenant loopback `10.1.1.1/32`
- `leaf2` AS 65102, VRF `BLUE` (L3VNI 15002), tenant loopback `10.2.2.2/32`

RTs are arranged so the **matching** value is never the last one listed
in its direction:

| leaf1 RED             | leaf2 BLUE            |
| --------------------- | --------------------- |
| import 65000:100, 199 | import 65000:200, 288 |
| export 65000:200, 299 | export 65000:100, 177 |

`leaf2` BLUE imports `10.1.1.1/32` because leaf1 RED exports `65000:200`
(BLUE's first import). `leaf1` RED imports `10.2.2.2/32` because leaf2
BLUE exports `65000:100` (RED's first import).

## Expected behavior

Real cEOS: both tenant loopbacks cross into the peer VRF — matching
happens on the first-listed RT, and the decoys (`199`, `299`, `288`,
`177`) are unused.

Buggy model: only the last RT per direction is retained (`199`/`299` on
leaf1, `288`/`177` on leaf2). None of those match anything, so neither
`10.1.1.1/32` nor `10.2.2.2/32` is imported — visible as missing routes
in the VRF RIB / EVPN RIB and in `evpnL3VniProperties()`.

## Status

Deployed on cEOS 4.36.0.1F via the `infra/` lab builder, collected, and
validated against Batfish. All 6 `checks.yaml` preconditions pass on the
real device: both cross-VRF routes import via their non-last RT.

The multiple-route-target modeling gap (batfish/batfish#10113) and the
related `send-community extended` gap (batfish/batfish#10116) are fixed,
so both cross-VRF routes now reach the main RIB and
`test_main_rib_routes` passes. `test_bgp_rib_routes` and
`test_evpn_rib_routes` still xfail on the pre-existing locally-originated
path-attribute divergence (lab-validation#152), which is unrelated to
route targets and appears in any Arista EVPN lab.
