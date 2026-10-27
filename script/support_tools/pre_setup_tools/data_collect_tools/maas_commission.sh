#!/bin/bash

PROFILE="admin"
INPUT_FILE="nodes.csv"
MAX_PARALLEL=10

# MAAS login
if ! maas list 2>/dev/null | grep -q "^${PROFILE} "; then
  echo "MAAS login..."

  API_KEY=$(sudo /snap/bin/maas apikey --username "$PROFILE" 2>/dev/null)

  if [ -z "$API_KEY" ]; then
    echo "ERROR: Failed to get MAAS API key."
    exit 1
  fi

  maas login "$PROFILE" http://localhost:5240/MAAS/ "$API_KEY"
fi

run_node() {
  HOSTNAME="$1"
  MAC="$2"
  IPMI_ADDR="$3"
  IPMI_USER="$4"
  IPMI_PASS="$5"

  LOG="log_${HOSTNAME}.log"

  {
    echo "=== Processing: $HOSTNAME ==="

    SYSTEM_ID=$(maas $PROFILE machines read \
      | jq -r ".[] | select(.hostname==\"$HOSTNAME\") | .system_id")

    if [ -z "$SYSTEM_ID" ]; then
      echo "Registering..."

      maas $PROFILE machines create \
        architecture="amd64/generic" \
        mac_addresses="$MAC" \
        hostname="$HOSTNAME" \
        power_type="ipmi" \
        power_parameters_power_address="$IPMI_ADDR" \
        power_parameters_power_user="$IPMI_USER" \
        power_parameters_power_pass="$IPMI_PASS"
    fi

    SYSTEM_ID=$(maas $PROFILE machines read \
      | jq -r ".[] | select(.hostname==\"$HOSTNAME\") | .system_id")

    echo "Commissioning ($SYSTEM_ID)..."

    maas $PROFILE machine commission $SYSTEM_ID \
      enable_ssh=true

    while true; do
      STATUS=$(maas $PROFILE machine read $SYSTEM_ID | jq -r '.status_name')
      echo "Status: $STATUS"

      if [[ "$STATUS" == "Ready" || "$STATUS" == "Failed commissioning" ]]; then
        break
      fi
      sleep 20
    done

    echo "Re-commission for SSH..."

    maas $PROFILE machine commission $SYSTEM_ID \
      enable_ssh=true

    while true; do
      STATUS=$(maas $PROFILE machine read $SYSTEM_ID | jq -r '.status_name')
      echo "Status: $STATUS"

      if [[ "$STATUS" == "Ready" || "$STATUS" == "Failed commissioning" ]]; then
        break
      fi
      sleep 20
    done

    echo "=== Done: $HOSTNAME ==="

  } > "$LOG" 2>&1
}

export -f run_node
export PROFILE

# ★ここがポイント（パイプ使わない）
while IFS=',' read -r HOSTNAME MAC IPMI_ADDR IPMI_USER IPMI_PASS SERVER_TYPE SERVER_ROLE DEPLOYMENT_TYPE
do
  # ヘッダスキップ
  if [ "$HOSTNAME" == "HOSTNAME" ]; then
    continue
  fi
  
  run_node "$HOSTNAME" "$MAC" "$IPMI_ADDR" "$IPMI_USER" "$IPMI_PASS" &

  while [ "$(jobs -r | wc -l)" -ge "$MAX_PARALLEL" ]; do
    sleep 2
  done

done < "$INPUT_FILE"

wait

echo "All nodes processed."
