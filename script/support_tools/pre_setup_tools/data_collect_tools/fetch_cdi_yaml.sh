#!/bin/bash

set -e

HOST="$1"
USER="$2"
PASS="$3"

TMP_FILE=$(mktemp)

# リモートファイル取得
sshpass -p "$PASS" scp -o StrictHostKeyChecking=no \
    ${USER}@${HOST}:/tmp/cdi.yaml \
    "$TMP_FILE"

# pcie_box配下に追加
sed 's/^/  /' "$TMP_FILE" >> cdi.yaml

rm -f "$TMP_FILE"
