#!/usr/bin/env bash
#
# Launch an EC2 instance configured for containerlab with KVM support.
# Uses M8i instances (nested virtualization) by default.
#
# Prerequisites:
#   - AWS CLI v2.34+ configured with valid credentials
#   - session-manager-plugin installed locally (to SSH over SSM)
#   - VM images uploaded to S3 via upload-image.sh
#   - A region that supports M8i instances (most US/EU regions)
#
# Usage:
#   ./ec2-launch.sh [--instance-type TYPE] [--key-name NAME] [--timeout-hours N] [--spot]
#
# The script creates:
#   - An IAM instance profile with S3 read access (for downloading VM images)
#     and the SSM managed policy (so the instance is reachable over Session
#     Manager — outbound 443 only, no inbound SSH and no security group)
#   - A key pair (if --key-name not provided)
#   - An EC2 instance with ec2-setup.sh as user-data
#   - Auto-termination via scheduled shutdown (InstanceInitiatedShutdownBehavior=terminate)
#
# Instance state is saved to ~/.lab-validation/instance.json for use by other scripts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${HOME}/.lab-validation"
STATE_FILE="${STATE_DIR}/instance.json"

# Defaults
INSTANCE_TYPE="m8i.2xlarge"
KEY_NAME=""
TIMEOUT_HOURS=4
USE_SPOT=false
IMAGE_FILTER="all"

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Launch an EC2 instance for containerlab with KVM support.

Options:
  --instance-type TYPE   EC2 instance type (default: m8i.2xlarge)
  --key-name NAME        Existing EC2 key pair name (auto-created if omitted)
  --timeout-hours N      Auto-terminate after N hours (default: 4)
  --spot                 Request a spot instance (~70% cheaper, may be interrupted)
  --images FILTER        Comma-separated list of images to load (default: all)
                         Available: ceos, vjunos-router, vjunos-switch, vjunos-evolved, nxos, srsim, all
  --help                 Show this help

Environment:
  AWS_DEFAULT_REGION     AWS region (or configured via 'aws configure')
  AWS_PROFILE            AWS CLI profile to use
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --instance-type) INSTANCE_TYPE="$2"; shift 2 ;;
        --key-name) KEY_NAME="$2"; shift 2 ;;
        --timeout-hours) TIMEOUT_HOURS="$2"; shift 2 ;;
        --spot) USE_SPOT=true; shift ;;
        --images) IMAGE_FILTER="$2"; shift 2 ;;
        --help) usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

mkdir -p "${STATE_DIR}"

# Check for existing instance
if [[ -f "${STATE_FILE}" ]]; then
    EXISTING_ID=$(python3 -c "import json; print(json.load(open('${STATE_FILE}'))['instance_id'])" 2>/dev/null || true)
    if [[ -n "${EXISTING_ID}" ]]; then
        EXISTING_STATE=$(aws ec2 describe-instances \
            --instance-ids "${EXISTING_ID}" \
            --query 'Reservations[0].Instances[0].State.Name' \
            --output text 2>/dev/null || echo "not-found")
        if [[ "${EXISTING_STATE}" == "running" || "${EXISTING_STATE}" == "pending" ]]; then
            echo "Error: instance ${EXISTING_ID} is already ${EXISTING_STATE}." >&2
            echo "Run ec2-teardown.sh first, or ec2-status.sh to check it." >&2
            exit 1
        fi
    fi
fi

# Resolve region from the environment first (the AWS CLI honors these but
# `aws configure get region` does not), then fall back to the configured
# profile default.
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(aws configure get region 2>/dev/null || echo "")}}"
if [[ -z "${REGION}" ]]; then
    echo "Error: no AWS region configured. Set AWS_DEFAULT_REGION or run 'aws configure'." >&2
    exit 1
fi
# Pin every subsequent `aws` call (and the SSM ProxyCommand we print) to it.
export AWS_DEFAULT_REGION="${REGION}"
echo "Region: ${REGION}"

# Derive S3 bucket name from account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="lab-validation-images-${ACCOUNT_ID}"

# Verify bucket exists and has images
if ! aws s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
    echo "Error: S3 bucket '${BUCKET_NAME}' not found." >&2
    echo "Run upload-image.sh first to upload your VM images." >&2
    exit 1
fi
echo "Image bucket: ${BUCKET_NAME}"

# Create IAM role and instance profile for S3 access (idempotent)
ROLE_NAME="lab-validation-ec2-role"
PROFILE_NAME="lab-validation-ec2-profile"

if ! aws iam get-role --role-name "${ROLE_NAME}" &>/dev/null; then
    echo "Creating IAM role: ${ROLE_NAME}"
    aws iam create-role \
        --role-name "${ROLE_NAME}" \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }' > /dev/null

    aws iam put-role-policy \
        --role-name "${ROLE_NAME}" \
        --policy-name "lab-validation-s3-read" \
        --policy-document "{
            \"Version\": \"2012-10-17\",
            \"Statement\": [{
                \"Effect\": \"Allow\",
                \"Action\": [\"s3:GetObject\", \"s3:ListBucket\", \"s3:PutObject\"],
                \"Resource\": [
                    \"arn:aws:s3:::${BUCKET_NAME}\",
                    \"arn:aws:s3:::${BUCKET_NAME}/*\"
                ]
            }]
        }"
fi

# Attach the SSM managed policy so the instance registers with Session Manager
# and is reachable over 443 (no inbound SSH). Idempotent — attaching an
# already-attached policy is a no-op. Done outside the create-role block so it
# is also applied to roles created before SSM became the default.
aws iam attach-role-policy \
    --role-name "${ROLE_NAME}" \
    --policy-arn "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore" >/dev/null

if ! aws iam get-instance-profile --instance-profile-name "${PROFILE_NAME}" &>/dev/null; then
    echo "Creating instance profile: ${PROFILE_NAME}"
    aws iam create-instance-profile --instance-profile-name "${PROFILE_NAME}" > /dev/null
    aws iam add-role-to-instance-profile \
        --instance-profile-name "${PROFILE_NAME}" \
        --role-name "${ROLE_NAME}"
    # IAM propagation delay
    echo "Waiting for IAM profile to propagate..."
    sleep 10
fi

# Find Ubuntu 24.04 LTS AMI
echo "Looking up Ubuntu 24.04 LTS AMI..."
AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters \
        "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" \
        "Name=state,Values=available" \
    --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
    --output text)

if [[ -z "${AMI_ID}" || "${AMI_ID}" == "None" ]]; then
    echo "Error: could not find Ubuntu 24.04 AMI in ${REGION}." >&2
    exit 1
fi
echo "AMI: ${AMI_ID}"

# No security group is created: the instance is reached over AWS Systems
# Manager (Session Manager), which the SSM agent dials out to over 443. There
# is no inbound SSH, so the instance keeps the VPC default security group.

# Create key pair if needed
KEY_FILE=""
if [[ -z "${KEY_NAME}" ]]; then
    KEY_NAME="lab-validation-$(date +%Y%m%d)"
    KEY_FILE="${STATE_DIR}/${KEY_NAME}.pem"
    if [[ ! -f "${KEY_FILE}" ]]; then
        # Delete stale key pair with same name if it exists
        aws ec2 delete-key-pair --key-name "${KEY_NAME}" 2>/dev/null || true
        echo "Creating key pair: ${KEY_NAME}"
        aws ec2 create-key-pair \
            --key-name "${KEY_NAME}" \
            --query 'KeyMaterial' \
            --output text > "${KEY_FILE}"
        chmod 600 "${KEY_FILE}"
    else
        echo "Reusing key file: ${KEY_FILE}"
    fi
else
    # User provided key name; check common locations for the .pem
    for candidate in "${STATE_DIR}/${KEY_NAME}.pem" "${HOME}/.ssh/${KEY_NAME}.pem" "${HOME}/.ssh/${KEY_NAME}"; do
        if [[ -f "${candidate}" ]]; then
            KEY_FILE="${candidate}"
            break
        fi
    done
    if [[ -z "${KEY_FILE}" ]]; then
        echo "Warning: could not find .pem file for key '${KEY_NAME}'." >&2
        echo "You'll need to specify the key file manually when SSHing." >&2
    fi
fi

# Generate user-data script with parameters baked in
TIMEOUT_MINUTES=$((TIMEOUT_HOURS * 60))
USER_DATA_FILE=$(mktemp)
sed -e "s|%%BUCKET_NAME%%|${BUCKET_NAME}|g" \
    -e "s|%%IMAGE_FILTER%%|${IMAGE_FILTER}|g" \
    -e "s|%%TIMEOUT_MINUTES%%|${TIMEOUT_MINUTES}|g" \
    "${SCRIPT_DIR}/ec2-setup.sh" > "${USER_DATA_FILE}"

# Build run-instances command
RUN_ARGS=(
    --image-id "${AMI_ID}"
    --instance-type "${INSTANCE_TYPE}"
    --key-name "${KEY_NAME}"
    --user-data "file://${USER_DATA_FILE}"
    --iam-instance-profile "Name=${PROFILE_NAME}"
    --cpu-options "NestedVirtualization=enabled"
    --instance-initiated-shutdown-behavior terminate
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":50,"VolumeType":"gp3"}}]'
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=lab-validation-containerlab},{Key=Project,Value=lab-validation}]"
    --query 'Instances[0].InstanceId'
    --output text
)

if [[ "${USE_SPOT}" == "true" ]]; then
    RUN_ARGS+=(--instance-market-options '{"MarketType":"spot","SpotOptions":{"SpotInstanceType":"one-time"}}')
    echo "Requesting spot instance..."
else
    echo "Launching on-demand instance..."
fi

INSTANCE_ID=$(aws ec2 run-instances "${RUN_ARGS[@]}")
rm -f "${USER_DATA_FILE}"
echo "Instance: ${INSTANCE_ID}"

# Wait for instance to be running
echo "Waiting for instance to enter 'running' state..."
aws ec2 wait instance-running --instance-ids "${INSTANCE_ID}"

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "${INSTANCE_ID}" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)
echo "Public IP: ${PUBLIC_IP}"

# Auto-termination is handled by `shutdown` scheduled in ec2-setup.sh.
# The instance has InstanceInitiatedShutdownBehavior=terminate, so
# shutdown will terminate it (and delete the EBS volume).
EXPIRY=$(date -u -v+${TIMEOUT_HOURS}H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || \
         date -u -d "+${TIMEOUT_HOURS} hours" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || \
         echo "unknown")
aws ec2 create-tags --resources "${INSTANCE_ID}" \
    --tags "Key=AutoTerminateAfter,Value=${EXPIRY}" 2>/dev/null || true

# Save state
python3 -c "
import json
state = {
    'instance_id': '${INSTANCE_ID}',
    'public_ip': '${PUBLIC_IP}',
    'region': '${REGION}',
    'instance_type': '${INSTANCE_TYPE}',
    'key_name': '${KEY_NAME}',
    'key_file': '${KEY_FILE}',
    'auto_terminate_after': '${EXPIRY}',
    'spot': True if '${USE_SPOT}' == 'true' else False,
}
with open('${STATE_FILE}', 'w') as f:
    json.dump(state, f, indent=2)
"

# The instance is reached over SSM Session Manager (no inbound SSH). SSH
# tunnels through an SSM ProxyCommand keyed on the instance-id; scp and the
# netmiko-based lab_builder steps then work unchanged. Add a one-off host to
# ~/.ssh/config so plain `ssh lab` / `scp ... lab:` work:
SSM_PROXY="sh -c \"aws ssm start-session --target %h --document-name AWS-StartSSHSession --parameters portNumber=%p --region ${REGION}\""

echo ""
echo "============================================"
echo "Instance launched successfully!"
echo "============================================"
echo "Instance ID:  ${INSTANCE_ID}"
echo "Public IP:    ${PUBLIC_IP}"
echo "Instance type: ${INSTANCE_TYPE}"
echo "Images:       ${IMAGE_FILTER}"
echo "Auto-terminate: ${EXPIRY}"
echo ""
echo "Connect via SSM Session Manager (requires the session-manager-plugin)."
echo "Add this block to ~/.ssh/config, then use 'ssh lab' / 'scp ... lab:':"
echo ""
echo "  Host lab"
echo "      HostName ${INSTANCE_ID}"
echo "      User ubuntu"
echo "      IdentityFile ${KEY_FILE}"
echo "      StrictHostKeyChecking no"
echo "      UserKnownHostsFile /dev/null"
echo "      ProxyCommand ${SSM_PROXY}"
echo ""
echo "The SSM agent registers ~30-60s after the instance is running; the"
echo "instance then bootstraps (~3-5 min). Check progress with:"
echo "  ssh lab 'tail -f /var/log/cloud-init-output.log'"
echo ""
echo "Verify setup is complete:"
echo "  ssh lab 'cat /var/log/ec2-setup-complete'"
echo ""
echo "State saved to: ${STATE_FILE}"
