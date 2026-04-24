#!/usr/bin/env bash
#
# Ensure VM images from infra/images/ are uploaded to S3.
# Creates the S3 bucket if it doesn't exist. Skips images already present.
#
# Usage:
#   ./upload-image.sh                    # Upload all images in infra/images/
#   ./upload-image.sh path/to/file.qcow2 # Upload a specific image
#
# This is idempotent: run it as many times as you want.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="${SCRIPT_DIR}/images"

# Derive bucket name from account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
BUCKET_NAME="lab-validation-images-${ACCOUNT_ID}"

# Create bucket if it doesn't exist
if ! aws s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
    echo "Creating S3 bucket: ${BUCKET_NAME} in ${REGION}"
    if [[ "${REGION}" == "us-east-1" ]]; then
        aws s3api create-bucket --bucket "${BUCKET_NAME}"
    else
        aws s3api create-bucket --bucket "${BUCKET_NAME}" \
            --create-bucket-configuration "LocationConstraint=${REGION}"
    fi
    aws s3api put-public-access-block --bucket "${BUCKET_NAME}" \
        --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
fi

# Collect files to upload
if [[ $# -ge 1 ]]; then
    FILES=("$@")
else
    FILES=()
    for f in "${IMAGES_DIR}"/*.qcow2 "${IMAGES_DIR}"/*.tar.xz; do
        [[ -f "${f}" ]] && FILES+=("${f}")
    done
    if [[ ${#FILES[@]} -eq 0 ]]; then
        echo "No .qcow2 or .tar.xz files found in ${IMAGES_DIR}/"
        echo "Download Juniper images from https://www.juniper.net/us/en/dm/vjunos-labs.html"
        echo "Download Arista cEOS images from https://www.arista.com/en/support/software-download"
        exit 0
    fi
fi

# Upload each file, skipping if already present
for filepath in "${FILES[@]}"; do
    filename=$(basename "${filepath}")
    s3_key="images/${filename}"

    if aws s3api head-object --bucket "${BUCKET_NAME}" --key "${s3_key}" &>/dev/null; then
        echo "Already in S3: ${filename}"
    else
        echo "Uploading ${filename} to s3://${BUCKET_NAME}/${s3_key}"
        aws s3 cp "${filepath}" "s3://${BUCKET_NAME}/${s3_key}"
    fi
done

echo ""
echo "Bucket: ${BUCKET_NAME}"
echo "Contents:"
aws s3 ls "s3://${BUCKET_NAME}/images/" 2>/dev/null || echo "  (empty)"
aws s3 ls "s3://${BUCKET_NAME}/docker-images/" 2>/dev/null || echo "  (no docker images yet)"
