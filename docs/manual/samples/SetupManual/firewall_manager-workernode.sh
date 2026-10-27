#!/usr/bin/env bash
PODS_CIDR="Pod用CIDR設定"
MANAGER_CIDR="マネージャ用CIDR設定"
DCI_OPERATOR_CIDR="DCI運用者端末用CIDR設定"
BASTION_IP="Harbor、GrafanaのGUIアクセスで経由する踏み台のIPアドレス"
# zone
firewall-cmd --permanent --new-zone=k8s-node
firewall-cmd --permanent --zone=k8s-node --add-forward
firewall-cmd --permanent --zone=k8s-node --add-source=${MANAGER_CIDR}
firewall-cmd --permanent --zone=k8s-node --add-source=${DCI_OPERATOR_CIDR}
firewall-cmd --permanent --new-zone=k8s-pod
firewall-cmd --permanent --zone=k8s-pod --add-forward
firewall-cmd --permanent --zone=k8s-pod --add-source=${PODS_CIDR}
# ssh
firewall-cmd --permanent --zone=k8s-node --add-rich-rule="rule family=ipv4 source address=${MANAGER_CIDR} port port=22 protocol=tcp accept"
firewall-cmd --permanent --zone=k8s-node --add-rich-rule="rule family=ipv4 source address=${DCI_OPERATOR_CIDR} port port=22 protocol=tcp accept"
# kubelet API
firewall-cmd --permanent --zone=k8s-node --add-rich-rule="rule family=ipv4 source address=${MANAGER_CIDR} port port=10250 protocol=tcp accept"
firewall-cmd --permanent --zone=k8s-pod --add-rich-rule="rule family=ipv4 source address=${PODS_CIDR} port port=10250 protocol=tcp accept"
# kube-proxy
firewall-cmd --permanent --zone=k8s-node --add-rich-rule="rule family=ipv4 source address=${MANAGER_CIDR} port port=10256 protocol=tcp accept"
firewall-cmd --permanent --zone=k8s-pod --add-rich-rule="rule family=ipv4 source address=${PODS_CIDR} port port=10256 protocol=tcp accept"
firewall-cmd --permanent --zone=k8s-node --add-rich-rule="rule family=ipv4 source address=${MANAGER_CIDR} port port=10249 protocol=tcp accept"
firewall-cmd --permanent --zone=k8s-pod --add-rich-rule="rule family=ipv4 source address=${PODS_CIDR} port port=10249 protocol=tcp accept"
# node-exporter
firewall-cmd --permanent --zone=k8s-node --add-rich-rule="rule family=ipv4 source address=${MANAGER_CIDR} port port=9100 protocol=tcp accept"
firewall-cmd --permanent --zone=k8s-pod --add-rich-rule="rule family=ipv4 source address=${PODS_CIDR} port port=9100 protocol=tcp accept"
# calico IPIP
firewall-cmd --permanent --zone=k8s-node --add-rich-rule="rule family=ipv4 source address=${MANAGER_CIDR} protocol value=4 accept"
firewall-cmd --permanent --zone=k8s-pod --add-rich-rule="rule family=ipv4 source address=${PODS_CIDR} protocol value=4 accept"
# calico Typha
firewall-cmd --permanent --zone=k8s-node --add-rich-rule="rule family=ipv4 source address=${MANAGER_CIDR} port port=5473 protocol=tcp accept"
firewall-cmd --permanent --zone=k8s-pod --add-rich-rule="rule family=ipv4 source address=${PODS_CIDR} port port=5473 protocol=tcp accept"
# calico BGP
firewall-cmd --permanent --zone=k8s-node --add-rich-rule="rule family=ipv4 source address=${MANAGER_CIDR} port port=179 protocol=tcp accept"
firewall-cmd --permanent --zone=k8s-pod --add-rich-rule="rule family=ipv4 source address=${PODS_CIDR} port port=179 protocol=tcp accept"
# vector (for receiving rsyslog)
firewall-cmd --permanent --zone=k8s-node --add-rich-rule="rule family=ipv4 source address=${MANAGER_CIDR} port port=514 protocol=tcp accept"
firewall-cmd --permanent --zone=k8s-pod --add-rich-rule="rule family=ipv4 source address=${PODS_CIDR} port port=514 protocol=tcp accept"
firewall-cmd --permanent --zone=k8s-node --add-rich-rule="rule family=ipv4 source address=${MANAGER_CIDR} port port=514 protocol=udp accept"
firewall-cmd --permanent --zone=k8s-pod --add-rich-rule="rule family=ipv4 source address=${PODS_CIDR} port port=514 protocol=udp accept"

# pod forward egress
firewall-cmd --permanent --new-policy pod-fwd-egress
firewall-cmd --permanent --policy pod-fwd-egress --set-target=ACCEPT
firewall-cmd --permanent --policy pod-fwd-egress --add-ingress-zone=k8s-pod
firewall-cmd --permanent --policy pod-fwd-egress --add-egress-zone=ANY

firewall-cmd --permanent --new-policy k8s-node-to-pod
firewall-cmd --permanent --policy k8s-node-to-pod --set-target=ACCEPT
firewall-cmd --permanent --policy k8s-node-to-pod --add-ingress-zone=k8s-node
firewall-cmd --permanent --policy k8s-node-to-pod --add-egress-zone=k8s-pod

firewall-cmd --permanent --new-policy k8s-pod-to-node
firewall-cmd --permanent --policy k8s-pod-to-node --set-target=ACCEPT
firewall-cmd --permanent --policy k8s-pod-to-node --add-ingress-zone=k8s-pod
firewall-cmd --permanent --policy k8s-pod-to-node --add-egress-zone=k8s-node

firewall-cmd --permanent --new-policy k8s-pod-to-pod
firewall-cmd --permanent --policy k8s-pod-to-pod --set-target=ACCEPT
firewall-cmd --permanent --policy k8s-pod-to-pod --add-ingress-zone=k8s-pod
firewall-cmd --permanent --policy k8s-pod-to-pod --add-egress-zone=k8s-pod

firewall-cmd --permanent --new-policy k8s-node-to-node
firewall-cmd --permanent --policy k8s-node-to-node --set-target=ACCEPT
firewall-cmd --permanent --policy k8s-node-to-node --add-ingress-zone=k8s-node
firewall-cmd --permanent --policy k8s-node-to-node --add-egress-zone=k8s-node

# public disabled
for i in interfaces sources services ports protocols; do
  for v in $(firewall-cmd --zone=public --list-$i); do
    firewall-cmd --permanent --zone=public --remove-${i/%?/}="$v"
  done
done
# reload
firewall-cmd --reload
