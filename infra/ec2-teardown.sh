#!/usr/bin/env bash
#
# Terminate the lab-validation EC2 instance and clean up associated resources.
#
# Usage:
#   ./ec2-teardown.sh              # Uses instance from ~/.lab-validation/instance.json
#   ./ec2-teardown.sh i-0abc123    # Terminate specific instance

set -euo pipefail

STATE_DIR="${HOME}/.lab-validation"
STATE_FILE="${STATE_DIR}/instance.json"

if [[ $# -ge 1 ]]; then
    INSTANCE_ID="$1"
else
    if [[ ! -f "${STATE_FILE}" ]]; then
        echo "Error: no instance state found at ${STATE_FILE}" >&2
        echo "Provide an instance ID as argument, or run ec2-launch.sh first." >&2
        exit 1
    fi
    INSTANCE_ID=$(python3 -c "import json; print(json.load(open('${STATE_FILE}'))['instance_id'])")
fi

echo "Terminating instance: ${INSTANCE_ID}"
aws ec2 terminate-instances --instance-ids "${INSTANCE_ID}" \
    --query 'TerminatingInstances[0].CurrentState.Name' --output text

# Remove state file
rm -f "${STATE_FILE}"
echo "Instance terminated. State file removed."
