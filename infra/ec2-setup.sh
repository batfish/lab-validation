#!/usr/bin/env bash
#
# Bootstrap script for EC2 instances. Runs as user-data during instance launch.
# Installs Docker, containerlab, KVM/QEMU tools, Python dependencies,
# and loads network OS images.
#
# Image loading strategy (idempotent):
#   1. If pre-built Docker tarballs exist in s3://bucket/docker-images/, load them.
#   2. Otherwise, if raw qcow2 images exist in s3://bucket/images/, build
#      vrnetlab containers from them and upload the results to docker-images/.
#   3. If neither exists, skip (user will need to upload images later).
#
# The placeholder %%BUCKET_NAME%% is replaced by ec2-launch.sh before use.
#
# This script runs as root. Output goes to /var/log/cloud-init-output.log.
# Completion is signaled by writing to /var/log/ec2-setup-complete.

set -euo pipefail

BUCKET_NAME="%%BUCKET_NAME%%"

LOG_FILE="/var/log/ec2-setup.log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=== ec2-setup.sh starting at $(date -u) ==="
echo "Image bucket: ${BUCKET_NAME}"

export DEBIAN_FRONTEND=noninteractive

# System updates
echo "--- Updating system packages ---"
apt-get update -y
apt-get upgrade -y

# KVM/QEMU tools
echo "--- Installing KVM/QEMU tools ---"
apt-get install -y qemu-kvm libvirt-daemon-system virtinst cpu-checker

# Verify KVM
if [[ -e /dev/kvm ]]; then
    echo "KVM available: $(ls -la /dev/kvm)"
    chmod 666 /dev/kvm
else
    echo "WARNING: /dev/kvm not found. VM-based containerlab nodes will not work."
fi

# Docker (official repo)
echo "--- Installing Docker ---"
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" \
    > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin

usermod -aG docker ubuntu
usermod -aG kvm ubuntu

# Containerlab
echo "--- Installing containerlab ---"
echo "deb [trusted=yes] https://netdevops.fury.site/apt/ /" \
    > /etc/apt/sources.list.d/netdevops.list
apt-get update -y
apt-get install -y containerlab

# Python tools
echo "--- Installing Python tools ---"
apt-get install -y python3-pip python3-venv
pip3 install --break-system-packages --ignore-installed netmiko paramiko PyYAML
pip3 install --break-system-packages awscli

# --- Load network OS images ---
echo "--- Loading network OS images ---"

DOCKER_TARBALLS=$(aws s3 ls "s3://${BUCKET_NAME}/docker-images/" 2>/dev/null \
    | awk '{print $4}' | grep '\.tar\.gz$' || true)

if [[ -n "${DOCKER_TARBALLS}" ]]; then
    # Strategy 1: Load pre-built Docker images
    for tarball in ${DOCKER_TARBALLS}; do
        echo "Loading Docker image: ${tarball}"
        aws s3 cp "s3://${BUCKET_NAME}/docker-images/${tarball}" - | gunzip | docker load
    done
else
    echo "No pre-built Docker images found. Checking for raw qcow2 images..."

    RAW_IMAGES=$(aws s3 ls "s3://${BUCKET_NAME}/images/" 2>/dev/null \
        | awk '{print $4}' | grep '\.qcow2$' || true)

    if [[ -n "${RAW_IMAGES}" ]]; then
        # Strategy 2: Build from qcow2
        echo "Cloning vrnetlab..."
        sudo -u ubuntu git clone https://github.com/hellt/vrnetlab.git /home/ubuntu/vrnetlab

        for qcow2 in ${RAW_IMAGES}; do
            echo "Processing: ${qcow2}"

            case "${qcow2}" in
                vJunos-router-*|vjunos-router-*)
                    dest="/home/ubuntu/vrnetlab/juniper/vjunosrouter" ;;
                vJunosEvolved-*|vjunosevolved-*)
                    dest="/home/ubuntu/vrnetlab/juniper/vjunosevolved" ;;
                vJunos-switch-*|vjunosswitch-*)
                    dest="/home/ubuntu/vrnetlab/juniper/vjunosswitch" ;;
                *)
                    echo "  Unknown image type: ${qcow2}, skipping"
                    continue ;;
            esac

            echo "  Downloading from S3..."
            aws s3 cp "s3://${BUCKET_NAME}/images/${qcow2}" "${dest}/"

            echo "  Building vrnetlab container..."
            if (cd "${dest}" && make); then
                # Upload the built image to S3 for next time
                IMAGE_NAME=$(docker images --format '{{.Repository}}:{{.Tag}}' \
                    | grep -i junos | head -1)
                if [[ -n "${IMAGE_NAME}" ]]; then
                    TARBALL_NAME=$(echo "${IMAGE_NAME}" | sed 's|.*/||; s|:|_|; s|juniper_||')
                    echo "  Saving and uploading Docker image to S3..."
                    docker save "${IMAGE_NAME}" | gzip \
                        | aws s3 cp - "s3://${BUCKET_NAME}/docker-images/${TARBALL_NAME}.tar.gz"
                    echo "  Uploaded: docker-images/${TARBALL_NAME}.tar.gz"
                fi
            else
                echo "  WARNING: vrnetlab build failed for ${qcow2}"
            fi
        done
    else
        echo "No images found in S3. Upload images with upload-image.sh."
    fi
fi

# --- Load pre-built container images (e.g., Arista cEOS) ---
echo "--- Loading container images from S3 ---"

CONTAINER_TARBALLS=$(aws s3 ls "s3://${BUCKET_NAME}/images/" 2>/dev/null \
    | awk '{print $4}' | grep '\.tar\.xz$' || true)

if [[ -n "${CONTAINER_TARBALLS}" ]]; then
    for tarball in ${CONTAINER_TARBALLS}; do
        echo "Processing container image: ${tarball}"
        # Extract image name and tag from filename, e.g.:
        #   cEOS64-lab-4.36.0.1F.tar.xz -> ceos:4.36.0.1F
        base="${tarball%.tar.xz}"
        case "${base}" in
            cEOS64-lab-*|cEOS-lab-*)
                version="${base#*-lab-}"
                tag="ceos:${version}"
                ;;
            *)
                echo "  Unknown container image: ${tarball}, skipping"
                continue
                ;;
        esac

        if docker image inspect "${tag}" &>/dev/null; then
            echo "  Already loaded: ${tag}"
        else
            echo "  Importing as ${tag}..."
            aws s3 cp "s3://${BUCKET_NAME}/images/${tarball}" "/tmp/${tarball}"
            docker import "/tmp/${tarball}" "${tag}"
            rm -f "/tmp/${tarball}"
            echo "  Loaded: ${tag}"
        fi
    done
else
    echo "No .tar.xz container images found in S3."
fi

echo "--- Docker images ---"
docker images --format '  {{.Repository}}:{{.Tag}}  {{.Size}}' | grep -v '<none>' || echo "  (none)"

# Create working directory
sudo -u ubuntu mkdir -p /home/ubuntu/lab

# Summary
echo ""
echo "=== Setup complete at $(date -u) ==="
echo ""
echo "Installed versions:"
echo "  Docker: $(docker --version)"
echo "  Containerlab: $(containerlab version 2>/dev/null | head -1 || echo 'installed')"
echo "  Python: $(python3 --version)"
echo "  KVM: $(kvm-ok 2>/dev/null || echo '/dev/kvm present: '$(test -e /dev/kvm && echo yes || echo no))"

# Signal completion
date -u > /var/log/ec2-setup-complete
