# frr_bgp_med_best_path

Tests where the MED sits in BGP best-path selection: it is compared only
between paths from the same neighbor AS, and it is compared before the
eBGP-over-iBGP step (RFC 4271, section 9.1.2.2, c and d).

## Topology

Four containerlab `frr` nodes (FRR 10.7.1).

| Node | AS    | Links                                 |
| ---- | ----- | ------------------------------------- |
| r1   | 64500 | eth1 10.0.12.0/31 to r2 eth1 (iBGP)   |
|      |       | eth2 10.0.13.0/31 to r3 eth1 (iBGP)   |
|      |       | eth3 10.0.14.0/31 to r4 eth1 (eBGP)   |
| r2   | 64500 |                                       |
| r3   | 64500 |                                       |
| r4   | 64496 |                                       |

r1 is the router under test. It has no policy that changes a route, and it
advertises nothing (`route-map NONE out`), so the other three tables hold
only their own routes. r2, r3 and r4 originate the prefixes below. The iBGP
peers r2 and r3 prepend one AS in their outbound route map, which makes that
AS the neighbor AS of the path at r1; every peer sets the MED there too.
Each prefix reaches r1 on two paths with the same local preference, AS-path
length and origin:

| Prefix           | Path 1 (peer, AS path, MED) | Path 2 (peer, AS path, MED) |
| ---------------- | --------------------------- | --------------------------- |
| 192.0.2.0/26     | r2 iBGP, `64497`, 100       | r3 iBGP, `64498`, 10        |
| 192.0.2.64/26    | r2 iBGP, `64496`, 10        | r4 eBGP, `64496`, 100       |
| 192.0.2.128/26   | r2 iBGP, `64497`, 100       | r3 iBGP, `64497`, 10        |
| 192.0.2.192/26   | r2 iBGP, `64496`, 100       | r4 eBGP, `64496`, 10        |

`configs/<node>.conf` are the startup `frr.conf` files. The snapshot's
`configs/<node>/<node>.cfg` wrap the collected running config in the
Cumulus concatenated format.

## Results

FRR's selection on r1 (`show bgp ipv4 unicast <prefix> json`, field
`selectionReason`):

| Prefix           | r1 selects                | Reason                                                   |
| ---------------- | ------------------------- | -------------------------------------------------------- |
| 192.0.2.0/26     | r2, MED 100               | Router ID: the MEDs are not compared, the neighbor ASes differ |
| 192.0.2.64/26    | r2 (iBGP), MED 10         | MED: compared before eBGP over iBGP                      |
| 192.0.2.128/26   | r3, MED 10                | MED (control: one neighbor AS)                           |
| 192.0.2.192/26   | r4 (eBGP), MED 10         | MED (control: the eBGP path also has the lower MED)      |

Batfish 2026.08.27.3685 selects r3 for 192.0.2.0/26 (it compares the MEDs
of paths from different neighbor ASes) and r4 for 192.0.2.64/26 (it prefers
eBGP over iBGP before it compares the MEDs). The two controls agree. The
comparison is in Batfish's vendor-independent `BgpRib`, so it is not
specific to FRR.

`test_bgp_rib_routes` and `test_main_rib_routes` on r1 are sickbayed for
these two prefixes: 192.0.2.0/26 is batfish/batfish#10260 (neighbor-AS
restriction of the MED comparison), 192.0.2.64/26 is batfish/batfish#10525 (MED
after eBGP over iBGP). `checks.yaml` verifies the next hop r1 installs for
each prefix.

Interface properties are sickbayed for the loopback bandwidth mismatch in
batfish/lab-validation#43.

## Build

This lab was not built with `lab_builder deploy` / `collect`: the author had
docker without root and no EC2 host. The nodes ran from the topology's
image (`quay.io/frrouting/frr:containerlab-10.7.1`) under plain docker, with
the same startup configs, interface names and daemons; each link was a
docker bridge network without IPv4 addressing instead of a veth pair, and
the commands of the `frr` profile ran through `docker exec` instead of SSH.
The snapshot was then built from those outputs by
`lab_builder.snapshot.build_snapshot`. The checks of `checks.yaml` were
evaluated with the same rules as `lab_builder validate` on the same command
outputs, not by `lab_builder validate` itself.

To rebuild on an EC2 host:

```bash
PYTHONPATH=src python3 -m lab_builder deploy topology.clab.yml
PYTHONPATH=src python3 -m lab_builder health-check topology.clab.yml
PYTHONPATH=src python3 -m lab_builder validate topology.clab.yml --checks checks.yaml
PYTHONPATH=src python3 -m lab_builder collect topology.clab.yml --output-dir collected
PYTHONPATH=src python3 -m lab_builder build-snapshot topology.clab.yml \
  --name frr_bgp_med_best_path --collected-dir collected --snapshots-dir snapshots
```
