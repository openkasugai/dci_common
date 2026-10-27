#!/bin/bash

PROFILE="admin"

echo "server,vendor,product_name,cpu_cores,memory_mb,storage_gb" > result.csv

maas $PROFILE machines read | jq -r '
.[] |
select(.status_name != "Deployed") |
[
  .hostname,
  (.hardware_info.system_vendor // "UNKNOWN"),
  (.hardware_info.system_product // "UNKNOWN"),
  .cpu_count,
  .memory,
  (.storage / 1000 | floor)
] | join(",")
'>> result.csv

echo "" >> result.csv
