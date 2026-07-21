# eos_evpn_l2_multiple_rts

Arista cEOS L2 EVPN lab exercising a `vlan-aware-bundle` that declares
**multiple** `route-target import` and `route-target export` lines.
Companion to `eos_evpn_multiple_rts` (the L3 VRF case).

Reference: batfish/batfish#10113.

## What it tests

Arista EOS allows an L2 vlan-aware-bundle (or `vlan`) to list several
import and export route targets:

```
vlan-aware-bundle BLUE
   rd 192.168.255.1:10110
   route-target import 65000:100
   route-target import 65000:199
   route-target export 65000:200
   route-target export 65000:299
   vlan 110
```

Batfish's Arista extractor previously stored a single import and single
export target per bundle and overwrote on each line, keeping only the
last. This lab proves the fix retains all of them.

## Topology

Two directly-connected VTEPs, eBGP IPv4 underlay plus eBGP EVPN overlay
over Loopback0, one L2 VNI (10110) in vlan-aware-bundle BLUE:

| leaf1 (AS 65101)      | leaf2 (AS 65102)      |
| --------------------- | --------------------- |
| import 65000:100, 199 | import 65000:200, 288 |
| export 65000:200, 299 | export 65000:100, 177 |

## How the difference is observed

Unlike the L3 lab, the L2 route targets have **no observable dataplane
effect in Batfish today**: L2 VNI membership between VTEPs is matched by
VNI number and BUM transport, not by route target, and there is no
`evpnL2VniProperties` question. The lab therefore proves non-overwrite by
inspecting the vendor-independent model: the `Layer2VniConfig` for VNI
10110 must carry both export route targets (`routeTargets`) and both
import route-target patterns (`importRouteTargets`). Before the fix only
the last of each survived.

See `working/` for the viModel inspection used to verify this on the
collected snapshot.

## Status

Deployed on cEOS 4.36.0.1F via the `infra/` lab builder, collected, and
inspected against Batfish. The `Layer2VniConfig` for VNI 10110 retains
all declared import and export route targets on both leaves.
