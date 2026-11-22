# frr_bgp_remove_private_as_replace_as

Tests what FRR advertises to an eBGP peer in each `neighbor X
remove-private-AS` mode: bare, `all`, `replace-AS` and `all replace-AS`
(batfish/batfish#10460).

## Topology

Four containerlab `frr` nodes (FRR 10.7.1), all eBGP.

| Node | AS    | Links                                                  |
| ---- | ----- | ------------------------------------------------------ |
| r1   | 64601 | eth1 10.0.12.0/31 to r2                                |
| r2   | 64500 | eth2-eth6 10.0.23.0/31-10.0.23.8/31 to r3 eth1-eth5    |
|      |       | eth7, eth8 10.0.24.0/31, 10.0.24.2/31 to r4 eth1, eth2 |
| r3   | 64496 |                                                        |
| r4   | 64602 |                                                        |

r1, in private AS 64601, originates twelve prefixes. It prepends public
AS 64497 to the 203.0.113.0/26s and r4's AS 64602 to 198.51.100.64/26 and
198.51.100.128/26, so r2 learns `64601`, `64601 64497` or `64601 64602`.
r2 sends each prefix over one session, each with one mode:

| r2 session      | Mode                                                     | Prefixes                             |
| --------------- | -------------------------------------------------------- | ------------------------------------ |
| eth2, 10.0.23.1 | `all replace-AS`                                         | 192.0.2.0/26, 203.0.113.0/26         |
| eth3, 10.0.23.3 | `replace-AS`                                             | 192.0.2.64/26, 203.0.113.64/26       |
| eth4, 10.0.23.5 | bare                                                     | 192.0.2.128/26, 203.0.113.128/26     |
| eth5, 10.0.23.7 | `all`                                                    | 192.0.2.192/26, 203.0.113.192/26     |
| eth6, 10.0.23.9 | `all replace-AS`, `local-as 64511 no-prepend replace-as` | 198.51.100.0/26                      |
| eth7, 10.0.24.1 | bare                                                     | 198.51.100.64/26                     |
| eth8, 10.0.24.3 | `all`                                                    | 198.51.100.128/26, 198.51.100.192/26 |

`configs/<node>.conf` are the startup `frr.conf` files. The snapshot's
`configs/<node>/<node>.cfg` wrap the collected running config in the
Cumulus concatenated format, the only form in which Batfish reads FRR
outside SONiC.

## Results

`bgp_peer_remove_private_as` in `bgpd/bgp_route.c`: without `all`, FRR
acts only on a path of private ASes alone. `replace-AS` replaces each
private AS with the session's local AS, the `local-as` if one is set.
Removal keeps the peer's own AS.

| Node | Prefix            | Mode             | AS path                 |
| ---- | ----------------- | ---------------- | ----------------------- |
| r3   | 192.0.2.0/26      | `all replace-AS` | `64500 64500`           |
| r3   | 203.0.113.0/26    | `all replace-AS` | `64500 64500 64497`     |
| r3   | 192.0.2.64/26     | `replace-AS`     | `64500 64500`           |
| r3   | 203.0.113.64/26   | `replace-AS`     | `64500 64601 64497`     |
| r3   | 192.0.2.128/26    | bare             | `64500`                 |
| r3   | 203.0.113.128/26  | bare             | `64500 64601 64497`     |
| r3   | 192.0.2.192/26    | `all`            | `64500`                 |
| r3   | 203.0.113.192/26  | `all`            | `64500 64497`           |
| r3   | 198.51.100.0/26   | `local-as`       | `64511 64511`           |
| r4   | 198.51.100.64/26  | bare             | rejected, `64500 64602` |
| r4   | 198.51.100.128/26 | `all`            | rejected, `64500 64602` |
| r4   | 198.51.100.192/26 | `all`            | `64500`                 |

`test_bgp_rib_routes` compares these paths, and `test_main_rib_routes`
the routes r4 rejects. `checks.yaml` verifies the session each prefix
arrives on.

With batfish/batfish#10460, Batfish leaves the path unchanged in both
`replace-AS` modes (batfish/lab-validation#263), removes every private AS
in the bare mode (batfish/lab-validation#264), and removes the peer's own
AS (batfish/lab-validation#265). `test_bgp_rib_routes` on r3 and r4 and
`test_main_rib_routes` on r4 are sickbayed for these.

Interface properties are sickbayed for the loopback bandwidth mismatch in
batfish/lab-validation#43. FRR 10's `local` routes are excluded by
`FrrValidator` (batfish/lab-validation#248).

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
