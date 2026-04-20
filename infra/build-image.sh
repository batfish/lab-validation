#!/usr/bin/env bash
#
# Build a vrnetlab container image from a qcow2 and upload the result to S3.
# Run this on a running lab-validation EC2 instance.
#
# Usage (on EC2 instance):
#   ./build-image.sh <path-to-qcow2>
#   ./build-image.sh ~/vrnetlab/juniper/vjunosrouter/vJunos-router-25.4R1.12.qcow2
#
# This is a one-time operation per image version. After building, the Docker
# image tarball is uploaded to S3 so future EC2 instances load it directly
# without needing to rebuild.

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $(basename "$0") <path-to-qcow2>" >&2
    echo "" >&2
    echo "The qcow2 must be in the correct vrnetlab directory, e.g.:" >&2
    echo "  ~/vrnetlab/juniper/vjunosrouter/vJunos-router-25.4R1.12.qcow2" >&2
    exit 1
fi

QCOW2_PATH="$1"
if [[ ! -f "${QCOW2_PATH}" ]]; then
    echo "Error: file not found: ${QCOW2_PATH}" >&2
    exit 1
fi

QCOW2_DIR=$(dirname "${QCOW2_PATH}")
QCOW2_FILE=$(basename "${QCOW2_PATH}")

# Get the bucket name from instance metadata/tags or environment
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || true)
BUCKET_NAME="${LAB_VALIDATION_BUCKET:-lab-validation-images-${ACCOUNT_ID}}"

echo "Building vrnetlab container from ${QCOW2_FILE}..."
echo "Build directory: ${QCOW2_DIR}"
(cd "${QCOW2_DIR}" && sudo make)

# Find the built image
IMAGE_NAME=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep -i junos | head -1)
if [[ -z "${IMAGE_NAME}" ]]; then
    echo "Error: no junos Docker image found after build." >&2
    exit 1
fi
echo "Built image: ${IMAGE_NAME}"

# Extract a clean name for the tarball
# e.g., vrnetlab/juniper_vjunos-router:25.4R1.12 -> vjunos-router-25.4R1.12
TARBALL_NAME=$(echo "${IMAGE_NAME}" | sed 's|.*/||; s|:|_|; s|juniper_||')
TARBALL_PATH="/tmp/${TARBALL_NAME}.tar.gz"

echo "Saving to ${TARBALL_PATH}..."
docker save "${IMAGE_NAME}" | gzip > "${TARBALL_PATH}"
ls -lh "${TARBALL_PATH}"

echo "Uploading to s3://${BUCKET_NAME}/docker-images/"
aws s3 cp "${TARBALL_PATH}" "s3://${BUCKET_NAME}/docker-images/${TARBALL_NAME}.tar.gz"

echo ""
echo "Done. Future EC2 instances will load this image automatically on boot."
echo "Image: ${IMAGE_NAME}"
echo "S3:    s3://${BUCKET_NAME}/docker-images/${TARBALL_NAME}.tar.gz"
