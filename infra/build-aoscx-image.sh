#!/usr/bin/env bash
#
# Build the upstream vrnetlab ArubaOS-CX image and cache it in S3.
#
# Usage on EC2:
#   ./build-aoscx-image.sh s3://BUCKET/images/AOS-CX_10_17_1021.ova 10.17.1021
#
# The source OVA is retained in S3. The extracted VMDK and Docker image are
# derived cache artifacts and are safe to rebuild from that source.

set -euo pipefail

SOURCE_URI="${1:-}"
RELEASE="${2:-10.17.1021}"
VRNETLAB_ROOT="${VRNETLAB_ROOT:-/home/ubuntu/vrnetlab}"
IMAGE_DIR="${VRNETLAB_ROOT}/aruba/aoscx"

die() {
    echo "Error: $*" >&2
    exit 1
}

need_command() {
    command -v "$1" >/dev/null || die "missing required command: $1"
}

[[ "${SOURCE_URI}" == s3://*.ova ]] || \
    die "usage: $0 s3://BUCKET/KEY.ova [release]"
need_command aws
need_command docker
need_command git
need_command tar

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET_NAME="${LAB_VALIDATION_BUCKET:-lab-validation-images-${ACCOUNT_ID}}"
SOURCE_PATH="${SOURCE_URI#s3://}"
SOURCE_BUCKET="${SOURCE_PATH%%/*}"
SOURCE_KEY="${SOURCE_PATH#*/}"
VMDK_URI="s3://${SOURCE_BUCKET}/${SOURCE_KEY%.ova}.vmdk"
WORK_DIR="${HOME}/.cache/aoscx"
mkdir -p "${WORK_DIR}" "${IMAGE_DIR}"

if [[ ! -d "${VRNETLAB_ROOT}/.git" ]]; then
    echo "Cloning vrnetlab..."
    clone_dir="${WORK_DIR}/vrnetlab"
    rm -rf "${clone_dir}"
    git clone --depth 1 https://github.com/hellt/vrnetlab.git "${clone_dir}"
    mkdir -p "${VRNETLAB_ROOT}"
    cp -a "${clone_dir}/." "${VRNETLAB_ROOT}/"
fi

VMDK_PATH="$(find "${IMAGE_DIR}" -maxdepth 1 -type f -name '*.vmdk' -print -quit)"
VMDK_NAME="${VMDK_PATH##*/}"
if [[ -z "${VMDK_PATH}" || ! "${VMDK_NAME}" =~ ^arubaoscx-disk-image-genericx86-p4-.*\.vmdk$ ]]; then
    rm -f "${VMDK_PATH}"
    VMDK_PATH=""
fi

if [[ -z "${VMDK_PATH}" ]]; then
    cached_vmdk_name=""
    if cached_vmdk_name="$(aws s3api head-object --bucket "${SOURCE_BUCKET}" \
        --key "${SOURCE_KEY%.ova}.vmdk" \
        --query 'Metadata.vmdk-name' --output text 2>/dev/null)" \
        && [[ "${cached_vmdk_name}" != "None" ]]; then
        VMDK_NAME="${cached_vmdk_name}"
        VMDK_PATH="${IMAGE_DIR}/${VMDK_NAME}"
        echo "Downloading cached VMDK: ${VMDK_URI}"
        aws s3 cp "${VMDK_URI}" "${VMDK_PATH}"
    else
        OVA_PATH="${WORK_DIR}/$(basename "${SOURCE_KEY}")"
        EXTRACT_DIR="${WORK_DIR}/extracted"
        echo "Downloading source OVA: ${SOURCE_URI}"
        aws s3 cp "${SOURCE_URI}" "${OVA_PATH}"
        rm -rf "${EXTRACT_DIR}"
        mkdir -p "${EXTRACT_DIR}"
        tar -xf "${OVA_PATH}" -C "${EXTRACT_DIR}"
        extracted_vmdk="$(find "${EXTRACT_DIR}" -maxdepth 1 -type f \
            -name '*.vmdk' -print -quit)"
        [[ -n "${extracted_vmdk}" ]] || die "OVA did not contain a VMDK"
        VMDK_NAME="$(basename "${extracted_vmdk}")"
        VMDK_PATH="${IMAGE_DIR}/${VMDK_NAME}"
        cp "${extracted_vmdk}" "${VMDK_PATH}"
        echo "Uploading extracted VMDK: ${VMDK_URI}"
        aws s3 cp "${VMDK_PATH}" "${VMDK_URI}" \
            --metadata "vmdk-name=${VMDK_NAME}"
    fi
fi

image_version="$(basename "${VMDK_NAME}" .vmdk | \
    sed -n 's/^arubaoscx-disk-image-genericx86-p4-//p')"
[[ -n "${image_version}" ]] || die "could not derive vrnetlab version from ${VMDK_NAME}"

echo "Building vrnetlab/aruba_arubaos-cx:${image_version}..."
(cd "${IMAGE_DIR}" && sudo make docker-image)

IMAGE_NAME="vrnetlab/aruba_arubaos-cx:${image_version}"
docker image inspect "${IMAGE_NAME}" >/dev/null || \
    die "expected Docker image was not produced: ${IMAGE_NAME}"
docker tag "${IMAGE_NAME}" "vrnetlab/vr-aoscx:${RELEASE}"

TARBALL_NAME="aoscx-${RELEASE}.tar.gz"
TARBALL_PATH="${WORK_DIR}/${TARBALL_NAME}"
echo "Saving ${IMAGE_NAME} as ${TARBALL_NAME}..."
docker save "${IMAGE_NAME}" "vrnetlab/vr-aoscx:${RELEASE}" |
    gzip > "${TARBALL_PATH}"
aws s3 cp "${TARBALL_PATH}" \
    "s3://${BUCKET_NAME}/docker-images/${TARBALL_NAME}"

echo "Built image: ${IMAGE_NAME}"
echo "Containerlab alias: vrnetlab/vr-aoscx:${RELEASE}"
echo "S3 cache: s3://${BUCKET_NAME}/docker-images/${TARBALL_NAME}"
