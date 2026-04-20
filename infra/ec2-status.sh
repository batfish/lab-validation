#!/usr/bin/env bash
#
# Check the status of lab-validation EC2 instances.
#
# Always queries EC2 by tag to find all lab-validation instances.
# Cross-references with the local state file and warns about mismatches.
#
# Usage:
#   ./ec2-status.sh                # Show all lab-validation instances
#   ./ec2-status.sh i-0abc123      # Check specific instance

set -euo pipefail

STATE_DIR="${HOME}/.lab-validation"
STATE_FILE="${STATE_DIR}/instance.json"

# If a specific instance ID was provided, just show that one
if [[ $# -ge 1 ]]; then
    INSTANCE_ID="$1"

    INFO=$(aws ec2 describe-instances \
        --instance-ids "${INSTANCE_ID}" \
        --query 'Reservations[0].Instances[0].{State:State.Name,IP:PublicIpAddress,Type:InstanceType,LaunchTime:LaunchTime}' \
        --output json 2>/dev/null || echo '{"State":"not-found"}')

    echo "${INFO}" | python3 -c "
import json, sys
i = json.load(sys.stdin)
print(f\"Instance:  ${INSTANCE_ID}\")
print(f\"State:     {i.get('State', 'unknown')}\")
print(f\"IP:        {i.get('IP') or 'none'}\")
print(f\"Type:      {i.get('Type') or 'unknown'}\")
print(f\"Launched:  {i.get('LaunchTime') or 'unknown'}\")
"
    exit 0
fi

# Query all lab-validation instances
INSTANCES=$(aws ec2 describe-instances \
    --filters \
        "Name=tag:Project,Values=lab-validation" \
        "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name,Type:InstanceType,IP:PublicIpAddress,LaunchTime:LaunchTime}' \
    --output json 2>/dev/null || echo "[]")

# Read state file if it exists
TRACKED_ID=""
KEY_FILE=""
EXPIRY=""
if [[ -f "${STATE_FILE}" ]]; then
    TRACKED_ID=$(python3 -c "import json; print(json.load(open('${STATE_FILE}'))['instance_id'])" 2>/dev/null || true)
    KEY_FILE=$(python3 -c "import json; print(json.load(open('${STATE_FILE}')).get('key_file', ''))" 2>/dev/null || true)
    EXPIRY=$(python3 -c "import json; print(json.load(open('${STATE_FILE}')).get('auto_terminate_after', ''))" 2>/dev/null || true)
fi

# Display instances and cross-reference with state file
python3 -c "
import json, sys

instances = json.loads('''${INSTANCES}''')
tracked_id = '${TRACKED_ID}'
key_file = '${KEY_FILE}'
expiry = '${EXPIRY}'

ec2_ids = {i['ID'] for i in instances}

if not instances and not tracked_id:
    print('No lab-validation instances found.')
    sys.exit(0)

# Show each EC2 instance
for i in instances:
    iid = i['ID']
    state = i['State']
    tracked = ' (tracked)' if iid == tracked_id else ''
    print(f'Instance:  {iid}{tracked}')
    print(f'State:     {state}')
    print(f'IP:        {i.get(\"IP\") or \"none\"}')
    print(f'Type:      {i.get(\"Type\") or \"unknown\"}')
    print(f'Launched:  {i.get(\"LaunchTime\") or \"unknown\"}')
    if iid == tracked_id and expiry:
        print(f'Auto-term: {expiry}')
    if state == 'running' and iid == tracked_id and key_file and i.get('IP'):
        print()
        print(f'SSH command:')
        print(f'  ssh -i {key_file} -o StrictHostKeyChecking=no ubuntu@{i[\"IP\"]}')
    print()

# Warn: tracked instance not found in EC2
if tracked_id and tracked_id not in ec2_ids:
    print(f'WARNING: state file tracks {tracked_id} but it was not found in EC2.')
    print(f'  It may have been terminated. Run ec2-teardown.sh to clean up the state file.')
    print()

# Warn: untracked instances found
untracked = [i for i in instances if i['ID'] != tracked_id]
if untracked:
    ids = ', '.join(i['ID'] for i in untracked)
    print(f'WARNING: {len(untracked)} instance(s) not tracked by state file: {ids}')
    print(f'  These may be orphaned. Terminate with: ec2-teardown.sh <instance-id>')
"
