#!/bin/bash
# start_port_forward.sh

PORT_FORWARD_TARGET=$1
PORT_FORWARD_MAPPING=$2
NS=$3

pkill -f "kubectl port-forward.*${PORT_FORWARD_TARGET}" 2>/dev/null || true
rm -f /tmp/kubectl_port_forward.{pid,log}
sleep 1

nohup kubectl port-forward -n ${NS} ${PORT_FORWARD_TARGET} ${PORT_FORWARD_MAPPING} --address 0.0.0.0 > /tmp/kubectl_port_forward.log 2>&1 &
echo $! > /tmp/kubectl_port_forward.pid
sleep 3
if ps -p $(cat /tmp/kubectl_port_forward.pid) > /dev/null 2>&1; then
  echo "Port forward started (PID: $(cat /tmp/kubectl_port_forward.pid))"
  exit 0
fi
exit 1
