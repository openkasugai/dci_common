#!/bin/bash

PROFILE="admin"
OUTFILE="result.csv"

echo "" >> "$OUTFILE"

echo "server,gpu_model" >> "$OUTFILE"

maas "$PROFILE" machines read | jq -r '
.[] |
select(.status_name != "Deployed") |
.system_id + " " + .hostname
' | while read -r SYS HOST; do

    IP=$(maas "$PROFILE" machine read "$SYS" | jq -r '.ip_addresses[0]')

    TARGET="$IP"
    if [ -z "$TARGET" ] || [ "$TARGET" = "null" ]; then
        TARGET="$HOST"
    fi

    GPU_IDS=$(
        ssh -n \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -o ConnectTimeout=5 \
            -o BatchMode=yes \
            "ubuntu@$TARGET" '
                lspci -nn 2>/dev/null |
                grep -i nvidia |
                while read -r line; do
                    PCI=$(echo "$line" |
                          grep -oE "\[[0-9a-f]{4}:[0-9a-f]{4}\]" |
                          tail -1 |
                          tr -d "[]")

                    [ -n "$PCI" ] && echo "$PCI"
                done
            ' 2>/dev/null
    )

    if [ -z "$GPU_IDS" ]; then
        echo "$HOST,NONE" >> "$OUTFILE"
        continue
    fi

    GPU_NAMES=""

    for PCI in $(echo "$GPU_IDS" | sort -u); do
        case "$PCI" in
            10de:2bb5)
                NAME="NVIDIA-BLACKWELL"
                ;;

            10de:2330|10de:2331)
                NAME="NVIDIA-H100-PCIE-80GB"
                ;;

            10de:2338|10de:2339)
                NAME="NVIDIA-H100-NVL-PCIE-94GB"
                ;;

            10de:20b5)
                NAME="NVIDIA-A100-PCIE-80GB"
                ;;

            10de:1eb8)
                NAME="NVIDIA-TESLA-T4-PCIE-16GB"
                ;;

            10de:20b8)
                NAME="NVIDIA-A100X-PCIE-80GB"
                ;;
            *)
                NAME="$PCI"
                ;;
        esac

        if [ -z "$GPU_NAMES" ]; then
            GPU_NAMES="$NAME"
        else
            GPU_NAMES="${GPU_NAMES};${NAME}"
        fi
    done

    echo "$HOST,$GPU_NAMES" >> "$OUTFILE"

done

echo "Output written to $OUTFILE"
