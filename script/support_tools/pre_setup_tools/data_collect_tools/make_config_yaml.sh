#!/bin/bash
set -u
set -o pipefail

INPUT="result.csv"
NODES="nodes.csv"
SWITCH_CSV="switch.csv"

#####################################
# データ
#####################################

declare -A CPU MEM DISK VENDOR PRODUCT
declare -A HOST CNI APP APP_NIC_MODEL
declare -A IPMI_ADDR IPMI_USER IPMI_PASS NODE_MAC
declare -A NODE_TYPE SERVER_ROLE DEPLOYMENT_TYPE
declare -A GPU_MODEL

declare -a SWITCH_LIST
declare -A SW_LOC SW_IP SW_USER SW_VENDOR SW_PRODUCT SW_OS
declare -a SW_RULES

declare -A SWITCH_ID_MAP
declare -A PORT_ID_MAP MAC_TO_PORTID
declare -A SWITCH_PORTS

NIC_LINES=()

#####################################
# 関数
#####################################

get_port_num() {
    local s="$1"

    if [[ "$s" =~ Port([0-9]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    elif [[ "$s" =~ Ethernet([0-9]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    elif [[ "$s" =~ Eth([0-9]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        echo ""
    fi
}

#####################################
# ① server
#####################################

while IFS=',' read -r SERVER VENDOR_ PRODUCT_ CPU_ MEM_ DISK_; do
  [[ "$SERVER" == "server" ]] && continue
  [[ -z "${DISK_:-}" ]] && break

  CPU["$SERVER"]="$CPU_"
  MEM["$SERVER"]="$MEM_"
  DISK["$SERVER"]="$DISK_"
  VENDOR["$SERVER"]="$VENDOR_"
  PRODUCT["$SERVER"]="$PRODUCT_"

done < <(awk '/^server,vendor/{f=1;next}/^$/{f=0}f' "$INPUT")

#####################################
# ② GPU
#####################################

while IFS=',' read -r SERVER GPU; do
  [[ "$SERVER" == "server" ]] && continue
  [[ -z "${GPU:-}" ]] && continue

  GPU_MODEL["$SERVER"]="$GPU"

done < <(awk '/^server,gpu_model/{f=1;next}f' "$INPUT")

#####################################
# ③ nodes
#####################################

while IFS=',' read -r HOSTNAME MAC IP USER PASS TYPE ROLE DEPLOY; do
  [[ "$HOSTNAME" == "HOSTNAME" ]] && continue
  [[ -z "${HOSTNAME:-}" ]] && continue

  NODE_MAC["$HOSTNAME"]="$MAC"
  IPMI_ADDR["$HOSTNAME"]="$IP"
  IPMI_USER["$HOSTNAME"]="$USER"
  IPMI_PASS["$HOSTNAME"]="$PASS"

  NODE_TYPE["$HOSTNAME"]="$TYPE"
  SERVER_ROLE["$HOSTNAME"]="$ROLE"
  DEPLOYMENT_TYPE["$HOSTNAME"]="$DEPLOY"

done < "$NODES"

#####################################
# ④ switch.csv
#####################################

MODE="SWITCH"

while IFS=',' read -r C1 C2 C3 C4 C5 C6 C7 C8 C9 C10; do

  [[ "$C1" == "NW_SWITCH_NAME" ]] && continue
  [[ -z "${C1:-}" ]] && continue

  NAME="$C1"
  SWITCH_LIST+=("$NAME")

  SW_LOC["$NAME"]="$C2"
  SW_IP["$NAME"]="$C3"
  SW_USER["$NAME"]="$C4"
  SW_VENDOR["$NAME"]="$C5"
  SW_PRODUCT["$NAME"]="$C6"
  SW_OS["$NAME"]="$C7"

  S=$(get_port_num "$C8")
  E=$(get_port_num "$C9")
  TYPE="$C10"

  SW_RULES+=("$NAME,$S,$E,$TYPE")

done < "$SWITCH_CSV"

#####################################
# ⑤ NIC解析
#####################################

while IFS=',' read -r SERVER IF MAC NIC SWITCH PORT; do
  [[ "$SERVER" == "server" ]] && continue

  PNUM=$(get_port_num "$PORT")
  ROLE=""

  for RULE in "${SW_RULES[@]}"; do
    IFS=',' read -r NAME S E TYPE <<< "$RULE"

    if [[ "$SWITCH" == "$NAME" && "$PNUM" -ge "$S" && "$PNUM" -le "$E" ]]; then
      ROLE="$TYPE"
      break
    fi
  done

  [[ -z "$ROLE" ]] && continue

  NIC_LINES+=("$SERVER,$MAC,$NIC,$SWITCH,$PORT,$ROLE")

  SWITCH_PORTS["$SWITCH"]+="$PORT "

  case "$ROLE" in
    app)
      APP["$SERVER"]="$MAC"
      APP_NIC_MODEL["$SERVER"]="$NIC"
      ;;
    cni)
      CNI["$SERVER"]="$MAC"
      ;;
    host)
      HOST["$SERVER"]="$MAC"
      ;;
  esac

done < <(awk '/^server,interface/{f=1;next}/^$/{f=0}f' "$INPUT")

#####################################
# location生成
#####################################

declare -A LOCATION_MAP

for SW in "${SWITCH_LIST[@]}"; do
    LOC="${SW_LOC[$SW]}"
    LOCATION_MAP["$LOC"]=1
done

echo "location:"

for LOC in $(printf '%s\n' "${!LOCATION_MAP[@]}" | sort); do
  echo "  - $LOC"
done

echo ""


#####################################
# ⑥ SW ID
#####################################

i=1
for SW in "${SWITCH_LIST[@]}"; do
  SWITCH_ID_MAP["$SW"]="sw$i"
  ((i++))
done

#####################################
# ⑦ nw_switch
#####################################

echo "nw_switch:"
for SW in "${SWITCH_LIST[@]}"; do
  echo "  - nw_switch_name: \"$SW\""
  echo "    location: \"${SW_LOC[$SW]}\""
  echo "    nw_ip_address: \"${SW_IP[$SW]}\""
  echo "    nw_user: \"${SW_USER[$SW]}\""
  echo "    status: 0"
  echo "    product_info:"
  echo "      vendor: \"${SW_VENDOR[$SW]}\""
  echo "      product_name: \"${SW_PRODUCT[$SW]}\""
  echo "      os: \"${SW_OS[$SW]}\""
  echo "      version: \"\""
done

#####################################
# ⑧ nw_port（安定）
#####################################

echo ""
echo "nw_port:"

PORT_ID=1

for SW in "${SWITCH_LIST[@]}"; do
  PORTS=$(echo "${SWITCH_PORTS[$SW]:-}" | tr ' ' '\n' | sort -u | sort -V)

  for PORT in $PORTS; do
    KEY="${SW}_${PORT}"
    PORT_ID_MAP["$KEY"]=$PORT_ID

    echo "  - nw_switch_id: \"${SWITCH_ID_MAP[$SW]}.NwSwitchID\""
    echo "    interface_name: $PORT"

    ((PORT_ID++))
  done
done

#####################################
# ⑨ MAC→port
#####################################

for LINE in "${NIC_LINES[@]}"; do
  IFS=',' read -r S M N SW P R <<< "$LINE"
  MAC_TO_PORTID["$M"]="${PORT_ID_MAP[${SW}_${P}]:-}"
done

#####################################
# ⑩ MAAS
#####################################

# API KEY
API_KEY=$(sudo /snap/bin/maas apikey --username admin 2>/dev/null || true)

# API IP
IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')

ACCESS_URL="http://${IP}:5240/MAAS/api/2.0/"

# VERSION固定
VERSION="3.6"

# フォールバック
API_KEY="${API_KEY:-""}"
ACCESS_URL="${ACCESS_URL:-""}"

echo ""
echo "maas:"
echo "  access_url: \"$ACCESS_URL\""
echo "  api_key: \"$API_KEY\""
echo "  status: 0"
echo "  product_info:"
echo "    vendor: \"canonical\""
echo "    product_name: \"MAAS\""
echo "    version: \"$VERSION\""

#####################################
# ⑪ COTS
#####################################

echo ""
echo "cots:"

for SERVER in "${!CPU[@]}"; do
  [[ "${NODE_TYPE[$SERVER]:-}" != "COTS" ]] && continue

  H="${HOST[$SERVER]:-}"
  C="${CNI[$SERVER]:-}"
  A="${APP[$SERVER]:-}"

  echo "  - host_name: $SERVER"
  echo "    ipmi_address: \"${IPMI_ADDR[$SERVER]:-}\""
  echo "    ipmi_user: \"${IPMI_USER[$SERVER]:-}\""
  echo "    ipmi_password: \"${IPMI_PASS[$SERVER]:-}\""
  echo "    server_role: ${SERVER_ROLE[$SERVER]:-}"
  echo "    deployment_type: ${DEPLOYMENT_TYPE[$SERVER]:-}"
  echo "    mgr_mac: \"${NODE_MAC[$SERVER]:-}\""

  echo "    host_mac: \"$H\""
  echo "    host_nw_port_id: ${MAC_TO_PORTID[$H]:-}"
  echo "    cni_mac: \"$C\""
  echo "    cni_nw_port_id: ${MAC_TO_PORTID[$C]:-}"

  if [[ -n "$A" ]]; then
    echo "    apldata:"
    echo "      mac: \"$A\""
    echo "      nw_port_id: ${MAC_TO_PORTID[$A]:-}"
    echo "      nic_model: \"${APP_NIC_MODEL[$SERVER]}\""
  fi

  echo "    cpu_cores: ${CPU[$SERVER]}"
  echo "    memory_mb: ${MEM[$SERVER]}"
  echo "    storage_gb: ${DISK[$SERVER]}"
  echo "    status: 0"
  echo "    product_info:"
  echo "      vendor: \"${VENDOR[$SERVER]}\""
  echo "      product_name: \"${PRODUCT[$SERVER]}\""
  echo "      version: \"\""
done

#####################################
# ⑫ COMPUTE
#####################################

echo ""
echo "compute_pool:"

for SERVER in "${!CPU[@]}"; do
  [[ "${NODE_TYPE[$SERVER]:-}" != "COMPUTE" ]] && continue

  H="${HOST[$SERVER]:-}"
  C="${CNI[$SERVER]:-}"
  A="${APP[$SERVER]:-}"

  echo "  - host_name: $SERVER"
  echo "    ipmi_address: \"${IPMI_ADDR[$SERVER]:-}\""
  echo "    ipmi_user: \"${IPMI_USER[$SERVER]:-}\""
  echo "    ipmi_password: \"${IPMI_PASS[$SERVER]:-}\""
  echo "    mgr_mac: \"${NODE_MAC[$SERVER]:-}\""

  echo "    host_mac: \"$H\""
  echo "    host_nw_port_id: ${MAC_TO_PORTID[$H]:-}"
  echo "    cni_mac: \"$C\""
  echo "    cni_nw_port_id: ${MAC_TO_PORTID[$C]:-}"

  # ★追加（cotsと同じ）
  if [[ -n "$A" ]]; then
    echo "    apldata:"
    echo "      mac: \"$A\""
    echo "      nw_port_id: ${MAC_TO_PORTID[$A]:-}"
    echo "      nic_model: \"${APP_NIC_MODEL[$SERVER]}\""
  fi

  echo "    cpu_cores: ${CPU[$SERVER]}"
  echo "    memory_mb: ${MEM[$SERVER]}"
  echo "    status: 0"
  echo "    product_info:"
  echo "      vendor: \"${VENDOR[$SERVER]}\""
  echo "      product_name: \"${PRODUCT[$SERVER]}\""
  echo "      version: \"\""
done

#####################################
# ⑬ cots_gpu
#####################################

echo ""
echo "cots_gpu:"

for SERVER in "${!GPU_MODEL[@]}"; do
  [[ "${NODE_TYPE[$SERVER]:-}" != "COTS" ]] && continue

  echo "  - worker: $SERVER"
  echo "    model: \"${GPU_MODEL[$SERVER]}\""
  echo "    status: 0"
done
