# Lab Creation Infrastructure

Tools for creating new lab-validation snapshots using
[containerlab](https://containerlab.dev/) on AWS EC2. Supported network OSes
include Juniper vJunos, Arista cEOS, Cisco NX-OS (N9Kv), and Nokia SR OS
(SR-SIM) — see the Supported Vendor Profiles table below.

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
- **Arista cEOS-64 tar.xz image** (optional) — download from
  [Arista Software Download](https://www.arista.com/en/support/software-download)
  (requires Arista account)
- **Batfish** running locally for validation (Docker image or built from
  source)

## One-Time Setup

### 1. Download Images

Download vendor images and save them to `infra/images/` (gitignored):

- **Juniper**: `vJunos-router-*.qcow2` from Juniper's website
- **Arista**: `cEOS64-lab-*.tar.xz` from Arista's software download portal

```bash
ls infra/images/
# vJunos-router-25.4R1.12.qcow2
# cEOS64-lab-4.36.0.1F.tar.xz
```

### 2. Upload to S3

```bash
cd infra
AWS_PROFILE=<profile> ./upload-image.sh
```

This creates an S3 bucket named `lab-validation-images-<account-id>` (if it
doesn't exist) and uploads all qcow2 and tar.xz files from `infra/images/`.
Idempotent — skips files already in S3.

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

For working examples, the build inputs (topology, startup configs,
checks) live alongside each snapshot at `snapshots/<lab>/source/`. A
few starting points:

- `infra/examples/two-router-ebgp/` — minimal 2-router Junos eBGP
  template (no matching snapshot; reference only)
- `snapshots/eos_ceos_ebgp/source/` — minimal 2-router Arista cEOS eBGP lab
- `snapshots/junos_evpn_type5/source/` — 4-node EVPN Type 5 fabric (Junos)

**Interface mapping**: containerlab `ethN` maps to vendor interfaces:

| containerlab | Junos (vJunos-router) | Arista (cEOS) | NX-OS (N9Kv) |
| ------------ | --------------------- | ------------- | ------------ |
| eth0         | management (auto)     | Management0   | mgmt0        |
| eth1         | ge-0/0/0              | Ethernet1     | Ethernet1/1  |
| eth2         | ge-0/0/1              | Ethernet2     | Ethernet1/2  |
| eth3         | ge-0/0/2              | Ethernet3     | Ethernet1/3  |
| ethN         | ge-0/0/(N-1)          | EthernetN     | Ethernet1/N  |

**Nokia SR OS (SR-SIM)** does not use `ethN` endpoints. Its containerlab link
endpoints encode the SR OS port directly: drop the leading `e` and replace
each `-` with `/`. For example `e1-1-c1-1` → port `1/1/c1/1` (card 1, MDA 1,
connector 1, port 1) and `e1-2-3` → `1/2/3`. The port must also be provisioned
and broken out in the startup config; see `examples/srsim-ceos-ebgp/`.

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
format in `snapshots/junos_evpn_type5/source/checks.yaml` for an example.

If no `checks.yaml` exists, manually verify the lab state by connecting to
each node and checking:

- `show configuration` — look for `## Warning: configuration block ignored:
unsupported platform` comments, which indicate the device is silently
  dropping config (e.g., using vJunos-router for features that need
  vJunos-switch)
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

## Convergence Expectations

Once a vJunos node is booted and SSH-reachable, routing protocol
convergence and config operations are fast:

- **BGP convergence** after config push: < 30 seconds for small labs
  (2-4 nodes, < 200 prefixes).
- **`commit check`**: < 5 seconds for any reasonable policy.
- **`commit`**: < 15 seconds for labs of this size.
- **Health-check after deploy**: SSH comes up ~3-5 min after
  `containerlab deploy`; BGP converges within seconds of SSH.

If a command hasn't completed within 2× its expected time, something
is wrong — investigate rather than retry with a longer timeout.

### Operational principles

- **Verify the tool works before looping.** Run the check command once
  interactively before wrapping it in a polling loop. If it fails on
  the first try, fix the command — don't blindly retry.
- **Prefer bulk operations.** Push 100 config lines via `load set
terminal` (< 5 seconds) rather than per-line `send_command_timing`
  (minutes). Use binary search to isolate failures in a batch.
- **No absurd timeouts.** A 60-minute timeout on a command expected to
  finish in 10 seconds masks bugs. Set timeouts at 2× expected runtime.

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

### Pushing config to running Junos devices

When pushing config to a running vJunos device programmatically:

- **Use `load set terminal`** + paste all lines + `^D`. This is fast
  even for hundreds of lines. Do NOT push lines one at a time via
  netmiko's `send_command_timing` (~2s/line overhead).
- **Binary search on commit failure** — if bulk `commit check` fails,
  bisect the config into halves and re-check each. Isolates rejections
  in O(log N) commits instead of O(N).
- **Bracket syntax `[ A B ]`** cannot be reliably delivered through
  netmiko/SSH interactive sessions (`[` triggers Junos CLI multi-value
  entry mode). Use the desugared equivalent: two separate `set` lines
  (e.g., `community set A` + `community set B`). Junos stores them
  identically — `show configuration | display set` always emits the
  desugared form.
- **Large configs as startup**: if a config is too large or complex for
  interactive push, use it as the containerlab `startup-config`. If
  commit fails at boot, SSH never comes up — use a minimal startup
  config and push terms post-boot.

**Always re-collect after changing the lab.** The snapshot's
`configs/<node>/show_running-config.txt` and every file under
`show/<node>/` must come from the actual running device after your
change. Do not hand-edit collected show data to match an updated
startup config — the snapshot is the observed state of the real lab,
and editing it defeats the point of empirical validation. If you
change a startup config (e.g., add ECMP), redeploy (or push-config)
and re-run `collect` + `build-snapshot`.

### Adding or editing `checks.yaml`

`checks.yaml` lives alongside the topology in `snapshots/<lab>/source/`
and defines preconditions the lab must satisfy before collection
(interfaces up, specific routes learned, BGP peers Established). To
add or iterate on one:

1. Write `snapshots/<lab>/source/checks.yaml` (see
   `snapshots/junos_evpn_type5/source/checks.yaml` for the schema).
2. Upload to the EC2 box alongside the topology and run:
   ```bash
   ssh -i $KEY ubuntu@$IP \
       'cd ~/lab && PYTHONPATH=src python3 -m lab_builder validate mylab/topology.clab.yml --checks mylab/checks.yaml'
   ```
3. Adjust checks until everything passes against the deployed lab,
   then commit the final version to `snapshots/<lab>/source/`.

## What to check in

Only commit artifacts that were actually produced by (or fed into)
the lab process. Build inputs and collected outputs both live under
`snapshots/<lab>/`:

- `snapshots/<lab>/source/` — the inputs used to build the lab:
  `topology.clab.yml`, startup `configs/*.cfg`, and `checks.yaml`
  (if any). These must match what was last deployed to produce the
  snapshot.
- `snapshots/<lab>/configs/`, `show/`, `batfish/`, `validation/` —
  the outputs collected from the running lab plus hand-authored
  `batfish/layer1_topology.json` and `validation/sickbay.yaml`.

Do not commit files you did not exercise end-to-end. If `checks.yaml`
was never run against the lab, don't check it in yet — run it first.
If startup configs drifted from what produced the snapshot, either
redeploy+re-collect or revert the configs.

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

### Juniper (vJunos)

| Command                                          | Goes to           | Purpose                        |
| ------------------------------------------------ | ----------------- | ------------------------------ |
| `show configuration \| display set`              | `configs/<node>/` | Device config                  |
| `show route \| display json`                     | `show/<node>/`    | Main routing table             |
| `show route protocol bgp detail \| display json` | `show/<node>/`    | BGP routes (incl. communities) |
| `show interfaces \| display json`                | `show/<node>/`    | Interface properties           |
| `show route instance \| display json`            | `show/<node>/`    | VRF info                       |
| `show version \| display json`                   | `show/<node>/`    | Software version               |
| `show bgp neighbor \| display json`              | `show/<node>/`    | BGP peer status                |
| `show ospf neighbor \| display json`             | `show/<node>/`    | OSPF status                    |
| `show isis adjacency \| display json`            | `show/<node>/`    | ISIS status                    |

### Arista (cEOS)

| Command                                 | Goes to           | Purpose              |
| --------------------------------------- | ----------------- | -------------------- |
| `show running-config`                   | `configs/<node>/` | Device config        |
| `show ip route vrf all \| json`         | `show/<node>/`    | Main routing table   |
| `show ip bgp vrf all \| json`           | `show/<node>/`    | BGP routes           |
| `show ip bgp neighbors vrf all \| json` | `show/<node>/`    | BGP peer details     |
| `show interfaces \| json`               | `show/<node>/`    | Interface properties |
| `show vrf \| json`                      | `show/<node>/`    | VRF info             |
| `show version \| json`                  | `show/<node>/`    | Software version     |
| `show bgp evpn \| json`                 | `show/<node>/`    | EVPN routes          |
| `show ip ospf neighbor \| json`         | `show/<node>/`    | OSPF status          |
| `show isis neighbors \| json`           | `show/<node>/`    | ISIS status          |

### Cisco NX-OS (N9Kv)

| Command                    | Goes to           | Purpose              |
| -------------------------- | ----------------- | -------------------- |
| `show running-config`      | `configs/<node>/` | Device config        |
| `show interface`           | `show/<node>/`    | Interface properties |
| `show ip route vrf all`    | `show/<node>/`    | Main routing table   |
| `show ip bgp vrf all`      | `show/<node>/`    | BGP routes           |
| `show ip bgp all neighbor` | `show/<node>/`    | BGP peer details     |
| `show version`             | `show/<node>/`    | Software version     |
| `show vrf`                 | `show/<node>/`    | VRF info             |

### Nokia SR OS (SR-SIM)

SR OS runs MD-CLI. It does NOT support Junos-style `show … | display json`, but it
DOES emit JSON from the **`info`** family: `info json <path>` (json modifier BEFORE the
path) renders config or operational state as JSON keyed by the YANG modules. Automation
reads the operational `state` branch with `info json /state …` — the SR OS analog of
`show | display json`. (Confirmed live on SR-SIM 26.3.R1, 2026-06-05; 26.3.R1 MD-CLI
Quick Reference, Table 4.) A few plain-text `show router …` are also captured for humans.

| Command                                         | Goes to           | Purpose                   |
| ----------------------------------------------- | ----------------- | ------------------------- |
| `admin show configuration`                      | `configs/<node>/` | Device config (MD-CLI)    |
| `info json /state system`                       | `show/<node>/`    | System state (JSON)       |
| `info json /state router "Base" interface *`    | `show/<node>/`    | Interface state (JSON)    |
| `info json /state router "Base" route-table`    | `show/<node>/`    | Main routing table (JSON) |
| `info json /state router "Base" bgp neighbor *` | `show/<node>/`    | BGP peer state (JSON)     |
| `info json /state router "Base" bgp rib`        | `show/<node>/`    | BGP RIB (JSON)            |
| `info json /state router "Base" ospf *`         | `show/<node>/`    | OSPF state (JSON)         |
| `info json /state router "Base" isis *`         | `show/<node>/`    | ISIS state (JSON)         |
| `show version` + `show router …`                | `show/<node>/`    | Plain-text cross-check    |

## Snapshot Directory Structure

The output matches the lab-validation framework's expected layout:

```
snapshots/<name>/
├── source/                   # build inputs (hand-authored)
│   ├── topology.clab.yml
│   ├── configs/              # startup configs in vendor source format
│   │   └── <node>.cfg
│   ├── checks.yaml           # optional preconditions
│   └── README.md             # optional lab notes
├── configs/                  # collected from running device
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
    ├── sickbay.yaml          # expected failure entries
    └── parse_warnings.yaml   # parser-rejection assertions (see below)
```

### `validation/parse_warnings.yaml` (optional)

When absent, every host is asserted to produce zero FATAL parse warnings
(`Parse warning (redflag)` rows whose `Details` start with `FATAL:`). To
assert that a host _should_ produce a FATAL warning — e.g., a snapshot
that exists to verify parser rejection like
`snapshots/junos_commit_check/` — add an `expects_fatal_warning` entry
naming the host and a `contains` substring that must appear in the
warning details. To suppress a known FATAL warning on a host, sickbay
the `test_parse_warnings` test for that host in
`validation/sickbay.yaml`.

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
--images FILTER        Comma-separated list of images to load (default: all)
                       Available: ceos, vjunos-router, vjunos-switch, vjunos-evolved, nxos
```

For example, `--images ceos` loads only the Arista cEOS image, skipping
the large Juniper VM images and reducing bootstrap time from ~5 min to
~2 min.

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
- **Determinism**: eliminate ties that can be broken differently by the
  device vs. Batfish, or non-deterministically across reboots (e.g.,
  some vendors' default BGP tiebreaker is "oldest path"). Common
  techniques, using whatever the vendor's equivalent CLI is:
  - **Deterministic tiebreakers**: force tiebreaks to use router-id
    rather than path age.
  - **ECMP**: enable multipath so equal-cost paths are all active,
    sidestepping tiebreakers entirely.
  - **Differentiated candidates**: give routes distinct local-prefs,
    MEDs, or AS-path lengths so best-path selection is unambiguous
    before the tiebreak stage.
- **Documentation**: README explaining what the lab tests and why

## Supported Vendor Profiles

| containerlab kind       | Vendor              | Default creds     | Boot time | KVM required |
| ----------------------- | ------------------- | ----------------- | --------- | ------------ |
| `juniper_vjunosrouter`  | Junos (MX)          | admin / admin@123 | 5-10 min  | Yes          |
| `juniper_vjunosswitch`  | Junos (QFX)         | admin / admin@123 | 5-10 min  | Yes          |
| `juniper_vjunosevolved` | Junos Evolved (PTX) | admin / admin@123 | ~15 min   | Yes          |
| `juniper_crpd`          | Junos cRPD          | root / clab123    | ~1 min    | No           |
| `arista_ceos`           | Arista EOS          | admin / admin     | ~1 min    | No           |
| `cisco_n9kv`            | Cisco NX-OS (N9Kv)  | admin / admin     | 5-10 min  | Yes          |
| `nokia_srsim`           | Nokia SR OS (SR-1)  | admin / admin     | ~2 min    | No\*         |

\* SR-SIM is a native container, but the install guide specifies Intel x86
and will not boot on ARM. Our default m8i instances satisfy this.

**Junos platform selection**: vJunos-router (MX) does NOT support `family
ethernet-switching`, VLANs with IRBs, or EVPN bridge domains. Labs that use
these features must use vJunos-switch (QFX). Use vJunos-router only for
pure IP routing (underlay, L3VPN, route reflectors, CE devices).

**Arista cEOS**: Container-native EOS image. No KVM required, boots in
under a minute. Startup configs use standard EOS CLI format. cEOS-64
(64-bit) is required for containerlab.

**Cisco NX-OS (N9Kv)**: Nexus 9000v virtual switch image running NX-OS.
Requires KVM (vrnetlab-based). Startup configs use standard NX-OS CLI
format. Interface mapping: eth1 → Ethernet1/1, eth2 → Ethernet1/2, etc.

**Nokia SR OS (SR-SIM)**: Native container loaded from `srsim.tar.xz` via
`docker load` (image tag `localhost/nokia/srsim:<version>`). Requires a Nokia
license mounted at `/nokia/license/license.txt`; in containerlab this is the
`license:` key under the `nokia_srsim` kind, and SR-SIM will not boot without
a valid one (license rejection happens inside the container, not at deploy).
Datapath interface mapping differs from other vendors: the containerlab link
endpoint encodes the SR OS port directly (`e1-1-c1-1` → port `1/1/c1/1`).
Batfish does not yet model SR OS, so SR OS labs capture source-of-truth data
rather than being validated against Batfish. See
`examples/srsim-ceos-ebgp/`.

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
