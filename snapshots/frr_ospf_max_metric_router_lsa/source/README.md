# frr_ospf_max_metric_router_lsa

Tests what FRR advertises with `max-metric router-lsa administrative` on
an ABR (batfish/batfish#7073).

## Topology

Four containerlab `frr` nodes (FRR 10.7.1). r0 is in area 0, r1 in
area 1, and abr1 and abr2 connect them. The abr1 path uses cost-10
links and the abr2 path cost-40000 links. abr1 has
`max-metric router-lsa administrative`. r1 redistributes a static
192.0.2.0/24 as E1 with metric 20.

| Node | lo             | eth1         | eth2         |
| ---- | -------------- | ------------ | ------------ |
| r0   | 10.255.0.10/32 | 10.0.1.0/31  | 10.0.2.0/31  |
| abr1 | 10.255.0.1/32  | 10.0.1.1/31  | 10.11.0.0/31 |
| abr2 | 10.255.0.2/32  | 10.0.2.1/31  | 10.12.0.0/31 |
| r1   | 10.255.1.1/32  | 10.11.0.1/31 | 10.12.0.1/31 |

`configs/<node>.conf` are the startup `frr.conf` files. The snapshot's
`configs/<node>/<node>.cfg` wrap the collected running config in the
Cumulus concatenated format, the only form in which Batfish reads FRR
outside SONiC.

## Results

FRR advertises abr1's transit links and its type 3 summary LSAs with max
metric (0xFFFF and 0xFF0000), and its type 4 ASBR summary LSAs with the
real cost. `checks.yaml` verifies this on the running lab:

| Node | Prefix         | Next hop         | Metric |
| ---- | -------------- | ---------------- | ------ |
| r0   | 10.255.1.1/32  | 10.0.2.1 (abr2)  | 80000  |
| r1   | 10.255.0.10/32 | 10.12.0.0 (abr2) | 80000  |
| r0   | 192.0.2.0/24   | 10.0.1.1 (abr1)  | 65565  |

abr1's loopback is a stub link, which FRR advertises at its interface
cost rather than the max metric (`lsa_link_loopback_set` in
`ospfd/ospf_lsa.c`). abr2 reaches 10.255.0.1/32 through r1 with metric 40010.

Batfish master maxes abr1's transit links and its loopback, but not its
type 3 summaries. r0 and r1 route to each other's loopback and the far
transit link through abr1, and r0, r1, and abr2 get the wrong metric for
abr1's loopback, so `test_main_rib_routes` is sickbayed on those three
nodes.

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
  --name frr_ospf_max_metric_router_lsa --collected-dir collected --snapshots-dir snapshots
```
