#!/usr/bin/env bash
#
# Build the vrnetlab SONiC VS image and cache it in S3.
#
# Usage on EC2:
#   ./build-sonic-image.sh [branch]
#
# Downloads target/sonic-vs.img.gz for the given SONiC release branch
# (default: 202605) from the public SONiC build pipeline, builds
# vrnetlab/sonic_sonic-vs:<branch>, and uploads it to
# s3://BUCKET/docker-images/sonic-<branch>.tar.gz.
#
# The vrnetlab wrapper applies the containerlab startup-config with
# "config replace", which stalls on SONiC 202605 and does not restart bgpd
# after a DEVICE_METADATA bgp_asn change. The build patches it to use
# "config reload -f" (the restore runs before SONiC reports the system as
# ready) and then restart the bgp service, whose bgpd otherwise keeps the
# default config_db's ASN and neighbors.

set -euo pipefail

BRANCH="${1:-202605}"
VRNETLAB_ROOT="${VRNETLAB_ROOT:-/home/ubuntu/vrnetlab}"
IMAGE_DIR="${VRNETLAB_ROOT}/sonic"
ARTIFACT_URL="https://sonic-build.azurewebsites.net/api/sonic/artifacts?branchName=${BRANCH}&platform=vs&target=target/sonic-vs.img.gz"

die() {
    echo "Error: $*" >&2
    exit 1
}

need_command() {
    command -v "$1" >/dev/null || die "missing required command: $1"
}

need_command aws
need_command curl
need_command docker
need_command git

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET_NAME="${LAB_VALIDATION_BUCKET:-lab-validation-images-${ACCOUNT_ID}}"
WORK_DIR="${HOME}/.cache/sonic"
mkdir -p "${WORK_DIR}"

if [[ ! -d "${VRNETLAB_ROOT}/.git" ]]; then
    echo "Cloning vrnetlab..."
    git clone --depth 1 https://github.com/hellt/vrnetlab.git "${VRNETLAB_ROOT}"
fi

GZ_PATH="${WORK_DIR}/sonic-vs-${BRANCH}.img.gz"
if [[ ! -f "${GZ_PATH}" ]]; then
    echo "Downloading SONiC ${BRANCH} VS image..."
    curl -fSL -o "${GZ_PATH}.partial" "${ARTIFACT_URL}"
    mv "${GZ_PATH}.partial" "${GZ_PATH}"
fi
gzip -t "${GZ_PATH}" || die "corrupt download: ${GZ_PATH}"

QCOW2_PATH="${IMAGE_DIR}/sonic-vs-${BRANCH}.qcow2"
echo "Extracting ${QCOW2_PATH}..."
gunzip -c "${GZ_PATH}" > "${QCOW2_PATH}"

BACKUP_SH="${IMAGE_DIR}/docker/backup.sh"
grep -q 'sudo config replace \$TMP_FILE' "${BACKUP_SH}" || \
    die "vrnetlab backup.sh no longer uses 'config replace'; review the patch"
RESTORE_CMD="sudo config reload -y -f \\\$TMP_FILE \&\& sudo config save -y \&\& sudo timeout 600 sh -c 'until systemctl is-active -q bgp; do sleep 5; done' \&\& sudo systemctl restart bgp"
sed -i "s|sudo config replace \\\$TMP_FILE \&\& sudo config save -y|${RESTORE_CMD}|" \
    "${BACKUP_SH}"

IMAGE_NAME="vrnetlab/sonic_sonic-vs:${BRANCH}"
echo "Building ${IMAGE_NAME}..."
build_status=0
(cd "${IMAGE_DIR}" && make IMAGE="sonic-vs-${BRANCH}.qcow2" docker-image) || build_status=$?
git -C "${VRNETLAB_ROOT}" checkout -- sonic/docker/backup.sh
rm -f "${QCOW2_PATH}"
[[ "${build_status}" -eq 0 ]] || die "vrnetlab build failed"

docker image inspect "${IMAGE_NAME}" >/dev/null || \
    die "expected Docker image was not produced: ${IMAGE_NAME}"

TARBALL_NAME="sonic-${BRANCH}.tar.gz"
echo "Saving ${IMAGE_NAME} to s3://${BUCKET_NAME}/docker-images/${TARBALL_NAME}..."
docker save "${IMAGE_NAME}" | gzip | \
    aws s3 cp - "s3://${BUCKET_NAME}/docker-images/${TARBALL_NAME}"

echo "Built image: ${IMAGE_NAME}"
echo "S3 cache: s3://${BUCKET_NAME}/docker-images/${TARBALL_NAME}"
