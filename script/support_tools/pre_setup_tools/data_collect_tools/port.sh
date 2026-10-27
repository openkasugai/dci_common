#!/bin/bash

PROFILE="admin"

echo "server,interface,mac,nic_type,switch,port" >> result.csv

maas $PROFILE machines read | jq -r '
.[] |
select(.status_name != "Deployed") |
.system_id + " " + .hostname
' | while read -r SYS HOST; do

    IP=$(maas $PROFILE machine read "$SYS" | jq -r '.ip_addresses[0]')

    TARGET="$IP"
    if [ -z "$TARGET" ] || [ "$TARGET" = "null" ]; then
        TARGET="$HOST"
    fi

    ssh-keygen -R "$TARGET" >/dev/null 2>&1
    
    ssh -n \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=5 \
        -o BatchMode=yes \
        ubuntu@$TARGET "

HOST=\$(hostname)

LLDP_ALL=\$(lldpctl -f keyvalue 2>/dev/null)

for IF_PATH in /sys/class/net/*; do
    IF=\$(basename \"\$IF_PATH\")

    case \"\$IF\" in
        lo|docker*|lxd*|br*) continue ;;
    esac

    STATE=\$(cat /sys/class/net/\$IF/operstate 2>/dev/null)
    [ \"\$STATE\" != \"up\" ] && continue

    MAC=\$(cat /sys/class/net/\$IF/address 2>/dev/null)

    BUS=\$(ethtool -i \"\$IF\" 2>/dev/null | awk '/bus-info/ {print \$2}' | sed 's/^0000://')

    NIC=\$(lspci -nn 2>/dev/null | grep -i \"\$BUS\")

    if [ -n \"\$NIC\" ]; then
        # ★ここが修正ポイント（メーカー削除）
        NIC=\$(echo \"\$NIC\" \
          | sed -E 's/^.*: (Intel Corporation|Mellanox Technologies) //' \
          | sed -E 's/\\[[0-9a-f]{4}:[0-9a-f]{4}\\]//' \
          | xargs)
        NIC=\$(echo \"\$NIC\" | sed -E 's/^MT[0-9]+ Family \[(.*)\]$/\1/')
        NIC=\$(echo \"\$NIC\" \
          | sed -E 's/^ConnectX-5$/NVIDIA-CONNECTX-5/' \
          | sed -E 's/^ConnectX-6 Lx$/NVIDIA-CONNECTX-6-LX/' \
          | sed -E 's/^ConnectX-6 Dx$/NVIDIA-CONNECTX-6-DX/' \
          | sed -E 's/^ConnectX-7$/NVIDIA-CONNECTX-7/')
    else
        NIC=\$(ethtool -i \"\$IF\" 2>/dev/null | awk '/driver/ {print \$2}')
    fi

    [ -z \"\$NIC\" ] && NIC=\"unknown\"

    SWITCH=\$(echo \"\$LLDP_ALL\" | awk -F= -v IF=\"\$IF\" '
        \$1==\"lldp.\"IF\".chassis.name\" {print \$2}
    ')

    PORT=\$(echo \"\$LLDP_ALL\" | awk -F= -v IF=\"\$IF\" '
        \$1==\"lldp.\"IF\".port.descr\" {print \$2; exit}
        \$1==\"lldp.\"IF\".port.ifname\" {print \$2; exit}
    ' | head -n1)

    [ -z \"\$SWITCH\" ] && SWITCH=\"NONE\"
    [ -z \"\$PORT\" ] && PORT=\"NONE\"

    echo \"\$HOST,\$IF,\$MAC,\$NIC,\$SWITCH,\$PORT\"

done
" >> result.csv

done

echo "" >> result.csv
