# Two-node Aruba AOS-CX vrnetlab lab

This example uses the upstream `aruba_aoscx` containerlab kind. vrnetlab
packages the Aruba QEMU VM inside a Docker image and handles the first-boot
password, management interface, and startup-config injection.

The topology is:

```text
        10.0.0.0/31
  cx1 ---------------- cx2
  1.1.1.1/32       2.2.2.2/32
```

The routed link uses AOS-CX `1/1/1`; the vrnetlab management path is separate
from the numbered AOS-CX interfaces.

## Image preparation

Upload the vendor OVA to the private lab image bucket:

```bash
AWS_PROFILE=adcv ./infra/upload-image.sh \
  ~/Downloads/AOS-CX_Switch_Simulator_10_17_1021_ova/AOS-CX_10_17_1021.ova
```

On an EC2 host with Docker, KVM, and the S3 instance role, build and cache the
vrnetlab image:

```bash
./infra/build-aoscx-image.sh \
  s3://BUCKET/images/AOS-CX_10_17_1021.ova 10.17.1021
```

The build caches the extracted VMDK under `images/` and the Docker image as
`docker-images/aoscx-10.17.1021.tar.gz`. The build currently uses the
upstream vrnetlab wrapper from `hellt/vrnetlab`; AOS-CX 10.17 has not been
listed among that wrapper's upstream tested releases, so the first build and
boot should be treated as a compatibility test.

Future hosts can load the Docker image without rebuilding:

```bash
AWS_PROFILE=adcv ./infra/ec2-launch.sh --images aoscx
```

## Deploy, converge, and collect

Run these commands from this directory on the EC2 host:

```bash
PYTHONPATH=src python3 -m lab_builder deploy topology.clab.yml
PYTHONPATH=src python3 -m lab_builder health-check topology.clab.yml
PYTHONPATH=src python3 -m lab_builder validate topology.clab.yml \
  --checks checks.yaml
PYTHONPATH=src python3 -m lab_builder collect topology.clab.yml \
  --output-dir collected
```

The collector captures configuration, startup JSON, interfaces, IPv4/IPv6
routes, VRFs, VLANs, software version, BGP/EVPN, and OSPF state. Operational
commands are stored as CLI text because AOS-CX does not provide JSON
modifiers for these commands; `show startup-config json` is the structured
configuration capture.

Build a standard lab-validation snapshot after collection:

```bash
PYTHONPATH=src python3 -m lab_builder build-snapshot topology.clab.yml \
  --name aoscx_static --collected-dir collected --snapshots-dir snapshots
```

Destroy the lab when finished:

```bash
PYTHONPATH=src python3 -m lab_builder destroy topology.clab.yml
```
