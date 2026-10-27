#!/bin/bash

CSV_FILE="cdi.csv"

IFS=',' read -r \
HOST USER PASS LOCATION CDI_VERSION GROUP_NAME \
CDI_GUEST CDI_USER CDI_PASSWORD \
CDIMGR_GUEST_USER CDIMGR_GUEST_PASSWORD \
CDIMGR_HOST CDIMGR_HOST_USER CDIMGR_HOST_PASSWORD DIRECTOR_PASSWORD \
PCIE_BOX_IP \
< <(sed -n '2p' "$CSV_FILE")

cat > cdi.yaml << EOF
cdi:
  name: "cdi_v1.1"
  location: "$LOCATION"
  remote_host: "$HOST"
  remote_user: "$USER"
  group_name: "$GROUP_NAME"
  status: 0
  product_info:
    vendor: "fujitsu"
    product_name: "PRIMERGY CDI"
    version: "$CDI_VERSION"

  extra_parameters:
    cdi_guest: "$CDI_GUEST"
    cdi_user: "$CDI_USER"
    cdi_password: "$CDI_PASSWORD"
    cdimgr_guest_user: "$CDIMGR_GUEST_USER"
    cdimgr_guest_password: "$CDIMGR_GUEST_PASSWORD"
    cdimgr_host: "$CDIMGR_HOST"
    cdimgr_host_user: "$CDIMGR_HOST_USER"
    cdimgr_host_password: "$CDIMGR_HOST_PASSWORD"
    director_password: "$DIRECTOR_PASSWORD"

pcie_box:
  ip_address: "$PCIE_BOX_IP"
  status: 0
EOF

./generate_cdi_yaml.sh "$HOST" "$USER" "$PASS" "$CDI_USER" "$CDI_PASSWORD"
./fetch_cdi_yaml.sh "$HOST" "$USER" "$PASS"
