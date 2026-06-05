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
IMAGE_FILTER="%%IMAGE_FILTER%%"
TIMEOUT_MINUTES="%%TIMEOUT_MINUTES%%"

LOG_FILE="/var/log/ec2-setup.log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=== ec2-setup.sh starting at $(date -u) ==="
echo "Image bucket: ${BUCKET_NAME}"
echo "Image filter: ${IMAGE_FILTER}"

# Schedule auto-shutdown. The instance is configured with
# InstanceInitiatedShutdownBehavior=terminate, so this terminates it.
echo "Scheduling shutdown in ${TIMEOUT_MINUTES} minutes"
shutdown -h +${TIMEOUT_MINUTES}

# Check if an image tag matches the filter.
# Usage: image_wanted <tag>  (e.g., image_wanted "vjunos-router")
# Returns 0 (true) if the filter is "all" or contains the tag.
image_wanted() {
    local tag="$1"
    [[ "${IMAGE_FILTER}" == "all" ]] && return 0
    echo ",${IMAGE_FILTER}," | grep -q ",${tag},"
}

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

# Debugging tools
echo "--- Installing debugging tools ---"
apt-get install -y sshpass jq

# --- Load network OS images ---
echo "--- Loading network OS images ---"

# Map a docker-tarball or qcow2 filename to (image_tag, image_grep, vrnetlab_dest).
# Sets globals: image_tag, image_grep, dest. Returns 0 on match, 1 on unknown.
classify_image() {
    local name="$1"
    case "${name}" in
        vJunos-router-*|vjunos-router-*)
            image_tag="vjunos-router"
            image_grep="junos"
            dest="/home/ubuntu/vrnetlab/juniper/vjunosrouter" ;;
        vJunosEvolved-*|vjunosevolved-*)
            image_tag="vjunos-evolved"
            image_grep="junos"
            dest="/home/ubuntu/vrnetlab/juniper/vjunosevolved" ;;
        vJunos-switch-*|vjunosswitch-*)
            image_tag="vjunos-switch"
            image_grep="junos"
            dest="/home/ubuntu/vrnetlab/juniper/vjunosswitch" ;;
        nexus9300v*|nexus9500v*|nxosv*|n9kv*|*nxos*)
            image_tag="nxos"
            image_grep="n9kv|nxos"
            dest="/home/ubuntu/vrnetlab/cisco/n9kv" ;;
        *veos*|*arista*)
            image_tag="veos"
            image_grep="veos"
            dest="" ;;
        *)
            return 1 ;;
    esac
    return 0
}

# Strategy 1: load any pre-built Docker tarballs that match the filter.
DOCKER_TARBALLS=$(aws s3 ls "s3://${BUCKET_NAME}/docker-images/" 2>/dev/null \
    | awk '{print $4}' | grep '\.tar\.gz$' || true)

LOADED_TAGS=""
for tarball in ${DOCKER_TARBALLS}; do
    if ! classify_image "${tarball}"; then
        echo "Skipping unknown docker-images/ tarball: ${tarball}"
        continue
    fi
    if ! image_wanted "${image_tag}"; then
        echo "Skipping ${tarball} (not in filter: ${IMAGE_FILTER})"
        continue
    fi
    echo "Loading Docker image: ${tarball}"
    aws s3 cp "s3://${BUCKET_NAME}/docker-images/${tarball}" - | gunzip | docker load
    LOADED_TAGS="${LOADED_TAGS},${image_tag}"
done

# Strategy 2: for any wanted image lacking a pre-built tarball, build from qcow2.
RAW_IMAGES=$(aws s3 ls "s3://${BUCKET_NAME}/images/" 2>/dev/null \
    | awk '{print $4}' | grep '\.qcow2$' || true)

VRNETLAB_CLONED=false
for qcow2 in ${RAW_IMAGES}; do
    if ! classify_image "${qcow2}"; then
        echo "Skipping unknown images/ qcow2: ${qcow2}"
        continue
    fi
    if ! image_wanted "${image_tag}"; then
        continue
    fi
    if [[ ",${LOADED_TAGS}," == *",${image_tag},"* ]]; then
        echo "Skipping qcow2 build for ${qcow2}: ${image_tag} already loaded from docker-images/"
        continue
    fi

    echo "Processing qcow2: ${qcow2}"
    if [[ "${VRNETLAB_CLONED}" == false ]]; then
        echo "Cloning vrnetlab..."
        sudo -u ubuntu git clone https://github.com/hellt/vrnetlab.git /home/ubuntu/vrnetlab
        VRNETLAB_CLONED=true
    fi

    mkdir -p "${dest}"

    # vrnetlab's Cisco n9kv Makefile expects qcow2 named n9kv-<version>.qcow2
    # so the resulting docker tag is vrnetlab/cisco_n9kv:<version>.
    # Rename Cisco's nexus9300v64.<version>.qcow2 accordingly.
    staged_name="${qcow2}"
    if [[ "${image_tag}" == "nxos" ]]; then
        staged_name=$(echo "${qcow2}" \
            | sed -E 's/^nexus9[35]00v(64)?(-lite)?\.(.+)\.qcow2$/n9kv-\3.qcow2/')
    fi

    echo "  Downloading from S3 as ${staged_name}..."
    aws s3 cp "s3://${BUCKET_NAME}/images/${qcow2}" "${dest}/${staged_name}"

    echo "  Building vrnetlab container..."
    if (cd "${dest}" && make); then
        IMAGE_NAME=$(docker images --format '{{.Repository}}:{{.Tag}}' \
            | { grep -iE "${image_grep}" || true; } | head -1)
        if [[ -n "${IMAGE_NAME}" ]]; then
            TARBALL_NAME=$(echo "${IMAGE_NAME}" \
                | sed 's|.*/||; s|:|_|; s|juniper_||; s|cisco_||')
            echo "  Saving and uploading ${IMAGE_NAME} to s3://${BUCKET_NAME}/docker-images/${TARBALL_NAME}.tar.gz..."
            if docker save "${IMAGE_NAME}" | gzip \
                    | aws s3 cp - "s3://${BUCKET_NAME}/docker-images/${TARBALL_NAME}.tar.gz"; then
                echo "  Uploaded: docker-images/${TARBALL_NAME}.tar.gz"
            else
                echo "  WARNING: failed to upload ${IMAGE_NAME} to S3 (image is loaded locally; future launches will rebuild from qcow2)"
            fi
        else
            echo "  WARNING: build succeeded but no docker image matched '${image_grep}'"
        fi
        LOADED_TAGS="${LOADED_TAGS},${image_tag}"
    else
        echo "  WARNING: vrnetlab build failed for ${qcow2}"
    fi
done

if [[ -z "${DOCKER_TARBALLS}" && -z "${RAW_IMAGES}" ]]; then
    echo "No images found in S3. Upload images with upload-image.sh."
fi

# --- Load pre-built container images (e.g., Arista cEOS) ---
echo "--- Loading container images from S3 ---"

CONTAINER_TARBALLS=$(aws s3 ls "s3://${BUCKET_NAME}/images/" 2>/dev/null \
    | awk '{print $4}' | grep '\.tar\.xz$' || true)

if [[ -n "${CONTAINER_TARBALLS}" ]]; then
    for tarball in ${CONTAINER_TARBALLS}; do
        echo "Processing container image: ${tarball}"
        # Extract image name, tag, and load method from filename.
        #   cEOS64-lab-4.36.0.1F.tar.xz -> ceos:4.36.0.1F   (filesystem import)
        #   srsim*.tar.xz               -> Nokia SR-SIM      (docker load)
        # cEOS ships as a root filesystem (docker import); SR-SIM ships as a
        # tagged OCI image (docker load restores localhost/nokia/srsim:<ver>).
        base="${tarball%.tar.xz}"
        method="import"
        filter_tag=""
        case "${base}" in
            cEOS64-lab-*|cEOS-lab-*)
                version="${base#*-lab-}"
                tag="ceos:${version}"
                filter_tag="ceos"
                method="import"
                ;;
            srsim*|*srsim*)
                # docker load restores the tag embedded in the image
                # (localhost/nokia/srsim:<version>); no tag to compute here.
                tag=""
                filter_tag="srsim"
                method="load"
                ;;
            *)
                echo "  Unknown container image: ${tarball}, skipping"
                continue
                ;;
        esac
        if ! image_wanted "${filter_tag}"; then
            echo "  Skipping ${tarball} (not in filter: ${IMAGE_FILTER})"
            continue
        fi

        if [[ "${method}" == "load" ]]; then
            echo "  Loading Docker image from ${tarball}..."
            aws s3 cp "s3://${BUCKET_NAME}/images/${tarball}" "/tmp/${tarball}"
            # xz-compressed; docker load handles the decompression.
            docker load -i "/tmp/${tarball}"
            rm -f "/tmp/${tarball}"
        elif docker image inspect "${tag}" &>/dev/null; then
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
