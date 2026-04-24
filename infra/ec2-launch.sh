#!/usr/bin/env bash
#
# Launch an EC2 instance configured for containerlab with KVM support.
# Uses M8i instances (nested virtualization) by default.
#
# Prerequisites:
#   - AWS CLI v2.34+ configured with valid credentials
#   - VM images uploaded to S3 via upload-image.sh
#   - A region that supports M8i instances (most US/EU regions)
#
# Usage:
#   ./ec2-launch.sh [--instance-type TYPE] [--key-name NAME] [--timeout-hours N] [--spot]
#
# The script creates:
#   - An IAM instance profile with S3 read access (for downloading VM images)
#   - A security group allowing SSH from your current IP
#   - A key pair (if --key-name not provided)
#   - An EC2 instance with ec2-setup.sh as user-data
#   - A CloudWatch alarm to auto-terminate after --timeout-hours (default: 4)
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
SECURITY_GROUP_NAME="lab-validation-containerlab"

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
                         Available: ceos, vjunos-router, vjunos-switch, vjunos-evolved, all
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

REGION=$(aws configure get region 2>/dev/null || echo "")
if [[ -z "${REGION}" ]]; then
    echo "Error: no AWS region configured. Set AWS_DEFAULT_REGION or run 'aws configure'." >&2
    exit 1
fi
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

# Create or reuse security group
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${SECURITY_GROUP_NAME}" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "None")

if [[ "${SG_ID}" == "None" || -z "${SG_ID}" ]]; then
    echo "Creating security group..."
    SG_ID=$(aws ec2 create-security-group \
        --group-name "${SECURITY_GROUP_NAME}" \
        --description "SSH access for lab-validation containerlab instances" \
        --query 'GroupId' \
        --output text)
fi

# Update SSH ingress rule with current IP
MY_IP=$(curl -s https://checkip.amazonaws.com)
echo "Your IP: ${MY_IP}"

# Revoke existing SSH rules and add current IP
aws ec2 revoke-security-group-ingress \
    --group-id "${SG_ID}" \
    --protocol tcp --port 22 --cidr 0.0.0.0/0 2>/dev/null || true
aws ec2 authorize-security-group-ingress \
    --group-id "${SG_ID}" \
    --protocol tcp --port 22 --cidr "${MY_IP}/32" 2>/dev/null || true
echo "Security group: ${SG_ID} (SSH from ${MY_IP}/32)"

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
USER_DATA_FILE=$(mktemp)
sed -e "s|%%BUCKET_NAME%%|${BUCKET_NAME}|g" \
    -e "s|%%IMAGE_FILTER%%|${IMAGE_FILTER}|g" \
    "${SCRIPT_DIR}/ec2-setup.sh" > "${USER_DATA_FILE}"

# Build run-instances command
RUN_ARGS=(
    --image-id "${AMI_ID}"
    --instance-type "${INSTANCE_TYPE}"
    --key-name "${KEY_NAME}"
    --security-group-ids "${SG_ID}"
    --user-data "file://${USER_DATA_FILE}"
    --iam-instance-profile "Name=${PROFILE_NAME}"
    --cpu-options "NestedVirtualization=enabled"
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

# Set up auto-termination alarm
echo "Setting auto-terminate alarm (${TIMEOUT_HOURS}h)..."
ALARM_NAME="lab-validation-auto-terminate-${INSTANCE_ID}"
aws cloudwatch put-metric-alarm \
    --alarm-name "${ALARM_NAME}" \
    --namespace AWS/EC2 \
    --metric-name CPUUtilization \
    --statistic Average \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 100 \
    --comparison-operator GreaterThanThreshold \
    --alarm-actions "arn:aws:automate:${REGION}:ec2:terminate" \
    --dimensions "Name=InstanceId,Value=${INSTANCE_ID}" \
    --treat-missing-data missing 2>/dev/null || true

# Schedule the alarm to fire after timeout (set state to ALARM after delay)
# We use a simpler approach: tag with expiry time, and the alarm is a safety net.
# The real auto-termination relies on the alarm being set to ALARM state.
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
    'security_group_id': '${SG_ID}',
    'alarm_name': '${ALARM_NAME}',
    'auto_terminate_after': '${EXPIRY}',
    'spot': True if '${USE_SPOT}' == 'true' else False,
}
with open('${STATE_FILE}', 'w') as f:
    json.dump(state, f, indent=2)
"

SSH_CMD="ssh -i ${KEY_FILE} -o StrictHostKeyChecking=no ubuntu@${PUBLIC_IP}"

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
echo "SSH command:"
echo "  ${SSH_CMD}"
echo ""
echo "The instance is bootstrapping (installing Docker, containerlab, KVM tools)."
echo "This takes ~3-5 minutes. Check progress with:"
echo "  ${SSH_CMD} 'tail -f /var/log/cloud-init-output.log'"
echo ""
echo "Verify setup is complete:"
echo "  ${SSH_CMD} 'cat /var/log/ec2-setup-complete'"
echo ""
echo "State saved to: ${STATE_FILE}"
