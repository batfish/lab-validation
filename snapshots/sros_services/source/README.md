# sros_services — Nokia SR OS Service Configuration Quick Reference lab

Source: [nokia/sros-docs-lab](https://github.com/nokia/sros-docs-lab)
(`service_config_qrg`), the lab behind Nokia's [SR OS Service Configuration
Quick Reference Guide](https://documentation.nokia.com/sr/26-3/7750-sr/titles/services-config-quick-ref.html).
Provided by our Nokia contact as a pre-canned containerlab topology.

## What this lab is

A **single combined topology**, not a graded ladder. Ten nodes — 4 PE + 2 P
(all Nokia SR-SIM) + 4 Linux CE — stacking the _entire_ SP service suite on one
shared IGP/MPLS underlay:

```
        cea                              cez
         |                                |
   +----pe1----+                    +----pe3----+
   |     |     |   (iBGP full mesh  |     |     |
ceb-+    |    p1------ AS 64500 ----p2    |    +-cey
   |     |     |   over system /32) |     |     |
   +----pe2----+                    +----pe4----+
        |                                |
       ceb                              cey
```

- **Underlay:** OSPF area 0 **and** IS-IS L2 with segment-routing (both run;
  OSPF is given `preference 20` so IS-IS — admin distance 18 — is the preferred
  IGP), LDP, RSVP-TE, MPLS, SR-ISIS/SR-TE LSPs. iBGP full mesh among the four
  PEs (AS 64500), sourced from system loopbacks.
- **Services:** Epipe (VLL), VPLS, VPRN (L3VPN RED/BLUE with RT import/export),
  IES + routed-VPLS, EVPN-VPWS, EVPN-MPLS with all-active multihoming (LAG +
  ethernet-segments). PE1/PE3 carry the routed services; all four PEs run
  EVPN-MPLS.

All SR-SIM configs are the upstream Nokia startup configs verbatim, with one
addition: a materialized `system security` block (AAA profiles + SSH cipher
list). SR-SIM auto-generates SSH defaults whose ciphers modern paramiko
rejects; configuring any `system security` subtree replaces those defaults, so
the block is required for SSH collection (and carries the admin user).

## Batfish coverage: modeled underlay vs. unmodeled service overlay

The Batfish SR-OS vendor model (as of `sros-next`) covers the **routed
underlay**; the **service overlay** is out of the VI model. Both must _parse_
cleanly — confirmed: all six device configs parse with **zero FATAL parse
warnings** and `fileParseStatus` PASSED.

### Modeled and validated (the underlay)

| Feature                                                                               | Status                                                 |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Interfaces (port / router-interface split, system loopback)                           | modeled                                                |
| OSPF (areas, interfaces, metric, preference)                                          | modeled                                                |
| IS-IS (L2, area-address, interface metric, **system-id auto-derived from system IP**) | modeled (system-id derivation added by this lab)       |
| BGP iBGP sessions (group→neighbor inheritance, system-sourced)                        | modeled                                                |
| Static routes (next-hop, blackhole)                                                   | modeled                                                |
| `service vprn` → VRF (RED/BLUE)                                                       | modeled                                                |
| per-VPRN interfaces with a name reused across VRFs                                    | modeled (qualified `<vrf>.<name>`, lab-validation#203) |
| policy-options (policy-statement, community, prefix-list)                             | modeled                                                |

### Parses but not converted — sickbay'd (the service overlay)

These constructs parse without error but have no representation in the Batfish
VI model. They are tracked in `../validation/sickbay.yaml`, each keyed to a
GitHub issue:

| Feature                                                               | Why out of scope                                                           |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| MPLS / LDP / RSVP-TE / segment-routing / LSPs                         | no MPLS transport in the Batfish VI dataplane                              |
| BGP `family vpn-ipv4` / `family evpn`                                 | no VPNv4/EVPN address-family in VI                                         |
| `bgp-ipvpn` RT import/export, `auto-bind-tunnel`                      | RD is extracted; inter-PE VPN route import is not reproduced (no VPNv4 AF) |
| L2 services: Epipe, VPLS, `service sdp`, `spoke-sdp`, SAP             | no L2VPN/pseudowire model                                                  |
| IES service + `interface ... vpls` (IRB)                              | IES service not extracted                                                  |
| EVPN (`bgp-evpn`, `ethernet-segment`, multihoming)                    | no EVPN model                                                              |
| `filter ip-filter` / `mac-filter` (ACLs)                              | SR-OS filters not extracted (policy-statements are)                        |
| QoS policies, `port ethernet mode access`, LAG LACP                   | not control-plane-relevant to routing                                      |
| static-route `indirect ... tunnel-next-hop resolution-filter sr-isis` | tunnel next-hop not modeled (the IES inter-PE static routes)               |

## Validation target

`pytest lab_tests/ --labname=sros_services` validates the underlay against device
ground truth (the `info json /state` captures): interfaces, iBGP session state,
and config-format on all six nodes, plus the main-RIB route comparison where it
is not sickbay'd.

- **BGP sessions, config-format, and interfaces validate clean on all six
  nodes** — including pe1/pe3's VPRN interface name reused across the RED and
  BLUE VRFs (`to-cea` / `to-cez`), which Batfish models under its VRF-qualified
  name `<vrf>.<name>` so both copies survive (batfish/lab-validation#203).
- **Main-RIB route comparison is sickbay'd on all six nodes**
  (`../validation/sickbay.yaml`), for two distinct documented reasons:
  - **IGP ECMP** (p1/p2/pe2/pe4): SR OS installs a single best path per prefix
    (`ecmp 1`); Batfish has no per-IGP ECMP limit and installs all equal-cost
    legs, so it holds the device's chosen next-hop plus extras. Tracked in
    batfish/lab-validation#200. Not worked around in the validator: forgiving the
    surplus legs there would globally weaken the cost matcher and could mask a
    real "right path + wrong extra legs" miscomputation.
  - **Service overlay** (pe1/pe3): these PEs run the routed VPRN/IES services, so
    their RIBs carry bgp-vpn (MPLS L3VPN) routes (batfish/batfish#9991) and IES
    interface + SR-ISIS-tunnel static routes (batfish/batfish#9996) that the VI
    model does not reproduce.
