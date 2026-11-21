# frr_bgp_remove_private_as_replace_as

Tests what FRR advertises to an eBGP peer configured with
`neighbor X remove-private-AS all replace-AS` or
`neighbor X remove-private-AS replace-AS` (batfish/batfish#10460).

## Topology

Four containerlab `frr` nodes (FRR 10.7.1), all eBGP.

| Node | AS    | eth1         | eth2         | eth3         |
| ---- | ----- | ------------ | ------------ | ------------ |
| r1   | 64601 | 10.0.12.0/31 | 10.0.14.0/31 |              |
| r2   | 64500 | 10.0.12.1/31 | 10.0.23.0/31 | 10.0.23.2/31 |
| r3   | 64496 | 10.0.23.1/31 | 10.0.23.3/31 | 10.0.34.1/31 |
| r4   | 64499 | 10.0.14.1/31 | 10.0.34.0/31 |              |

r1, in private AS 64601, originates 192.0.2.0/24 and 198.51.100.0/24.
r3 learns each prefix through r4 (AS path `64499 64601`, origin IGP) and
through r2. r2 has two sessions to r3: over eth2 it sends only
192.0.2.0/24, with `remove-private-AS all replace-AS`; over eth3 only
198.51.100.0/24, with `remove-private-AS replace-AS`. Both set origin
incomplete.

`configs/<node>.conf` are the startup `frr.conf` files. The snapshot's
`configs/<node>/<node>.cfg` wrap the collected running config in the
Cumulus concatenated format, the only form in which Batfish reads FRR
outside SONiC.

## Results

In both modes FRR replaces r1's private AS with r2's own AS rather than
removing it (`aspath_replace_private_asns` in `bgpd/bgp_aspath.c`), so r3
receives `64500 64500` from r2, two ASes long. That ties with the path
through r4 on length, and r3 picks r4 on origin. `checks.yaml` verifies
this on the running lab:

| Node | Prefix          | Next hop       |
| ---- | --------------- | -------------- |
| r3   | 192.0.2.0/24    | 10.0.34.0 (r4) |
| r3   | 198.51.100.0/24 | 10.0.34.0 (r4) |

If the private AS were removed instead of replaced, the path through r2
would be `64500`, one AS long, and r3 would pick r2 (10.0.23.0 and
10.0.23.2). `test_main_rib_routes` on r3 checks for this.

Interface properties are sickbayed for the loopback bandwidth mismatch in
batfish/lab-validation#43. FRR 10's `local` routes are excluded by
`FrrValidator` (batfish/lab-validation#248). The collected data has no
BGP RIB, so `test_bgp_rib_routes` is not implemented for FRR.

## Build

```bash
# On the EC2 host:
PYTHONPATH=src python3 -m lab_builder deploy topology.clab.yml
PYTHONPATH=src python3 -m lab_builder health-check topology.clab.yml
PYTHONPATH=src python3 -m lab_builder validate topology.clab.yml --checks checks.yaml
PYTHONPATH=src python3 -m lab_builder collect topology.clab.yml --output-dir collected
PYTHONPATH=src python3 -m lab_builder build-snapshot topology.clab.yml \
  --name frr_bgp_remove_private_as_replace_as --collected-dir collected --snapshots-dir snapshots
```
