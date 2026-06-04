# SR-SIM + cEOS two-router eBGP lab

A minimal two-router eBGP lab pairing a Nokia SR-SIM (SR OS) router with an
Arista cEOS router. This is the first lab exercising the `nokia_srsim`
containerlab kind in `lab_builder`.

```
r1 (SR-SIM, AS 65001) ---[1/1/c1/1]---[Ethernet1]--- r2 (cEOS, AS 65002)
  system 1.1.1.1/32                                    Loopback0 2.2.2.2/32
  link 10.0.0.0/31                                     link 10.0.0.1/31
```

After convergence each router advertises its loopback and learns the other's
via eBGP.

## Why this lab exists

This is **step one of adding Nokia SR OS support to Batfish**. Batfish cannot
yet parse or model SR OS configurations (no SR OS grammar or vendor model
exists in `batfish/batfish`). So this lab is **not** validated against Batfish.
Its purpose is to capture SR OS operational data — the running config and show
command outputs — that will serve as the "source of truth" validation target
once an SR OS parser and vendor model are built.

Pairing SR-SIM with cEOS (already supported and Batfish-modeled) keeps the
non-SR-OS side of the lab a known-good reference.

## Prerequisites

### License (required — SR-SIM will not boot without it)

SR-SIM requires a valid Nokia license mounted at `/nokia/license/license.txt`.
Containerlab provides it via the `license:` key in `topology.clab.yml`. Place
the Nokia-provided license file on the EC2 host and point the `license:` key
at it (default path in the topology: `/home/ubuntu/srsim-license.txt`).

### Image

The SR-SIM Docker image (`localhost/nokia/srsim:26.3.R1`) is loaded from the
`srsim.tar.xz` shipped in the Nokia SR-SIM download via `docker load`. Upload
it to S3 with `upload-image.sh` and it loads automatically on EC2 launch (or
filter with `--images srsim,ceos`).

## Build steps

```bash
# Upload images (SR-SIM tarball + cEOS) to S3
AWS_PROFILE=adcv ./infra/upload-image.sh

# Launch EC2 (loads srsim + ceos)
AWS_PROFILE=adcv ./infra/ec2-launch.sh --images srsim,ceos

# Copy the license to the host and update the license: path if needed
scp -i <key> srsim-license.txt ubuntu@<ip>:/home/ubuntu/srsim-license.txt

# Deploy, health-check, validate, collect, build snapshot (on EC2)
python -m lab_builder deploy topology.clab.yml
python -m lab_builder health-check topology.clab.yml
python -m lab_builder validate topology.clab.yml --checks checks.yaml
python -m lab_builder collect topology.clab.yml --output-dir /tmp/collected
python -m lab_builder build-snapshot topology.clab.yml \
    --name srsim_ceos_ebgp --collected-dir /tmp/collected --snapshots-dir /tmp/snapshots
```

## Captured data

`collected-snapshot/` holds the source-of-truth data captured from this lab:
the SR OS running config (`configs/r1/`), cEOS config (`configs/r2/`), per-node
show outputs (`show/`), and the generated `batfish/layer1_topology.json`. It is
kept here rather than under top-level `snapshots/` because that directory is
auto-discovered by the lab-validation CI, which would try to validate the
`sros` host against Batfish — and there is no SR OS model yet. When SR OS
modeling lands, this data becomes the validation target and can move into
`snapshots/`.

## Verified behavior (SR OS 26.3.R1, containerlab 0.76.0)

This lab was deployed end-to-end on EC2 with a valid license. Confirmed:

- The SR-SIM boots from `configs/r1.cfg` as a startup config (`Loaded 312
lines ... Committing configuration ... finished`) and eBGP converges with no
  manual steps. All four `checks.yaml` checks pass.
- Both routers learn each other's loopback via eBGP (r1 learns 2.2.2.2/32,
  r2 learns 1.1.1.1/32).

Notes on the SR OS config, learned by building this lab:

- **MD-CLI, not classic CLI.** `nokia_srsim` runs MD-CLI; the startup config
  is in MD-CLI curly-brace format.
- **Hardware must be provisioned.** The SR-1's line card and MDA are not
  present by default — `card 1 card-type iom-1` + `mda 1 mda-type
me6-100gb-qsfp28`, then the 100G connector is broken out (`port 1/1/c1
connector breakout c1-100g`) to expose port `1/1/c1/1`.
- **eBGP routes are rejected by default.** SR OS drops received eBGP routes
  unless an import policy accepts them — hence the `import-all` policy. An
  export policy is likewise required to advertise the system address.
- **The `system { security { ... } }` block is required in the startup
  config.** SR OS auto-generates SSH server ciphers/MACs and the default admin
  user on a first boot, but a startup config that includes any `system
security` subtree replaces those defaults. The config therefore carries the
  full materialized security block (admin user + SSH cipher/MAC lists); without
  it, SSH collection fails to negotiate ciphers or authenticate. The admin
  password is the public SR-SIM default.

No Batfish validation: there is no SR OS model yet. The captured data is
groundwork for that future work.
