# Lab Creation Infrastructure

Tools for creating new lab-validation snapshots using
[containerlab](https://containerlab.dev/) on AWS EC2 with Juniper
vJunos-router virtual images.

## Overview

This directory contains everything needed to:

1. Provision an AWS EC2 instance with KVM, Docker, and containerlab
2. Deploy Juniper virtual router topologies
3. Collect device operational data (show command outputs)
4. Package the data as lab-validation snapshots
5. Validate against Batfish

The workflow is designed to be driven by Claude Code or run manually.

## Prerequisites

- **AWS CLI v2.34+** with configured credentials (`aws configure` or
  `AWS_PROFILE` environment variable)
- **Juniper vJunos-router qcow2 image** — free download from
  [Juniper vJunos Labs](https://www.juniper.net/us/en/dm/vjunos-labs.html)
  (non-production use, no time limit)
- **Batfish** running locally for validation (Docker image or built from
  source)

## One-Time Setup

### 1. Download the Juniper Image

Download `vJunos-router-*.qcow2` from Juniper's website and save it to
`infra/images/` (this directory is gitignored):

```bash
ls infra/images/
# vJunos-router-25.4R1.12.qcow2
```

### 2. Upload to S3

```bash
cd infra
AWS_PROFILE=<profile> ./upload-image.sh
```

This creates an S3 bucket named `lab-validation-images-<account-id>` (if it
doesn't exist) and uploads all qcow2 files from `infra/images/`. Idempotent —
skips files already in S3.

### 3. First Launch — Build the Docker Image

The first EC2 launch will find the qcow2 in S3 but no pre-built Docker image.
The setup script automatically builds the vrnetlab container and uploads the
result to S3 for future launches. This takes ~10 minutes total for the first
launch.

```bash
AWS_PROFILE=<profile> ./ec2-launch.sh
# Wait for setup to complete (~5-10 min)
ssh -i <key> ubuntu@<ip> 'cat /var/log/ec2-setup-complete'
```

### Subsequent Launches

After the Docker image is in S3, new instances load it directly (~2-3 min):

```bash
AWS_PROFILE=<profile> ./ec2-launch.sh
```

## Creating a Lab

### Step 1: Design the Topology

Create a containerlab topology YAML file and Junos configs. Configs must be
in **curly-brace format** (not `set` format) because vrnetlab concatenates
them with its init.conf and loads them as a config disk.

See `infra/examples/` for working examples:

- `two-router-ebgp.clab.yml` — minimal 2-router eBGP lab
- `evpn-type5/topology.clab.yml` — 4-node EVPN Type 5 fabric

**Interface mapping**: containerlab `ethN` maps to Junos `ge-0/0/(N-1)`:

| containerlab | Junos             |
| ------------ | ----------------- |
| eth0         | management (auto) |
| eth1         | ge-0/0/0          |
| eth2         | ge-0/0/1          |
| eth3         | ge-0/0/2          |
| ethN         | ge-0/0/(N-1)      |

### Step 2: Launch EC2 and Upload

```bash
# Launch instance
AWS_PROFILE=<profile> ./ec2-launch.sh

# Upload topology and configs
IP=<from launch output>
KEY=<from launch output>
ssh -i $KEY ubuntu@$IP 'mkdir -p ~/lab/mylab/configs ~/lab/src'
scp -i $KEY -r src/lab_builder ubuntu@$IP:~/lab/src/
scp -i $KEY topology.clab.yml ubuntu@$IP:~/lab/mylab/
scp -i $KEY configs/*.cfg ubuntu@$IP:~/lab/mylab/configs/
```

### Step 3: Deploy Topology

```bash
ssh -i $KEY ubuntu@$IP \
    'cd ~/lab/mylab && sudo containerlab deploy -t topology.clab.yml'
```

vJunos-router takes 5-10 minutes to boot. Monitor with:

```bash
ssh -i $KEY ubuntu@$IP 'sudo containerlab inspect -t ~/lab/mylab/topology.clab.yml'
```

Wait until all nodes show `(healthy)`.

### Step 4: Health Check

Verify SSH access and routing protocol convergence:

```bash
ssh -i $KEY ubuntu@$IP \
    'cd ~/lab && PYTHONPATH=src python3 -m lab_builder health-check mylab/topology.clab.yml'
```

This waits for SSH on all nodes, then polls BGP/OSPF/ISIS neighbor status
until sessions are established.

**Important**: health-check only verifies routing protocol convergence. It
does not check that the lab is actually demonstrating the intended behavior
(e.g., IRBs are up, expected routes are present, VXLAN tunnels are
established). Use the `validate` step below to verify lab state.

### Step 4.5: Validate Lab State

If the topology has a `checks.yaml` file, run validation checks to verify
the lab is in the expected state before collecting data:

```bash
ssh -i $KEY ubuntu@$IP \
    'cd ~/lab && PYTHONPATH=src python3 -m lab_builder validate mylab/topology.clab.yml --checks mylab/checks.yaml'
```

This runs topology-specific checks (interface state, route existence, BGP
peer status) and exits non-zero if any check fails. See the `checks.yaml`
format in `infra/examples/evpn-type5/checks.yaml` for an example.

If no `checks.yaml` exists, manually verify the lab state by connecting to
each node and checking:

- `show interfaces` — look for `hardware-down` flags on key interfaces
- `show route table <vrf>.inet.0` — confirm expected routes exist
- `show ethernet-switching vxlan-tunnel-endpoint remote` — confirm VXLAN
  tunnels (if applicable)

**Do not proceed to collection if the lab is in a degraded state.** Common
pitfalls:

- **IRBs hardware-down**: VLAN autostate deactivates IRBs when no
  switchport members are active in the VLAN. Verify access ports are wired
  in the containerlab topology and are oper-up.
- **Missing containerlab wiring**: Configs referencing interfaces that have
  no link in the topology YAML will have those interfaces oper-down.
- **Dead BGP peers**: Neighbors configured for nodes not in the topology
  will sit in Idle/Active, which may be harmless or may indicate a
  topology/config mismatch.

### Step 5: Collect Show Commands

```bash
ssh -i $KEY ubuntu@$IP \
    'cd ~/lab && PYTHONPATH=src python3 -m lab_builder collect mylab/topology.clab.yml --output-dir /tmp/collected'
```

Collects 9 show commands per Junos node (see "Show Commands Collected" below).
Files are named to match the lab-validation parser conventions.

### Step 6: Build Snapshot

```bash
ssh -i $KEY ubuntu@$IP \
    'cd ~/lab && PYTHONPATH=src python3 -m lab_builder build-snapshot mylab/topology.clab.yml --name junos_my_feature --collected-dir /tmp/collected --snapshots-dir /tmp/snapshots'
```

### Step 7: Download Snapshot

```bash
scp -i $KEY -r ubuntu@$IP:/tmp/snapshots/junos_my_feature snapshots/
```

### Step 8: Tear Down

```bash
AWS_PROFILE=<profile> ./ec2-teardown.sh
```

### Step 9: Validate Against Batfish

Locally (requires Batfish running):

```bash
pytest lab_tests/test_labs.py --labname=junos_my_feature -v --tb=short
```

### Step 10: Triage Failures

For each test failure, determine the cause:

- **Parser bug**: the lab-validation parsers can't handle the device output.
  Fix the parser, add unit tests.
- **Batfish modeling discrepancy**: Batfish predicts different routes or
  interfaces than the real device. File a GitHub issue in batfish/batfish or
  batfish/lab-validation and add a sickbay entry.
- **Config error in the lab**: fix the config, re-deploy, re-collect.
- **Expected difference**: management interfaces, pseudo-interfaces, etc. that
  Batfish intentionally doesn't model. Update the validator's exclusion logic.

## Iterating on a Lab

To modify configs without full redeploy (saves 5-10 min boot time):

```bash
# Push new config to a node
ssh -i $KEY ubuntu@$IP \
    'cd ~/lab && PYTHONPATH=src python3 -m lab_builder push-config mylab/topology.clab.yml r1 /path/to/new-config.txt'

# Re-collect just that node
ssh -i $KEY ubuntu@$IP \
    'cd ~/lab && PYTHONPATH=src python3 -m lab_builder recollect mylab/topology.clab.yml r1 --output-dir /tmp/collected'
```

Then re-download and re-validate locally.

## Scripts Reference

| Script            | Where it runs | Purpose                                                   |
| ----------------- | ------------- | --------------------------------------------------------- |
| `ec2-launch.sh`   | Local         | Launch EC2 with KVM, Docker, containerlab, images from S3 |
| `ec2-status.sh`   | Local         | Show all lab-validation instances, warn about orphans     |
| `ec2-teardown.sh` | Local         | Terminate instance and clean up                           |
| `upload-image.sh` | Local         | Upload qcow2 images to S3 (idempotent)                    |
| `build-image.sh`  | EC2           | Build vrnetlab Docker image from qcow2, upload to S3      |
| `ec2-setup.sh`    | EC2 (auto)    | Bootstrap script, runs as user-data                       |

## lab_builder CLI Reference

Run on EC2 as `PYTHONPATH=src python3 -m lab_builder <command>`:

| Command                                                                  | Purpose                              |
| ------------------------------------------------------------------------ | ------------------------------------ |
| `deploy <topo.yml>`                                                      | Deploy containerlab topology         |
| `inspect <topo.yml>`                                                     | Show discovered nodes and IPs        |
| `health-check <topo.yml> [--timeout N]`                                  | Wait for SSH + routing convergence   |
| `validate <topo.yml> --checks FILE`                                      | Run topology-level validation checks |
| `collect <topo.yml> --output-dir DIR`                                    | Collect show commands from all nodes |
| `recollect <topo.yml> NODE --output-dir DIR`                             | Re-collect one node                  |
| `push-config <topo.yml> NODE FILE`                                       | Push set-format config and commit    |
| `build-snapshot <topo.yml> --name N --collected-dir D --snapshots-dir S` | Package as snapshot                  |
| `destroy <topo.yml>`                                                     | Tear down topology                   |

## Show Commands Collected

For Juniper (vJunos-router), these are collected automatically:

| Command                                   | Goes to           | Purpose              |
| ----------------------------------------- | ----------------- | -------------------- |
| `show configuration \| display set`       | `configs/<node>/` | Device config        |
| `show route \| display json`              | `show/<node>/`    | Main routing table   |
| `show route protocol bgp \| display json` | `show/<node>/`    | BGP routes           |
| `show interfaces \| display json`         | `show/<node>/`    | Interface properties |
| `show route instance \| display json`     | `show/<node>/`    | VRF info             |
| `show version \| display json`            | `show/<node>/`    | Software version     |
| `show bgp neighbor \| display json`       | `show/<node>/`    | BGP peer status      |
| `show ospf neighbor \| display json`      | `show/<node>/`    | OSPF status          |
| `show isis adjacency \| display json`     | `show/<node>/`    | ISIS status          |

## Snapshot Directory Structure

The output matches the lab-validation framework's expected layout:

```
snapshots/<name>/
├── configs/
│   ├── <node1>/
│   │   └── show_configuration_|_display_set.txt
│   └── <node2>/
│       └── show_configuration_|_display_set.txt
├── show/
│   ├── host_nos.txt          # {"node1": "junos", "node2": "junos"}
│   ├── <node1>/
│   │   ├── show_route_|_display_json.txt
│   │   ├── show_route_protocol_bgp_|_display_json.txt
│   │   ├── show_interfaces_|_display_json.txt
│   │   └── ...
│   └── <node2>/
│       └── ...
└── validation/               # optional
    └── sickbay.yaml          # expected failure entries
```

## EC2 Instance Details

### Instance Types

Default is **m8i.2xlarge** (8 vCPU, 32 GB RAM). These support nested
virtualization via `--cpu-options NestedVirtualization=enabled`, which vrnetlab
needs to run VM-based router images inside Docker containers.

| Instance    | vCPU | RAM   | ~$/hr  | Routers |
| ----------- | ---- | ----- | ------ | ------- |
| m8i.xlarge  | 4    | 16 GB | ~$0.23 | 1-2     |
| m8i.2xlarge | 8    | 32 GB | ~$0.46 | 2-4     |
| m8i.4xlarge | 16   | 64 GB | ~$0.92 | 4-8     |

Each vJunos-router needs ~5 GB RAM and 4 vCPUs.

For spot pricing (~70% cheaper), add `--spot`.

### ec2-launch.sh Options

```
--instance-type TYPE   EC2 instance type (default: m8i.2xlarge)
--key-name NAME        Use existing EC2 key pair (auto-created if omitted)
--timeout-hours N      Auto-terminate after N hours (default: 4)
--spot                 Request spot instance
```

### Cost Safety

- Auto-terminate alarm after 4 hours (configurable)
- `ec2-status.sh` warns about orphaned instances
- The launch script prevents creating multiple tracked instances

### What Gets Installed (ec2-setup.sh)

- Docker CE
- containerlab (from netdevops apt repo)
- KVM/QEMU tools (qemu-kvm, libvirt)
- Python 3 with netmiko, paramiko, PyYAML, awscli
- Pre-built Docker images from S3 (or builds from qcow2 as fallback)

## Lab Design Principles

- **Simplicity**: minimum routers to demonstrate the feature (2-3 typical)
- **Feature isolation**: one feature per lab
- **Corner cases**: misconfigurations, asymmetric settings, boundary values
- **Reproducibility**: deterministic results, avoid time-dependent behavior
- **Documentation**: README explaining what the lab tests and why

## Supported Vendor Profiles

| containerlab kind       | Vendor              | Default creds     | Boot time | KVM required |
| ----------------------- | ------------------- | ----------------- | --------- | ------------ |
| `juniper_vjunosrouter`  | Junos (MX)          | admin / admin@123 | 5-10 min  | Yes          |
| `juniper_vjunosswitch`  | Junos (QFX)         | admin / admin@123 | 5-10 min  | Yes          |
| `juniper_vjunosevolved` | Junos Evolved (PTX) | admin / admin@123 | ~15 min   | Yes          |
| `juniper_crpd`          | Junos cRPD          | root / clab123    | ~1 min    | No           |

**Platform selection**: vJunos-router (MX) does NOT support `family
ethernet-switching`, VLANs with IRBs, or EVPN bridge domains. Labs that use
these features must use vJunos-switch (QFX). Use vJunos-router only for
pure IP routing (underlay, L3VPN, route reflectors, CE devices).

## Troubleshooting

**SSH connection refused after deploy**: vJunos-router takes 5-10 minutes to
boot. Wait for `(healthy)` in `containerlab inspect` output before attempting
SSH.

**Startup config not applied**: Configs must be in curly-brace format, not
set format. vrnetlab concatenates the config with its init.conf and mounts
it as a USB config disk.

**KVM not available**: Verify the instance type supports nested virtualization
(M8i/C8i/R8i families) and that `--cpu-options NestedVirtualization=enabled`
was used at launch. Check with `ls /dev/kvm` on the instance.

**Docker image not loaded**: Check `docker images | grep vjunos`. If empty,
the S3 bucket may not have the Docker tarball. The setup script falls back to
building from qcow2 if available.

**Node names wrong in collected data**: containerlab names containers as
`clab-<topology>-<node>`. The lab_builder extracts node names by stripping
this prefix. If node names contain hyphens, verify with
`python3 -m lab_builder inspect topology.clab.yml`.
