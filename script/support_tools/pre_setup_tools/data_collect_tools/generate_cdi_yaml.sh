#!/bin/bash

set -e

HOST="$1"
USER="$2"
PASS="$3"
CDI_USER="$4"
CDI_PASSWORD="$5"

# -----------------------------
# 1. リモートでYAML生成
# -----------------------------
sshpass -p "$PASS" ssh -tt -o StrictHostKeyChecking=no ${USER}@${HOST} << EOF
set -e

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

# install
echo "ubuntu" | sudo -S apt update -y >/dev/null 2>&1
echo "ubuntu" | sudo -S apt install -y expect jq >/dev/null 2>&1

if ! command -v yq >/dev/null; then
  sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
  sudo chmod +x /usr/local/bin/yq
fi

# JSON取得
expect << EOD | sed -n '/^{/,/^}/p' > /tmp/cdi.json
spawn cdictl -u \$URL auth login
expect "Enter username:"
send "$CDI_USER\r"

expect "Password for cdiadmin"
send "$CDI_PASSWORD\r"

expect "cdi:"
send "cdictl resource list -f 1 -o JSON\r"

expect "Success"

expect "cdi:"
send "exit\r"

expect eof
EOD

# YAML生成（★これをファイルに直接出す）
jq '
{
  nic: (
    .data.resources
    | map(select(.res_type == "nic"))
    | map({
        res_uuid: .res_uuid,
        res_name: .res_name,
        mac_address: (.mac_address // ""),
        nw_port_id: (.nw_port_id // 0),
        status: 0
      })
  ),
  gpu: (
    .data.resources
    | map(select(.res_type == "gpu"))
    | map({
        res_uuid: .res_uuid,
        res_name: .res_name,
        uuid: (.gpu_uuid // ""),
        status: 0
      })
  ),
  ssd: (
    .data.resources
    | map(select(.res_type == "storage"))
    | map({
        res_uuid: .res_uuid,
        res_name: .res_name,
        storage_gb: 960,
        status: 0
      })
  )
}
' /tmp/cdi.json | yq -P > /tmp/cdi.yaml

exit
EOF
