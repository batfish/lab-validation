# nxos_isis — Cisco NX-OS IS-IS L2 lab

Two Cisco N9Kv routers running a single level-2-only IS-IS instance
(`UNDERLAY`, area 49.0001) over a point-to-point link. Each advertises its
loopback into IS-IS; after convergence each router installs the other's
loopback as an `isisL2` route.

```
   r1 ---[Ethernet1/1]---[Ethernet1/1]--- r2
 lo0: 1.1.1.1/32                        lo0: 2.2.2.2/32
 link: 10.0.0.0/31                      link: 10.0.0.1/31
 net: 49.0001.0000.0000.0011.00         net: 49.0001.0000.0000.0022.00
```

## What this lab exercises

NX-OS IS-IS parsing and dataplane modeling, tracked in
[batfish/batfish#10003](https://github.com/batfish/batfish/issues/10003).
The reproducer in that issue is the basis for the configs here:

- `router isis UNDERLAY` with `net` and `is-type level-2`
- `ip router isis UNDERLAY` plus `isis circuit-type level-2` / `isis network
point-to-point` on interfaces

The issue's reproducer used IOS-style syntax (`is-type level-2-only`,
`isis circuit-type level-2-only`, `metric-style wide`) that NX-OS rejects.
The valid NX-OS equivalents are `is-type level-2` and `isis circuit-type
level-2`; NX-OS uses wide metrics by default, so `metric-style` is dropped.

**First-boot quirk:** the N9Kv silently drops `is-type level-2` and
`isis circuit-type level-2` when applied via the vrnetlab startup-config
injection (the `isis`-dependent lines parse before `feature isis` has fully
settled). They apply cleanly when pushed after boot, which is how this
snapshot was collected — the collected `configs/<node>/show_running-config.txt`
(the file Batfish parses) contains all the IS-IS lines. Without them the
adjacency forms as the default level-1-2 and routes install as `L1` instead of
`L2`.

## Batfish coverage

Batfish models NX-OS IS-IS as of batfish/batfish#10003: `router isis`,
`net`, `is-type`, `ip router isis`, `isis circuit-type`, and `isis network
point-to-point` are parsed and converted, the level-2 adjacency forms over
the point-to-point link, and each router installs the other's loopback as an
`isisL2` route (1.1.1.1/32, 2.2.2.2/32) with the NX-OS wide metric (40 per
transit link, 1 on the originating loopback).

The lab-validation NX-OS route parser was extended in this change to recognize
`isis-<tag>, L1|L2` next-hop lines (previously the parser raised on any IS-IS
route).

`test_main_rib_routes` validates clean. The NX-OS validator skips the
management VRF (vrnetlab injects a management default route and brings mgmt0
up out of band, neither of which is in the startup config Batfish parses), so
only the routed IS-IS state is compared.

## Validation target

`pytest lab_tests/test_labs.py --labname=nxos_isis` parses the collected
device data and compares the main RIB against Batfish. The IS-IS loopback
routes, interface, and config checks all validate clean.
