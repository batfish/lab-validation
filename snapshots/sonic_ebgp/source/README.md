# sonic_ebgp

Two SONiC routers (containerlab `sonic-vm`, SONiC 202605, FRR 10.5.4)
peering eBGP over two parallel links. Each advertises its Loopback0, so
each learns the other's loopback as a two-way ECMP BGP route.

```text
          192.168.12.0/31  Ethernet0
  s1 --------------------------------- s2
  AS 65001 ---------------------------- AS 65002
          192.168.12.2/31  Ethernet4
  Loopback0 1.1.1.1/32        Loopback0 2.2.2.2/32
```

## Startup configs

`configs/<node>.json` are full config_db files: the sonic-vm default
config with DEVICE_METADATA, INTERFACE, LOOPBACK_INTERFACE, and
BGP_NEIGHBOR replaced. SONiC's bgpcfgd renders the FRR config from
BGP_NEIGHBOR, so `frr.conf` in the snapshot is generated, not authored.

The link subnets avoid 10.0.0.0/24, which vrnetlab's QEMU user-mode
management network uses inside the VM.

## Build

```bash
# On the EC2 host:
./build-sonic-image.sh 202605
PYTHONPATH=src python3 -m lab_builder deploy topology.clab.yml
PYTHONPATH=src python3 -m lab_builder health-check topology.clab.yml
PYTHONPATH=src python3 -m lab_builder validate topology.clab.yml --checks checks.yaml
PYTHONPATH=src python3 -m lab_builder collect topology.clab.yml --output-dir collected
PYTHONPATH=src python3 -m lab_builder build-snapshot topology.clab.yml \
  --name sonic_ebgp --collected-dir collected --snapshots-dir snapshots
```

## Results

Batfish's main RIB matches the device on both nodes. The device RIB also
holds the management network (eth0) routes, which are outside config_db;
the validator excludes them.

Batfish does not set bandwidth on SONiC ports
(batfish/lab-validation#232). BGP RIB validation is not implemented for
SONiC: FRR 10 BGP JSON uses a `path` string where the existing FRR
parser expects the FRR 7 `aspath` object.
